"""Hydrate: @-Tokens -> echte Werte (nur In-Scope-Eintraege)."""

from __future__ import annotations

import re
from dataclasses import dataclass

from .parammap import ParamMap, tokens_in


@dataclass
class HydrateResult:
    text: str
    replaced: dict[str, int]           # token -> Anzahl Ersetzungen
    remaining_tokens: list[str]        # nicht ersetzte @-Tokens im Output


def _token_pattern(token: str) -> re.Pattern:
    # Whole-Token: rechts kein weiteres Bezeichnerzeichen (verhindert @param1
    # in @param12). Links kann @ ohnehin nicht Teil eines Bezeichners sein.
    return re.compile(re.escape(token) + r"(?![A-Za-z0-9_])")


def hydrate(sql_segment: str, pmap: ParamMap) -> HydrateResult:
    text = sql_segment
    replaced: dict[str, int] = {}
    # Laengste Tokens zuerst -> @param12 vor @param1.
    entries = sorted(pmap.in_scope(), key=lambda e: len(e.token), reverse=True)
    for e in entries:
        pat = _token_pattern(e.token)
        text, n = pat.subn(lambda _m, v=e.value: v, text)
        if n:
            replaced[e.token] = n
    remaining = tokens_in(text)
    return HydrateResult(text=text, replaced=replaced, remaining_tokens=remaining)
