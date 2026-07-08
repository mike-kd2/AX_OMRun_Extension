Wheelhouse -- Offline-Paketquelle fuer die OPTIONALEN Extras.

Enthaltene Wheels:
  omrun_param_tool-*.whl   das Tool selbst (py3-none-any, ueberall lauffaehig)
  pyperclip-*.whl          Zwischenablage (pure python, ueberall lauffaehig)
  lxml-*-cp311-win_amd64   lxml fuer Windows x64, Python 3.11
  lxml-*-cp312-win_amd64   lxml fuer Windows x64, Python 3.12

Zielsystem: Windows Server 2022 x64 (win_amd64), Python 3.11 oder 3.12 (64-bit).

Offline-Installation auf dem airgapped Server (Repo/Wheelhouse mitkopieren):
  pip install --no-index --find-links wheelhouse "omrun-param-tool[lxml,clipboard]"

Nur Zwischenablage ohne lxml:
  pip install --no-index --find-links wheelhouse "omrun-param-tool[clipboard]"

Hinweis: lxml ist plattform-/Python-versions-spezifisch. Fuer eine andere
Windows-Python-Version oder Plattform neu bauen mit:
  scripts/build_wheelhouse.sh  win_amd64:313      (Beispiel Python 3.13)
Das Tool-Wheel bei Codeaenderungen ebenfalls neu bauen (gleiches Skript).

Kernbetrieb OHNE Wheelhouse ist weiterhin moeglich: das Tool laeuft rein auf der
Python-Standardbibliothek (siehe README, Abschnitt "Betrieb auf airgapped Server").
