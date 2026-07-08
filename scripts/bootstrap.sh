#!/usr/bin/env bash
# Optionaler venv-Bootstrap (Linux/macOS).
#
# Fuer den Betrieb NICHT noetig: das Tool laeuft ohne Installation via
# ./omrun-param-tool (nur Python 3.10+ erforderlich). Dieses Skript ist fuer
# alle, die eine virtuelle Umgebung wollen -- optional mit lxml/pyperclip
# (die Extras benoetigen einmalig Netzwerk bzw. lokale Wheels).
#
# Nutzung:
#   scripts/bootstrap.sh                 # nur Kern (keine externen Deps)
#   scripts/bootstrap.sh --extras        # zusaetzlich lxml + clipboard
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="${PYTHON:-python3}"
extras=""
[ "${1:-}" = "--extras" ] && extras="[lxml,clipboard]"

cd "$here"
"$PY" -m venv .venv
# shellcheck disable=SC1091
. .venv/bin/activate
python -m pip install --upgrade pip >/dev/null 2>&1 || true
python -m pip install -e ".${extras}"
echo
echo "Fertig. Aktivieren mit: source .venv/bin/activate"
echo "Danach: omrun-param-tool inspect --config <suite>"
