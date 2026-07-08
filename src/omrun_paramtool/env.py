"""Environment (.env): Alias-Tabelle DbAlias -> Wert, mit Layering und
rekursiver Aufloesung.

- Eine spezifische .env (z.B. Demo/TestEnvironment1) plus immer Global.env.
- Praezedenz bei Alias-Kollision: 'specific' (Default, Annahme) oder 'global'.
  Die reale OMrun-Regel ist noch zu verifizieren -> schaltbar gehalten.
- Wert eines Alias: <Db> falls gesetzt, sonst <Server>.
- Rekursion: ist der Wert selbst ein @-Alias, weiter aufloesen
  (Zyklus-Schutz, Max-Tiefe).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from . import dataset_xml as dx
from .errors import ResolutionError

_TOKEN_RE = re.compile(r"^@[A-Za-z_][A-Za-z0-9_]*$")
_MAX_DEPTH = 32


@dataclass(frozen=True)
class AliasRow:
    alias: str
    db: str | None
    server: str | None
    db_type: str | None
    source_file: str

    @property
    def raw_value(self) -> str | None:
        if self.db not in (None, ""):
            return self.db
        return self.server


@dataclass
class Resolution:
    token: str
    value: str | None          # None = nicht aufloesbar
    chain: list[str] = field(default_factory=list)
    resolved: bool = True


class Environment:
    def __init__(self, precedence: str = "specific"):
        if precedence not in ("specific", "global"):
            raise ValueError("precedence muss 'specific' oder 'global' sein")
        self.precedence = precedence
        self._table: dict[str, AliasRow] = {}

    # --- Laden -----------------------------------------------------------
    def _load_file(self, path: Path, override: bool) -> None:
        tree = dx.load(path)
        root = tree.getroot()
        for env in dx.local_findall(root, "Environment"):
            alias = dx.child_text(env, "DbAlias")
            if not alias:
                continue
            row = AliasRow(
                alias=alias,
                db=dx.child_text(env, "Db"),
                server=dx.child_text(env, "Server"),
                db_type=dx.child_text(env, "DbType"),
                source_file=path.name,
            )
            if override or alias not in self._table:
                self._table[alias] = row

    @classmethod
    def load(
        cls,
        specific: str | Path | None,
        global_env: str | Path | None,
        precedence: str = "specific",
    ) -> "Environment":
        self = cls(precedence=precedence)
        # Reihenfolge so, dass die gewuenschte Ebene per override gewinnt.
        if precedence == "specific":
            if global_env:
                self._load_file(Path(global_env), override=True)
            if specific:
                self._load_file(Path(specific), override=True)
        else:  # 'global' gewinnt
            if specific:
                self._load_file(Path(specific), override=True)
            if global_env:
                self._load_file(Path(global_env), override=True)
        return self

    # --- Aufloesung ------------------------------------------------------
    def aliases(self) -> list[str]:
        return list(self._table.keys())

    def resolve(self, token: str) -> Resolution:
        chain: list[str] = []
        seen: set[str] = set()
        current = token
        for _ in range(_MAX_DEPTH):
            chain.append(current)
            if current in seen:
                raise ResolutionError(
                    f"Alias-Zyklus bei {token}: {' -> '.join(chain)}"
                )
            seen.add(current)
            row = self._table.get(current)
            if row is None:
                # Nicht in der Tabelle: nur der Ausgangstoken gilt als
                # 'nicht aufloesbar'; ein Zwischenwert, der kein Alias ist,
                # ist bereits final (siehe unten).
                resolved = current != token
                return Resolution(
                    token=token,
                    value=current if resolved else None,
                    chain=chain[:-1] if not resolved else chain,
                    resolved=resolved,
                )
            value = row.raw_value
            if value is None or value == "":
                return Resolution(token=token, value=None, chain=chain, resolved=False)
            if _TOKEN_RE.match(value) and value in self._table:
                current = value
                continue
            chain.append(value)
            return Resolution(token=token, value=value, chain=chain, resolved=True)
        raise ResolutionError(f"Aufloesung zu tief bei {token} (Zyklus?)")
