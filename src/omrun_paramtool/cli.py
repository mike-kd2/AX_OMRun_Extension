"""Kommandozeile: inspect / hydrate / dehydrate.

Ausgabe-Disziplin: das eigentliche SQL bzw. aufgeloeste Werte gehen nach stdout
(bzw. Zwischenablage); Diagnostik/Warnungen nach stderr. Mit --quiet werden in
inspect keine Werte gezeigt (nur Tokens/Metadaten)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import clipboard, locate
from . import segments as seg
from .dehydrate import dehydrate as do_dehydrate
from .env import Environment
from .errors import OMrunToolError
from .hydrate import hydrate as do_hydrate
from .parammap import build as build_map
from .rtl import RunTimeList
from .tob import TestObject


def _eprint(*args) -> None:
    print(*args, file=sys.stderr)


def _load_context(a: argparse.Namespace):
    root = Path(a.config)
    if not root.exists():
        raise OMrunToolError(f"Config-Wurzel nicht gefunden: {root}")
    tob_path = locate.find_tob(root, a.object)
    tob = TestObject(tob_path)

    rtl = None
    if getattr(a, "rtl", None):
        rtl = RunTimeList(locate.find_rtl(tob_path, a.rtl))

    env = None
    if getattr(a, "env", None):
        env = Environment.load(
            specific=locate.find_env(root, a.env),
            global_env=locate.find_global_env(root),
            precedence=a.env_precedence,
        )
    return root, tob_path, tob, rtl, env


# --- inspect -------------------------------------------------------------
def cmd_inspect(a: argparse.Namespace) -> int:
    root = Path(a.config)
    if not root.exists():
        raise OMrunToolError(f"Config-Wurzel nicht gefunden: {root}")

    if not a.object:
        _eprint("TestObjects:")
        for t in locate.list_objects(root):
            _eprint(f"  {t.relative_to(root)}")
        _eprint("\nEnvironments:")
        for e in locate.list_envs(root):
            _eprint(f"  {e.stem}")
        return 0

    _, tob_path, tob, rtl, env = _load_context(a)
    _eprint(f"TestObject: {tob_path.relative_to(root)}")
    _eprint(f"Seiten: A={tob.has_side('A')} B={tob.has_side('B')}")
    _eprint("RunTimeLists: " + ", ".join(r.stem for r in locate.list_rtls(tob_path)))

    side = a.side if a.side in ("A", "B") else "A"
    sql, pmap = build_map(tob, side, rtl, env, number=a.number)
    segs = seg.split(sql)
    _eprint(f"\nSeite {side}: /*BODY*/-Marker={'ja' if segs.has_body else 'nein'}")

    _eprint("\nParamMap (In-Scope):")
    for e in pmap.in_scope():
        val = "***" if a.quiet else e.value
        chain = (" via " + " -> ".join(e.resolved_via)) if e.resolved_via else ""
        safe = "" if e.safe_dehydrate else f"  [dehydrate uebersprungen: {e.unsafe_reason}]"
        _eprint(f"  {e.token} = {val}   ({e.cls}){chain}{safe}")
    if pmap.unresolved_env:
        _eprint("\nNicht aufgeloeste Whitelist-Aliase: " + ", ".join(pmap.unresolved_env))
    return 0


# --- hydrate -------------------------------------------------------------
def cmd_hydrate(a: argparse.Namespace) -> int:
    _, _, tob, rtl, env = _load_context(a)
    sides = ["A", "B"] if a.side == "both" else [a.side]

    outputs: list[str] = []
    strict_fail = False
    for side in sides:
        sql, pmap = build_map(tob, side, rtl, env, number=a.number)
        segment, eff_part, warn = seg.select(sql, a.part)
        if warn:
            _eprint(f"[{side}] {warn}")
        res = do_hydrate(segment, pmap)
        if len(sides) > 1:
            outputs.append(f"-- ===== Seite {side} ({eff_part}) =====\n{res.text}")
        else:
            outputs.append(res.text)
        _eprint(
            f"[{side}] hydriert: "
            + ", ".join(f"{t}x{n}" for t, n in res.replaced.items())
            if res.replaced
            else f"[{side}] keine Ersetzung"
        )
        expected_leftover = [t for t in res.remaining_tokens]
        if expected_leftover:
            _eprint(f"[{side}] verbleibende Tokens (nicht in Scope): "
                    + ", ".join(expected_leftover))
            if a.strict:
                strict_fail = True

    clipboard.write_output(a.out, "\n".join(outputs))
    return 3 if strict_fail else 0


# --- dehydrate -----------------------------------------------------------
def cmd_dehydrate(a: argparse.Namespace) -> int:
    _, _, tob, rtl, env = _load_context(a)
    side = a.side if a.side in ("A", "B") else "A"
    _, pmap = build_map(tob, side, rtl, env, number=a.number)

    developed = clipboard.read_input(a.in_)
    res = do_dehydrate(developed, pmap, force=a.force)

    clipboard.write_output(a.out, res.text)

    if res.replaced:
        _eprint("dehydriert: " + ", ".join(f"{t}x{n}" for t, n in res.replaced.items()))
    for token, reason in res.skipped_unsafe:
        _eprint(f"uebersprungen (unsicher) {token}: {reason}")
    if res.not_found:
        _eprint("Wert nicht im Text gefunden: " + ", ".join(res.not_found))
    if res.conflicts:
        for token, hits in res.conflicts:
            _eprint(f"KONFLIKT {token}: {hits} Treffer -> nicht ersetzt (--force zum Erzwingen)")
        if not a.force:
            return 3
    return 0


# --- parser --------------------------------------------------------------
def _add_common(p: argparse.ArgumentParser) -> None:
    p.add_argument("--config", required=True, help="Config-Wurzel (OMrun-Suite)")
    p.add_argument("--object", help="TestObject (Name oder Pfad)")
    p.add_argument("--env", help="Environment-Name (.env, ohne Endung)")
    p.add_argument("--rtl", help="RunTimeList-Name (.rtl, ohne Endung)")
    p.add_argument("--number", help="DataTableRunTime <Number> (Default: erste aktive)")
    p.add_argument(
        "--env-precedence",
        choices=("specific", "global"),
        default="specific",
        help="Layering-Praezedenz bei Alias-Kollision (Default: specific)",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="omrun-param-tool")
    sub = parser.add_subparsers(dest="cmd", required=True)

    pi = sub.add_parser("inspect", help="Objekte/Envs/ParamMap anzeigen (read-only)")
    _add_common(pi)
    pi.add_argument("--side", default="A", choices=("A", "B"))
    pi.add_argument("--quiet", action="store_true", help="keine Werte ausgeben")
    pi.set_defaults(func=cmd_inspect)

    ph = sub.add_parser("hydrate", help="@Tokens -> echte Werte")
    _add_common(ph)
    ph.add_argument("--side", default="A", choices=("A", "B", "both"))
    ph.add_argument("--part", default="body", choices=("body", "header", "full"))
    ph.add_argument("--out", default="-", help="'-' (stdout, Default) oder 'clip'")
    ph.add_argument("--strict", action="store_true",
                    help="Exit 3 bei verbleibenden Tokens")
    ph.set_defaults(func=cmd_hydrate)

    pd = sub.add_parser("dehydrate", help="echte Werte -> @Tokens")
    _add_common(pd)
    pd.add_argument("--side", default="A", choices=("A", "B"))
    pd.add_argument("--in", dest="in_", default="-", help="'-' (stdin, Default) oder 'clip'")
    pd.add_argument("--out", default="-", help="'-' (stdout, Default) oder 'clip'")
    pd.add_argument("--force", action="store_true", help="Mehrfachtreffer trotzdem ersetzen")
    pd.set_defaults(func=cmd_dehydrate)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    a = parser.parse_args(argv)
    if a.cmd != "inspect" and not a.object:
        parser.error("--object ist erforderlich")
    try:
        return a.func(a)
    except OMrunToolError as exc:
        _eprint(f"Fehler: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
