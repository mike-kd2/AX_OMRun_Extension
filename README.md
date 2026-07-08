# OMrun Param-Tool

Lokales CLI, das OMrun-SQL (mit Platzhaltern wie `@param1`, `@SCHEMA_Source`)
gegen die Werte aus den OMrun-XML-Configs **hydriert** (fuer die Entwicklung in
SSMS/Cursor) und wieder **dehydriert** (zurueck in die parametrisierte Form).

Die Werte kommen direkt aus den Configs (`.tob`, `.rtl`, `.env`), nicht aus einer
separaten Mapping-Datei -> kein Drift. Rein lokal, keine Netzwerk-/DB-Aufrufe,
airgapped lauffaehig.

Stand: **Stufe 1** (`inspect` / `hydrate` / `dehydrate` ueber stdin/stdout bzw.
Zwischenablage). Kein Write-back in OMrun-Files (das ist Stufe 2).

## Voraussetzung

Nur **Python 3.10+**. Der Kern laeuft ohne jede externe Abhaengigkeit auf der
Python-Standardbibliothek -- ideal fuer airgapped Server (nichts zu installieren,
kein Netzwerk noetig).

Optional: `lxml` (bessere Serialisierungstreue fuer den spaeteren Write-back) und
`pyperclip` (Zwischenablage). Ohne diese Pakete funktioniert alles ausser dem
`clip`-Modus.

## Voll portabel (KEIN Python installiert, kein Admin)

Wenn auf dem Server gar kein Python vorhanden ist und nichts installiert werden
darf: portables "embeddable" Python (nur entpacken, keine Installation) + das
Tool als Single-File-App. Ablauf:

1. **Einmalig auf einem Rechner MIT Internet** (dein Laptop reicht) den portablen
   Ordner bauen -- er laedt das embeddable Python von python.org und bindet die
   Wheelhouse-Extras ein:

   ```
   # Windows-Online-Rechner:
   powershell -ExecutionPolicy Bypass -File scripts\make_portable_windows.ps1
   # oder Linux/macOS-Online-Rechner (erzeugt trotzdem den Windows-Interpreter):
   scripts/make_portable_windows.sh
   ```

   Ergebnis: `portable\` mit `python\` (portabler Interpreter), `omrun-param-tool.pyz`
   und `run-portable.cmd`.

2. **Den Ordner `portable\` komplett auf den airgapped Windows-Server kopieren**
   (gleicher Transferweg wie fuer das restliche Repo).

3. **Dort ohne Installation ausfuehren:**

   ```
   .\portable\run-portable.cmd inspect --config <suite>
   .\portable\run-portable.cmd hydrate --config <suite> --object CreateCompareView ^
        --side A --env Demo --rtl Extensive --out clip
   ```

Hinweis: Den Interpreter (`python.org`-ZIP) kann nur ein Online-Rechner ziehen --
das ist der einzige einmalige Online-Schritt. `portable\omrun-param-tool.pyz` und
`run-portable.cmd` liegen bereits im Repo; nur der Ordner `portable\python\` wird
vom Skript erzeugt.

## Betrieb auf airgapped Server (wenn Python vorhanden ist)

Drei Wege, alle netzwerkfrei:

**A) Launcher (empfohlen)** -- Repo klonen/kopieren, dann direkt:

```bash
./omrun-param-tool inspect --config <suite>          # Linux/macOS
omrun-param-tool.cmd inspect --config <suite>        # Windows
```

**B) Als Modul** -- ohne Wrapper:

```bash
PYTHONPATH=src python -m omrun_paramtool inspect --config <suite>
```

**C) Ein einzelnes File** -- Zipapp bauen (einmalig, offline) und verteilen:

```bash
python scripts/build_pyz.py
python dist/omrun-param-tool.pyz inspect --config <suite>
```

Das `.pyz` ist selbst-enthalten (reine Standardbibliothek) und laeuft auf jedem
Python 3.10+.

### Optionaler venv (nur wenn du lxml/pyperclip willst)

```bash
scripts/bootstrap.sh            # Kern (keine externen Deps)
scripts/bootstrap.sh --extras   # + lxml + pyperclip (braucht einmalig Netz/Wheels)
# Windows:
powershell -ExecutionPolicy Bypass -File scripts\bootstrap.ps1 [-Extras]
```

### XML-Backend

Automatisch: `lxml` falls vorhanden, sonst Standardbibliothek. Erzwingbar via
Umgebungsvariable `OMRUN_XML_BACKEND=stdlib` bzw. `=lxml`.

### Optionale Extras via Wheelhouse (offline)

Wenn du die optionalen Pakete (`lxml`, `pyperclip`) auf dem airgapped Server
willst, liegt unter `wheelhouse/` eine Offline-Paketquelle bereit (Windows x64,
Python 3.11/3.12). Installation ohne Netzwerk:

```
pip install --no-index --find-links wheelhouse "omrun-param-tool[lxml,clipboard]"
```

`lxml` ist plattform-/Python-versions-spezifisch. Fuer eine andere Zielumgebung
das Wheelhouse neu bauen (auf einem Rechner mit Netz):

```
scripts/build_wheelhouse.sh win_amd64:312           # Windows x64, Python 3.12
scripts/build_wheelhouse.sh manylinux2014_x86_64:311 # Linux x64, Python 3.11
# Windows: powershell -File scripts\build_wheelhouse.ps1 win_amd64:312
```

Details: `wheelhouse/README.txt`.

## Konzepte

- **Config-Wurzel** (`--config`): eine OMrun-Suite (enthaelt `Environment/` und
  darunter die Objekt-Ordner mit `.tob` + `RunTimeList/`).
- **TestObject** (`--object`): das `.tob` mit `QueryA` (Source) und `QueryB` (Target).
- **Seite** (`--side A|B|both`): welcher Query.
- **Environment** (`--env`): die spezifische `.env`; `Global.env` wird immer dazugeladen.
- **RunTimeList** (`--rtl`) + **Number** (`--number`): liefert die `@paramN`-Werte
  (eine `.rtl` kann mehrere Zeilen haben).
- **Segment** (`--part body|header|full`): am `/*BODY*/`-Marker. Default `body`;
  ohne Marker Fallback auf den ganzen Query.

### Was wird ersetzt

| Klasse | Beispiel | Quelle | hydriert? |
|---|---|---|---|
| Parameter | `@param1` | `.rtl` (Caption) | ja |
| Schema/User | `@SCHEMA_Source`, `@USER_Source` | `.env` (rekursiv) | ja |
| Connection-Alias | `@DB_Source` | `.env` | nein (bleibt stehen) |
| OM-System-Var | `@SCRIPT`, `@BSS`, `@ENV` | `Global.env` | nein (bleibt stehen) |

## Verwendung

```bash
# Ueberblick: Objekte + Environments
omrun-param-tool inspect --config <suite>

# Aufgeloeste ParamMap pruefen (Werte, Herkunft, Aufloesungsketten)
omrun-param-tool inspect --config <suite> --object CreateCompareView \
    --side A --env Demo --rtl Extensive

# Hydrate: Body -> lauffaehiges SQL in die Zwischenablage
omrun-param-tool hydrate --config <suite> --object CreateCompareView \
    --side A --env Demo --rtl Extensive --out clip

# Dehydrate: entwickeltes SQL (Zwischenablage) -> parametrisiert
omrun-param-tool dehydrate --config <suite> --object CreateCompareView \
    --side A --env Demo --rtl Extensive --in clip --out clip
```

`--out`/`--in`: `-` = stdout/stdin (Default), `clip` = Zwischenablage.

## Dehydrate-Sicherheit (wichtig)

Dehydrate ersetzt **nur** Whole-Token-Treffer, longest-value-first, und nur
**sichere, eindeutige** Werte. Bewusst **nicht** automatisch zurueckgesetzt werden:

- Werte mit Whitespace/Sonderzeichen (z.B. `//text()`, `1,2,3,4,5`).
- Zu kurze Werte (z.B. `*`) -> schuetzt `SELECT *` vor Zerstoerung.
- Mehrfach vorkommende Werte (z.B. ein Schema-Name an 5 Stellen) -> gemeldet,
  nur mit `--force` ersetzt.

Solche Faelle werden auf stderr **gemeldet**, nicht still veraendert. Das heisst:
ein Hydrate->Dehydrate-Durchlauf ist bewusst **nicht** immer verlustfrei -- die
Sicherheit gegen Fehlersetzungen hat Vorrang. Uebersprungene Tokens ggf. manuell
oder mit `--force` (nach Sichtpruefung) nachziehen.

## Tests

```
python -m pytest
```

Die Tests laufen gegen anonymisierte Demo-Configs unter `tests/fixtures/configs/`.

## Roadmap

- **Stufe 2:** `writeback` des entwickelten Body direkt in den `.tob`-Node
  (das verlustfreie `elem.text`-Schreiben ist bereits implementiert und getestet).
  Vorher zu klaeren: OMrun-File-Locking/Caching (Write-back nur bei geschlossenem OMrun).

## Offene Verifikationspunkte

- `.env`-Layering-Praezedenz in OMrun real (Annahme: spezifische `.env` gewinnt,
  schaltbar via `--env-precedence`).
- Exaktes Wertfeld pro `DbType` bei der Alias-Aufloesung (aktuell `Db`, sonst `Server`).

Details siehe `docs/01_Analysebericht.md` und `docs/02_Architektur.md`.
