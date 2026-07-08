"""Ein-/Ausgabe ueber Zwischenablage (optional) oder stdin/stdout.

pyperclip ist optionale Abhaengigkeit; ohne sie ist nur '-' (stdio) verfuegbar.
"""

from __future__ import annotations

import sys

from .errors import OMrunToolError


def _require_pyperclip():
    try:
        import pyperclip  # noqa: PLC0415
    except ImportError as exc:  # pragma: no cover - umgebungsabhaengig
        raise OMrunToolError(
            "Zwischenablage benoetigt 'pyperclip' (pip install omrun-param-tool[clipboard]). "
            "Alternativ '-' fuer stdin/stdout verwenden."
        ) from exc
    return pyperclip


def read_input(target: str) -> str:
    if target == "-":
        return sys.stdin.read()
    if target == "clip":
        return _require_pyperclip().paste()
    raise OMrunToolError(f"unbekanntes Eingabeziel: {target!r}")


def write_output(target: str, text: str) -> None:
    if target == "-":
        sys.stdout.write(text)
        if not text.endswith("\n"):
            sys.stdout.write("\n")
        return
    if target == "clip":
        _require_pyperclip().copy(text)
        return
    raise OMrunToolError(f"unbekanntes Ausgabeziel: {target!r}")
