# Baut ein Wheelhouse (Offline-Paketquelle) fuer die OPTIONALEN Extras
# lxml + pyperclip sowie das Tool selbst -- Windows-Variante.
#
# Der Kern braucht KEINE Wheels (reine Standardbibliothek). Dieses Wheelhouse
# ist nur fuer lxml (Stufe-2-Treue) bzw. pyperclip (Zwischenablage) noetig.
#
# lxml ist ein Binaer-Wheel -> plattform-/Python-versions-spezifisch. Fuer das
# ZIEL-System bauen. Beispiel Zielangabe: win_amd64:312
#
# Nutzung (Rechner MIT Netzwerk):
#   powershell -File scripts\build_wheelhouse.ps1 win_amd64:312
#   powershell -File scripts\build_wheelhouse.ps1            # Host-Plattform
#
# Danach offline auf dem Server:
#   pip install --no-index --find-links wheelhouse "omrun-param-tool[lxml,clipboard]"
param([string[]]$Targets)

$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $PSScriptRoot
$py = if ($env:PYTHON) { $env:PYTHON } else { "python" }
$wh = Join-Path $here "wheelhouse"
Set-Location $here
New-Item -ItemType Directory -Force -Path $wh | Out-Null

Write-Host "== Tool-Wheel (py3-none-any) =="
& $py -m pip wheel . -w $wh --no-deps -q

Write-Host "== pyperclip (pure python) =="
& $py -m pip download pyperclip -d $wh --only-binary=:all: -q

if (-not $Targets -or $Targets.Count -eq 0) {
    Write-Host "== lxml fuer Host-Plattform =="
    & $py -m pip download lxml -d $wh --only-binary=:all: -q
} else {
    foreach ($t in $Targets) {
        $plat, $pyver = $t.Split(":")
        Write-Host "== lxml fuer $plat / cp$pyver =="
        & $py -m pip download lxml -d $wh --only-binary=:all: `
            --platform $plat --python-version $pyver --abi "cp$pyver" -q
    }
}

Write-Host ""
Write-Host "Wheelhouse gefuellt: $wh"
Get-ChildItem $wh | Select-Object -ExpandProperty Name
Write-Host ""
Write-Host 'Offline-Install: pip install --no-index --find-links wheelhouse "omrun-param-tool[lxml,clipboard]"'
