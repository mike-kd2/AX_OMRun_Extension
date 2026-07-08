"""End-to-End ueber das CLI-Modul, erzwungen auf dem stdlib-Backend
(sichert den airgapped Betrieb ohne lxml)."""

import os
import subprocess
import sys
from pathlib import Path

from conftest import COMP

ROOT = Path(__file__).resolve().parent.parent


def _run(args, stdin=None):
    env = dict(os.environ)
    env["OMRUN_XML_BACKEND"] = "stdlib"
    env["PYTHONPATH"] = str(ROOT / "src") + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.run(
        [sys.executable, "-m", "omrun_paramtool", *args],
        input=stdin,
        capture_output=True,
        text=True,
        env=env,
    )


def test_cli_hydrate_stdlib():
    r = _run(
        [
            "hydrate",
            "--config", str(COMP),
            "--object", "CreateCompareView",
            "--side", "A",
            "--env", "Demo",
            "--rtl", "Extensive",
        ]
    )
    assert r.returncode == 0
    assert "demo_source.v_GetCompareQueryOra" in r.stdout
    assert "@param1" not in r.stdout


def test_cli_roundtrip_via_pipe():
    hy = _run(
        [
            "hydrate", "--config", str(COMP), "--object", "CreateCompareView",
            "--side", "A", "--env", "Demo", "--rtl", "Extensive",
        ]
    )
    de = _run(
        [
            "dehydrate", "--config", str(COMP), "--object", "CreateCompareView",
            "--side", "A", "--env", "Demo", "--rtl", "Extensive", "--force",
        ],
        stdin=hy.stdout,
    )
    assert de.returncode == 0
    # mit --force werden die eindeutigen Tokens wiederhergestellt
    assert "@SCHEMA_Source" in de.stdout
    assert "@param1" in de.stdout


def test_cli_missing_object_exit2():
    r = _run(
        ["hydrate", "--config", str(COMP), "--object", "Nope",
         "--env", "Demo", "--rtl", "Extensive"]
    )
    assert r.returncode == 2
    assert "Fehler" in r.stderr
