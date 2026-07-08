"""Header/Body-Segmentierung am /*BODY*/-Marker.

Vertrag: header + marker + body == Originaltext (verlustfreie Rekombination,
Fundament fuer Write-back in Stufe 2).
"""

from __future__ import annotations

from dataclasses import dataclass

MARKER = "/*BODY*/"


@dataclass(frozen=True)
class Segments:
    header: str
    marker: str          # "" wenn kein Marker vorhanden
    body: str            # "" wenn kein Marker vorhanden
    has_body: bool

    def recombine(self) -> str:
        return self.header + self.marker + self.body


def split(sql: str) -> Segments:
    idx = sql.find(MARKER)
    if idx == -1:
        return Segments(header=sql, marker="", body="", has_body=False)
    return Segments(
        header=sql[:idx],
        marker=MARKER,
        body=sql[idx + len(MARKER):],
        has_body=True,
    )


def select(sql: str, part: str) -> tuple[str, str, str | None]:
    """Segment gemaess part waehlen.

    part: 'body' (Default), 'header' oder 'full'.
    Returns (text, effective_part, warning_or_None).

    'body' ohne vorhandenen Marker faellt auf den ganzen Text zurueck (Header),
    da Kontrolllisten haeufig nur einen Kopf ohne Body haben.
    """
    seg = split(sql)
    if part == "full":
        return seg.recombine(), "full", None
    if part == "header":
        return seg.header, "header", None
    if part == "body":
        if seg.has_body:
            return seg.body, "body", None
        return (
            seg.header,
            "header",
            "kein /*BODY*/-Marker vorhanden -> Fallback auf gesamten Query (Header).",
        )
    raise ValueError(f"unbekannter part: {part!r}")
