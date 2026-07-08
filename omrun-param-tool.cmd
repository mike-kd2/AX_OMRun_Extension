@echo off
rem Launcher ohne Installation (Windows): setzt PYTHONPATH auf src\ und ruft das Modul.
rem Nutzung: omrun-param-tool.cmd hydrate --config ... (siehe README)
rem Python via %PYTHON% ueberschreibbar (Default: python).
setlocal
set "HERE=%~dp0"
if "%PYTHON%"=="" set "PYTHON=python"
set "PYTHONPATH=%HERE%src;%PYTHONPATH%"
"%PYTHON%" -m omrun_paramtool %*
