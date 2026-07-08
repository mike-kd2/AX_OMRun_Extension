@echo off
rem Portabler Launcher -- KEIN installiertes Python noetig.
rem Nutzt das embeddable Python neben dieser Datei (Ordner python\) und fuehrt
rem das Tool als Single-File-App (omrun-param-tool.pyz) aus.
rem
rem Voraussetzung: der Ordner python\ wurde einmalig per
rem   scripts\make_portable_windows.ps1  (auf einem Online-Rechner) erzeugt.
rem
rem Beispiel:
rem   run-portable.cmd inspect  --config C:\pfad\zur\Suite
rem   run-portable.cmd hydrate  --config C:\pfad\zur\Suite --object CreateCompareView ^
rem                    --side A --env Demo --rtl Extensive --out clip
setlocal
set "HERE=%~dp0"
if not exist "%HERE%python\python.exe" (
  echo [Fehler] %HERE%python\python.exe fehlt.
  echo Erzeuge den portablen Python-Ordner einmalig auf einem Online-Rechner mit:
  echo   powershell -ExecutionPolicy Bypass -File scripts\make_portable_windows.ps1
  exit /b 1
)
"%HERE%python\python.exe" "%HERE%omrun-param-tool.pyz" %*
