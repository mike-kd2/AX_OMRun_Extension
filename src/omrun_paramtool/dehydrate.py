"""Dehydrate: echte Werte -> @-Tokens.

Nur Whole-Token, longest-value-first, ausschliesslich sichere & eindeutige
In-Scope-Werte. Mehrdeutigkeiten werden gemeldet, nicht still ersetzt.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .parammap import ParamMap


@dataclass
class DehydrateResult:
    text: str
    replaced: dict[str, int] = field(default_factory=dict)   # token -> Anzahl
    skipped_unsafe: list[tuple[str, str]] = field(default_factory=list)  # (token, grund)
    not_found: list[str] = field(default_factory=list)       # Wert 0x im Text
    conflicts: list[tuple[str, int]] = field(default_factory=list)  # (token, treffer>1)


def _value_pattern(value: str) -> re.Pattern:
    # Whole-Token an Bezeichnergrenzen. Wert wurde bereits als bezeichner-artig
    # (kein Whitespace/Sonderzeichen) gefiltert.
    return re.compile(
        r"(?<![A-Za-z0-9_@])" + re.escape(value) + r"(?![A-Za-z0-9_])"
    )


def dehydrate(sql_segment: str, pmap: ParamMap, force: bool = False) -> DehydrateResult:
    result = DehydrateResult(text=sql_segment)
    entries = pmap.in_scope()

    # Zuerst unsichere aussortieren und melden.
    safe_entries = []
    for e in entries:
        if e.safe_dehydrate:
            safe_entries.append(e)
        else:
            result.skipped_unsafe.append((e.token, e.unsafe_reason or "unsicher"))

    # Laengste Werte zuerst, damit z.B. 'demo_source_admin' vor 'demo_source' greift.
    safe_entries.sort(key=lambda e: len(e.value), reverse=True)

    for e in safe_entries:
        pat = _value_pattern(e.value)
        hits = len(pat.findall(result.text))
        if hits == 0:
            result.not_found.append(e.token)
            continue
        if hits > 1 and not force:
            result.conflicts.append((e.token, hits))
            continue
        result.text = pat.sub(e.token, result.text)
        result.replaced[e.token] = hits

    return result
