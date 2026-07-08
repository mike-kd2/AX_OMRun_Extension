# Optionaler venv-Bootstrap (Windows PowerShell).
#
# Fuer den Betrieb NICHT noetig: das Tool laeuft ohne Installation via
# .\omrun-param-tool.cmd (nur Python 3.10+ erforderlich). Dieses Skript ist fuer
# alle, die eine virtuelle Umgebung wollen -- optional mit lxml/pyperclip
# (die Extras benoetigen einmalig Netzwerk bzw. lokale Wheels).
#
# Nutzung:
#   powershell -ExecutionPolicy Bypass -File scripts\bootstrap.ps1
#   powershell -ExecutionPolicy Bypass -File scripts\bootstrap.ps1 -Extras
param([switch]$Extras)

$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $PSScriptRoot
$py = if ($env:PYTHON) { $env:PYTHON } else { "python" }
$target = if ($Extras) { ".[lxml,clipboard]" } else { "." }

Set-Location $here
& $py -m venv .venv
& ".\.venv\Scripts\python.exe" -m pip install --upgrade pip *> $null
& ".\.venv\Scripts\python.exe" -m pip install -e $target
Write-Host ""
Write-Host "Fertig. Aktivieren mit: .\.venv\Scripts\Activate.ps1"
Write-Host "Danach: omrun-param-tool inspect --config <suite>"
