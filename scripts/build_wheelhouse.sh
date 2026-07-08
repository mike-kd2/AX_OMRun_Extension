#!/usr/bin/env bash
# Baut ein Wheelhouse (Offline-Paketquelle) fuer die OPTIONALEN Extras
# lxml + pyperclip sowie das Tool selbst.
#
# Der Kern des Tools braucht KEINE Wheels (reine Standardbibliothek). Dieses
# Wheelhouse ist nur noetig, wenn du auf dem airgapped Server lxml (Stufe-2-
# Serialisierungstreue) oder pyperclip (Zwischenablage) willst.
#
# lxml ist ein BINAeR-Wheel -> plattform- und Python-versions-spezifisch. Man
# baut das Wheelhouse fuer das ZIEL-System, nicht fuer das Build-System.
#
# Nutzung (auf einem Rechner MIT Netzwerk):
#   scripts/build_wheelhouse.sh win_amd64:312 [win_amd64:311 ...]
#   scripts/build_wheelhouse.sh manylinux2014_x86_64:311
# Ohne Argument: aktuelle Host-Plattform.
#
# Danach auf dem airgapped Server (Wheelhouse mitkopieren):
#   pip install --no-index --find-links wheelhouse "omrun-param-tool[lxml,clipboard]"
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="${PYTHON:-python3}"
WH="$here/wheelhouse"
cd "$here"
mkdir -p "$WH"

echo "== Tool-Wheel (py3-none-any) =="
"$PY" -m pip wheel . -w "$WH" --no-deps -q

echo "== pyperclip (pure python) =="
"$PY" -m pip download pyperclip -d "$WH" --only-binary=:all: -q

if [ "$#" -eq 0 ]; then
  echo "== lxml fuer Host-Plattform =="
  "$PY" -m pip download lxml -d "$WH" --only-binary=:all: -q
else
  for target in "$@"; do
    plat="${target%%:*}"
    pyver="${target##*:}"
    echo "== lxml fuer ${plat} / cp${pyver} =="
    "$PY" -m pip download lxml -d "$WH" --only-binary=:all: \
      --platform "$plat" --python-version "$pyver" --abi "cp${pyver}" -q
  done
fi

echo
echo "Wheelhouse gefuellt: $WH"
ls -1 "$WH"
echo
echo "Offline-Install auf dem Server:"
echo "  pip install --no-index --find-links wheelhouse \"omrun-param-tool[lxml,clipboard]\""
