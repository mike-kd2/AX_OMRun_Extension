# Baut einen VOLL PORTABLEN Windows-Ordner: embeddable Python (keine Installation,
# kein Admin) + optionale Extras aus dem Wheelhouse + das Tool als .pyz + Launcher.
#
# EINMALIG auf einem Rechner MIT Internet ausfuehren (dein Laptop reicht; python.org
# muss erreichbar sein). Danach den erzeugten Ordner portable\ komplett auf den
# airgapped Server kopieren und dort .\portable\run-portable.cmd aufrufen.
#
#   powershell -ExecutionPolicy Bypass -File scripts\make_portable_windows.ps1
#   powershell -ExecutionPolicy Bypass -File scripts\make_portable_windows.ps1 -PythonVersion 3.11.9
#   ... -NoLxml     # ohne lxml (nur stdlib-Kern; Tool laeuft trotzdem voll)
param(
    [string]$PythonVersion = "3.12.8",
    [switch]$NoLxml
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$portable = Join-Path $root "portable"
$pydir = Join-Path $portable "python"
$whl = Join-Path $root "wheelhouse"

Add-Type -AssemblyName System.IO.Compression.FileSystem

# --- Zielordner vorbereiten ------------------------------------------------
New-Item -ItemType Directory -Force -Path $portable | Out-Null
if (Test-Path $pydir) { Remove-Item -Recurse -Force $pydir }
New-Item -ItemType Directory -Force -Path $pydir | Out-Null

# --- embeddable Python laden + entpacken -----------------------------------
$zipUrl = "https://www.python.org/ftp/python/$PythonVersion/python-$PythonVersion-embed-amd64.zip"
$zipTmp = Join-Path $env:TEMP "python-$PythonVersion-embed-amd64.zip"
Write-Host "Lade embeddable Python: $zipUrl"
Invoke-WebRequest -Uri $zipUrl -OutFile $zipTmp
[System.IO.Compression.ZipFile]::ExtractToDirectory($zipTmp, $pydir)

# --- ._pth so patchen, dass site-packages + import site aktiv sind ---------
$pth = Get-ChildItem $pydir -Filter "python*._pth" | Select-Object -First 1
if ($pth) {
    $lines = Get-Content $pth.FullName
    $lines = $lines | ForEach-Object { if ($_ -match '^\s*#\s*import\s+site') { "import site" } else { $_ } }
    if ($lines -notcontains "Lib\site-packages") { $lines += "Lib\site-packages" }
    Set-Content -Path $pth.FullName -Value $lines -Encoding Ascii
}
$sitePackages = Join-Path $pydir "Lib\site-packages"
New-Item -ItemType Directory -Force -Path $sitePackages | Out-Null

# --- optionale Extras aus dem Wheelhouse in site-packages entpacken --------
function Expand-Wheel($wheelPath, $dest) {
    $tmp = "$wheelPath.zip"
    Copy-Item $wheelPath $tmp -Force
    [System.IO.Compression.ZipFile]::ExtractToDirectory($tmp, $dest)
    Remove-Item $tmp -Force
}

if (Test-Path $whl) {
    $pyTag = "cp" + ($PythonVersion.Split(".")[0..1] -join "")   # z.B. cp312
    Get-ChildItem $whl -Filter "pyperclip-*.whl" | ForEach-Object { Expand-Wheel $_.FullName $sitePackages }
    if (-not $NoLxml) {
        $lxmlWheel = Get-ChildItem $whl -Filter "lxml-*$pyTag*win_amd64.whl" | Select-Object -First 1
        if ($lxmlWheel) {
            Expand-Wheel $lxmlWheel.FullName $sitePackages
            Write-Host "lxml eingebunden: $($lxmlWheel.Name)"
        } else {
            Write-Warning "Kein lxml-Wheel fuer $pyTag/win_amd64 im Wheelhouse -> Kern laeuft ohne lxml."
        }
    }
}

# --- .pyz + Launcher sicherstellen -----------------------------------------
$pyz = Join-Path $portable "omrun-param-tool.pyz"
if (-not (Test-Path $pyz)) {
    Write-Warning "portable\omrun-param-tool.pyz fehlt -> mit 'python scripts/build_pyz.py' neu bauen und nach portable\ kopieren."
}

Write-Host ""
Write-Host "Fertig. Portabler Ordner: $portable"
Write-Host "Test:  .\portable\run-portable.cmd inspect --config <suite>"
Write-Host "Transfer: den gesamten Ordner 'portable\' auf den airgapped Server kopieren."
