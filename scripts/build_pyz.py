#!/usr/bin/env python3
"""Baut ein einzelnes, selbst-enthaltenes Executable dist/omrun-param-tool.pyz.

Reine Standardbibliothek -> das .pyz laeuft auf jedem Python 3.10+ ohne
Installation und ohne Netzwerk (ideal fuer airgapped). Aufruf danach:

    python omrun-param-tool.pyz hydrate --config ... (siehe README)

Neu bauen:  python scripts/build_pyz.py
"""

from __future__ import annotations

import zipapp
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
# Kanonische, versionierte Ablage (wird vom portablen Launcher genutzt).
OUT = ROOT / "portable" / "omrun-param-tool.pyz"


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    zipapp.create_archive(
        source=SRC,
        target=OUT,
        main="omrun_paramtool.cli:main",
        compressed=True,
    )
    print(f"gebaut: {OUT.relative_to(ROOT)}")
    print("Aufruf: python", OUT.name, "inspect --config <suite>")
    print("(portabel: portable/run-portable.cmd inspect --config <suite>)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
