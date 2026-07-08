Portabler Betrieb -- KEIN installiertes Python, kein Admin.

Inhalt (im Repo):
  omrun-param-tool.pyz   das Tool als Single-File-App (reine stdlib, laeuft ueberall)
  run-portable.cmd       Launcher: nutzt python\ neben dieser Datei
  python\                NICHT im Repo -- einmalig erzeugt (siehe unten)

So machst du es lauffaehig:

1) EINMALIG auf einem Rechner MIT Internet (Laptop reicht) den Interpreter holen:
     powershell -ExecutionPolicy Bypass -File ..\scripts\make_portable_windows.ps1
   (oder von Linux/macOS aus:  ../scripts/make_portable_windows.sh)
   Das laedt das embeddable Python von python.org nach python\ und bindet die
   Wheelhouse-Extras (lxml, pyperclip) ein.

2) Den GESAMTEN Ordner portable\ auf den airgapped Windows-Server kopieren.

3) Dort ohne Installation:
     .\portable\run-portable.cmd inspect --config <suite>

Warum python\ nicht im Repo liegt: der Interpreter ist gross und
plattformspezifisch und laesst sich nur von einem Online-Rechner (python.org)
beziehen. Alles andere ist bereits versioniert.

Tool-Code geaendert? Dann das .pyz neu bauen:  python scripts\build_pyz.py
