#!/usr/bin/env bash
# Baut denselben portablen Windows-Ordner wie make_portable_windows.ps1, aber
# von einem Online-LINUX/macOS-Rechner aus (reine Dateioperationen; das erzeugte
# python\ ist ein Windows-Interpreter und laeuft NUR auf Windows).
#
# EINMALIG auf einem Rechner MIT Internet (python.org erreichbar). Danach den
# Ordner portable/ auf den airgapped Windows-Server kopieren und dort
# run-portable.cmd aufrufen.
#
#   scripts/make_portable_windows.sh                 # Python 3.12.8, mit lxml
#   scripts/make_portable_windows.sh 3.11.9          # andere Version
#   NO_LXML=1 scripts/make_portable_windows.sh       # ohne lxml
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
pyver="${1:-3.12.8}"
portable="$here/portable"
pydir="$portable/python"
whl="$here/wheelhouse"

mkdir -p "$portable"
rm -rf "$pydir"; mkdir -p "$pydir"

url="https://www.python.org/ftp/python/$pyver/python-$pyver-embed-amd64.zip"
tmp="$(mktemp -d)/embed.zip"
echo "Lade embeddable Python: $url"
curl -fSL "$url" -o "$tmp"
( cd "$pydir" && unzip -q "$tmp" )

# ._pth patchen: import site aktivieren, site-packages ergaenzen
pth="$(ls "$pydir"/python*._pth 2>/dev/null | head -1 || true)"
if [ -n "$pth" ]; then
  sed -i 's/^\s*#\s*import\s\+site/import site/' "$pth"
  grep -qxF 'Lib\site-packages' "$pth" || printf 'Lib\\site-packages\n' >> "$pth"
fi
sp="$pydir/Lib/site-packages"; mkdir -p "$sp"

# Wheels aus dem Wheelhouse entpacken (Wheel == Zip)
if [ -d "$whl" ]; then
  pytag="cp$(echo "$pyver" | cut -d. -f1-2 | tr -d .)"   # cp312
  for w in "$whl"/pyperclip-*.whl; do [ -e "$w" ] && unzip -qo "$w" -d "$sp"; done
  if [ -z "${NO_LXML:-}" ]; then
    lw="$(ls "$whl"/lxml-*"$pytag"*win_amd64.whl 2>/dev/null | head -1 || true)"
    if [ -n "$lw" ]; then unzip -qo "$lw" -d "$sp"; echo "lxml eingebunden: $(basename "$lw")";
    else echo "WARN: kein lxml-Wheel fuer $pytag/win_amd64 -> Kern laeuft ohne lxml."; fi
  fi
fi

[ -f "$portable/omrun-param-tool.pyz" ] || echo "WARN: portable/omrun-param-tool.pyz fehlt (python scripts/build_pyz.py)."
echo
echo "Fertig: $portable  -> gesamten Ordner auf den airgapped Server kopieren."
echo "Test auf Windows: .\\portable\\run-portable.cmd inspect --config <suite>"
