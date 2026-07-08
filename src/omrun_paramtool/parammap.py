"""Baut aus den Selektoren die ParamMap: welche Tokens auf welche Werte,
mit Klassifikation, Scope und Dehydrate-Sicherheitsflag."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .env import Environment
from .rtl import RunTimeList
from .tob import TestObject

# Ein Platzhalter im SQL: @ gefolgt von Bezeichner.
TOKEN_RE = re.compile(r"@[A-Za-z_][A-Za-z0-9_]*")

# Default-Whitelist der Environment-Aliase, die in den SQL-Text hydriert werden.
DEFAULT_ENV_PREFIXES = ("@SCHEMA_", "@USER_")

# Werte, die als Bezeichner NICHT eindeutig genug sind -> nie auto-dehydrieren.
_UNSAFE_CHARS = re.compile(r"[\s,*()/\\'\"]")
_MIN_SAFE_LEN = 2


@dataclass
class Entry:
    token: str
    value: str
    cls: str                     # 'param' | 'env_schema'
    in_scope: bool
    source: str
    resolved_via: list[str] = field(default_factory=list)
    safe_dehydrate: bool = True
    unsafe_reason: str | None = None


def _is_safe_value(value: str) -> tuple[bool, str | None]:
    if len(value) < _MIN_SAFE_LEN:
        return False, "zu kurz"
    if _UNSAFE_CHARS.search(value):
        return False, "enthaelt Whitespace/Sonderzeichen"
    return True, None


def tokens_in(sql: str) -> list[str]:
    """Distinkte @-Tokens in Reihenfolge des ersten Auftretens."""
    seen: dict[str, None] = {}
    for m in TOKEN_RE.finditer(sql):
        seen.setdefault(m.group(0), None)
    return list(seen.keys())


@dataclass
class ParamMap:
    entries: list[Entry]
    unresolved_env: list[str]        # whitelist-Aliase im SQL ohne Wert

    def in_scope(self) -> list[Entry]:
        return [e for e in self.entries if e.in_scope]

    def by_token(self) -> dict[str, Entry]:
        return {e.token: e for e in self.entries}


def build(
    tob: TestObject,
    side: str,
    rtl: RunTimeList | None,
    env: Environment | None,
    number: str | None = None,
    env_prefixes: tuple[str, ...] = DEFAULT_ENV_PREFIXES,
) -> tuple[str, ParamMap]:
    """Liefert (roh-SQL der Seite, ParamMap)."""
    query = tob.get_query(side)
    sql = query.sql
    present = set(tokens_in(sql))

    entries: list[Entry] = []
    unresolved_env: list[str] = []

    # 1) @paramN aus der .rtl
    params = rtl.param_map(number) if rtl is not None else {}
    for token, value in params.items():
        safe, reason = _is_safe_value(value)
        entries.append(
            Entry(
                token=token,
                value=value,
                cls="param",
                in_scope=True,
                source=f"{rtl.path.name}:{token}",
                safe_dehydrate=safe,
                unsafe_reason=reason,
            )
        )

    # 2) Whitelist-Environment-Aliase, die im SQL vorkommen
    if env is not None:
        for token in sorted(present):
            if not token.startswith(env_prefixes):
                continue
            res = env.resolve(token)
            if not res.resolved or res.value is None:
                unresolved_env.append(token)
                continue
            safe, reason = _is_safe_value(res.value)
            entries.append(
                Entry(
                    token=token,
                    value=res.value,
                    cls="env_schema",
                    in_scope=True,
                    source=f"env:{token}",
                    resolved_via=res.chain,
                    safe_dehydrate=safe,
                    unsafe_reason=reason,
                )
            )

    # 3) Duplikat-Werte innerhalb der In-Scope-Menge -> dehydrate unsicher
    _flag_value_collisions(entries)

    return sql, ParamMap(entries=entries, unresolved_env=unresolved_env)


def _flag_value_collisions(entries: list[Entry]) -> None:
    scoped = [e for e in entries if e.in_scope]
    # gleiche Werte fuer verschiedene Tokens
    counts: dict[str, int] = {}
    for e in scoped:
        counts[e.value] = counts.get(e.value, 0) + 1
    for e in scoped:
        if counts[e.value] > 1 and e.safe_dehydrate:
            e.safe_dehydrate = False
            e.unsafe_reason = "Wert nicht eindeutig (mehreren Tokens zugeordnet)"
    # ein Wert ist Teilstring eines anderen -> Ueberlappung
    for e in scoped:
        if not e.safe_dehydrate:
            continue
        for other in scoped:
            if other is e:
                continue
            if e.value != other.value and e.value in other.value:
                e.safe_dehydrate = False
                e.unsafe_reason = f"Wert ist Teilstring von {other.token}-Wert"
                break
