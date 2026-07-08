# Architekturvorschlag OMrun Param-Tool (Deliverable 2)

Basierend auf Analysebericht (Deliverable 1) und deinen Entscheidungen zu den offenen Punkten.

Fixierte Entscheidungen:
1. Hydrate ersetzt **nur** `@paramN` (aus `.rtl`) und `@SCHEMA_*` / `@USER_*` (aus `.env`, rekursiv). `@DB_*`, OM-System-Variablen (`@SCRIPT`/`@BSS`/`@ENV`/...) und `@A_*` bleiben unangetastet.
2. Segment-Default = **Body**; Header/Body/Full waehlbar. Body muss **eigenstaendig lauffaehig** sein (nur Body raus -> nur Body laeuft). Kontrolllisten haben oft nur Header (kein Body), Source A/B zeigen dort auf dieselbe DB.
3. `.env`-Layering-Praezedenz noch **unklar** -> Annahme "spezifische `.env` gewinnt vor `Global.env`", als Config schaltbar, im Output transparent gemacht, spaeter zu verifizieren.
4. `@A_*` bewusst weggelassen (keine Sonderbehandlung noetig, siehe Punkt 5).
5. Dehydrate: nur Whole-Token, longest-match-first, nur bekannte In-Scope-Werte, Konflikte melden statt still ersetzen.
6. Multi-Row `.rtl`: Zeilenwahl per `--number N`, Default = erste aktive Zeile.

---

## 1. Datenmodell der Param-Map

### 1.1 Selektoren (identifizieren einen Substitutions-Kontext eindeutig)

```
Context = (
  config_root,        # Wurzel einer Suite, z.B. .../TestScripts/<Suite>
  tob,                # TestObject-Datei (.tob)
  side,               # A | B | both     (QueryA/AliasDbA  bzw. QueryB/AliasDbB)
  env,                # Name der spezifischen .env (z.B. "Demo", "TestEnvironment1")
  rtl,                # Name der .rtl-Variante (z.B. "Extensive")
  number,             # <Number> der DataTableRunTime-Zeile (Default: erste aktive)
)
```

`Global.env` wird immer als Basis-Layer dazugeladen (nicht als Selektor).

### 1.2 ParamMap (Ergebnis der Aufloesung)

Geordnete Liste von Eintraegen, longest-value-first sortierbar:

```
Entry = {
  token:     str,        # z.B. "@param1", "@SCHEMA_Source"
  value:     str,        # aufgeloester Literalwert, z.B. "v_GetCompareQueryOra", "demo_source"
  cls:       "param" | "env_schema",
  in_scope:  bool,       # True = wird hydriert/dehydriert
  source:    str,        # Herkunft (Datei + XPath/Row) fuer Transparenz
  resolved_via: [str],   # Aufloesungskette bei rekursiven env-Aliasen
  safe_dehydrate: bool,  # False bei riskanten Werten (z.B. "*", "1,2,3", "//text()")
}
```

Klassifikation:
- `param`: Token stammt aus einer `.rtl`-Caption (`msdata:Caption="@paramN"`). Immer `in_scope`.
- `env_schema`: `.env`-`DbAlias`, dessen Name auf der Whitelist `@SCHEMA_*` / `@USER_*` steht. `in_scope`.
- Alle anderen Aliase (`@DB_*`, `@SCRIPT`, `@BSS`, ...) werden zwar zur **Aufloesung** genutzt (Ketten), aber `in_scope = False` -> nicht in den SQL-Text eingesetzt.

`safe_dehydrate = False`, wenn der Wert kein plausibler Objektbezeichner ist (enthaelt Whitespace/Komma/Wildcard `*`/Slashes, oder Laenge < konfig. Minimum, oder Wert ist im aktuellen Map-Set nicht eindeutig). Solche Eintraege werden bei Dehydrate **nicht automatisch** ersetzt, sondern gemeldet.

---

## 2. Extraktions- und Ersetzungslogik

### 2.1 XML-Zugriff (`dataset_xml.py`)
- lxml, `etree.XMLParser(strip_cdata=False, remove_blank_text=False)`.
- Namespace-Handling ueber `local-name()`-XPath, damit Default-Namespace der DataSets kein Prefix-Gefummel erzwingt.
- **Write-back-Prinzip (schon jetzt vorbereitet):** ausschliesslich `elem.text` des Ziel-Elements setzen, nie den Baum neu serialisieren-und-ersetzen. Damit bleiben Escaping (`&lt;`/`&gt;`/`&amp;`), Formatierung und alle uebrigen Knoten unveraendert. Round-Trip-Test als Pflicht-Testfall.

### 2.2 TestObject (`tob.py`)
- Liest `ConfigurationA/QueryA` + `AliasDbA`, `ConfigurationB/QueryB` + `AliasDbB` (via `local-name()`).
- Liefert Roh-SQL (bereits von lxml entschaerft, echte `<`/`>`).

### 2.3 Segmentierung (`segments.py`)
- Marker: exakt `/*BODY*/` auf eigener Zeile.
- Wenn vorhanden: `header` = alles davor, `body` = alles danach, `marker` = die Zeile.
- Wenn nicht vorhanden: `header` = ganzer Text, `body` = leer.
- `--part`:
  - `body` (Default): gibt nur den Body zurueck; existiert kein Body -> Fallback auf `header` mit Hinweis.
  - `header`: nur der Kopf (Kontrolllisten-Fall).
  - `full`: Kopf + Marker + Body verbatim.
- Garantie: `header + marker + body == Originaltext` (verlustfreie Rekombination fuer Write-back in Stufe 2).

### 2.4 RunTimeList (`rtl.py`)
- Aus Schema: Map `element_localname (_x0040_keyN) -> Caption (@paramN)`.
- Aus gewaehlter `DataTableRunTime`-Zeile (`--number`, sonst erste mit `Active=true`): Wert je Element.
- Ergebnis: `@paramN -> value`.

### 2.5 Environment (`env.py`)
- Laedt spezifische `.env` + `Global.env`, baut `DbAlias -> Environment-Row`.
- Praezedenz: spezifisch ueberschreibt Global (schaltbar `--env-precedence specific|global`), Default `specific` (Annahme, markiert).
- Wertfeld eines Alias: `<Db>` falls gesetzt, sonst `<Server>` (fuer OM-Variablen).
- **Rekursive Aufloesung** mit Zyklus-Schutz und Max-Tiefe: ist der Wert selbst ein `@`-Token, weiter aufloesen (z.B. `@USER_Source -> @SCHEMA_Source -> demo_source`). Kette in `resolved_via` protokolliert.
- In die ParamMap gelangen nur Aliase, deren **Name** der Whitelist entspricht (`@SCHEMA_*`, `@USER_*`); die Aufloesung darf aber durch beliebige Aliase laufen.

### 2.6 Hydrate (`hydrate.py`)
1. Context aufloesen -> ParamMap (nur `in_scope`-Eintraege aktiv).
2. Segment gemaess `--part` waehlen.
3. Token -> Wert ersetzen. Da Tokens eindeutig mit `@` beginnen und per Regex `@name`-begrenzt sind, ist die Hydrate-Richtung kollisionsarm. `@SCHEMA_Source.@param1` -> `demo_source.v_GetCompareQueryOra` (zwei unabhaengige Token-Ersetzungen).
4. Ausgabe nach stdout oder Zwischenablage.
5. Nicht aufgeloeste `@`-Tokens im Output werden als Warnung gelistet (z.B. verbleibende `@DB_*`/OM-Variablen -- erwartet -- vs. unerwartete Unbekannte).

### 2.7 Dehydrate (`dehydrate.py`)
1. Denselben Context/ParamMap aufbauen (gleiche Selektoren wie beim Hydrate).
2. Kandidaten = `in_scope`-Eintraege mit `safe_dehydrate = True`, sortiert longest-value-first.
3. Wert -> Token nur als Whole-Token (Boundary-Regex, `re.escape` auf Wert), keine Teilstring-Treffer.
4. Konfliktbehandlung (melden, nicht still ersetzen):
   - Wert kommt 0x vor -> Info (Parameter evtl. nicht genutzt).
   - Wert kommt mehrfach vor -> Warnung mit Positionen, Ersetzung nur nach `--force` oder interaktiver Bestaetigung.
   - Zwei Map-Werte sind identisch/ueberlappen -> Warnung, kein Auto-Ersatz.
   - `safe_dehydrate = False` (z.B. `*`, `1,2,3,4,5`, `//text()`) -> standardmaessig uebersprungen, im Report aufgefuehrt.
5. Ausgabe + Report (welche Tokens gesetzt, welche uebersprungen, welche Konflikte).

### 2.8 Inspect (`inspect`, read-only Transparenz)
- Listet verfuegbare Objects/Envs/RTLs/Rows und die aufgeloeste ParamMap (Token, Wert, Klasse, Herkunft, Aufloesungskette, safe-Flag), ohne SQL auszugeben. Hilft, den richtigen Context zu waehlen und Aufloesung zu pruefen.

---

## 3. CLI-Interface

Basis-Kommando `omrun` (bzw. `python -m omrun_paramtool`).

```
omrun inspect   --config <root> [--object <tob>] [--env <name>] [--rtl <name>]
omrun hydrate   --config <root> --object <tob> [--side A|B|both]
                --env <name> --rtl <name> [--number N]
                [--part body|header|full] [--out -|clip]
omrun dehydrate --config <root> --object <tob>
                --env <name> --rtl <name> [--number N]
                [--in -|clip] [--out -|clip] [--force]
```

Optionen:
- `--config` Suite-Wurzel (dort liegen `Environment/`, und darunter die Objekt-Ordner mit `.tob` + `RunTimeList/`).
- `--object` Name oder Pfad des `.tob` (Auto-Discovery, wenn eindeutig).
- `--side` Default `A`; `both` fuer Kontrolllisten-Vergleich.
- `--env` / `--rtl` Namen ohne Endung; `Global.env` implizit.
- `--number` Row-Wahl (Default erste `Active=true`).
- `--part` Default `body`.
- `--in/--out` `-` = stdin/stdout (Default), `clip` = Zwischenablage (optionales `pyperclip`).
- `--env-precedence` `specific` (Default) | `global`.
- Global: `--dry-run`, `--verbose` (Herkunft/Ketten), `--quiet` (keine Werte ausser Ergebnis, fuer sensible Umgebungen).

Exit-Codes: 0 ok, 2 Nutzungsfehler, 3 ungeloeste/mehrdeutige Tokens (bei `--strict`).

Ausgabe-Disziplin (airgapped/sensibel): Werte nur im hydrierten SQL bzw. bei `inspect`/`--verbose`. Fehlermeldungen nennen Tokens, nicht zwangslaeufig Werte.

---

## 4. Repo-Layout (GitLab-tauglich, versionierbar)

```
.
├── README.md
├── pyproject.toml                 # Deps: lxml; optional: pyperclip. Python 3.10+
├── .gitignore
├── docs/
│   ├── 01_Analysebericht.md
│   └── 02_Architektur.md
├── src/omrun_paramtool/
│   ├── __init__.py
│   ├── __main__.py                # python -m omrun_paramtool
│   ├── cli.py                     # argparse, keine Schwergewichte
│   ├── dataset_xml.py             # lxml load/save, local-name()-Helfer, safe text write
│   ├── tob.py                     # QueryA/B, AliasDbA/B
│   ├── rtl.py                     # @paramN via Caption, Row-Wahl
│   ├── env.py                     # Alias-Tabelle, rekursive Aufloesung, Layering
│   ├── segments.py                # header/body/full + /*BODY*/-Marker
│   ├── parammap.py                # Context -> ParamMap, Klassifikation, Scope, safe-Flags
│   ├── hydrate.py
│   ├── dehydrate.py
│   ├── clipboard.py               # pyperclip optional, stdin/stdout Fallback
│   └── errors.py
└── tests/
    ├── fixtures/                  # anonymisierte Teilmenge beider Configs (SelfTest + Comp_ORA_PG)
    ├── test_segments.py           # Marker vorhanden/fehlend, Rekombination verlustfrei
    ├── test_rtl.py                # Caption-Mapping, Multi-Row
    ├── test_env.py                # Rekursion, Zyklus, Layering-Praezedenz
    ├── test_roundtrip.py          # tob laden -> text setzen -> Escaping/Format unveraendert
    ├── test_hydrate.py
    └── test_dehydrate.py          # Whole-Token, longest-first, Konflikt-/Safe-Faelle (*, //text())
```

Abhaengigkeiten bewusst minimal: `lxml` (Pflicht), `pyperclip` (optional, nur fuer `clip`). Keine Netzwerkaufrufe, kein DB-Zugriff. Airgapped lauffaehig.

---

## 5. Abgrenzung Stufe 1 vs. Stufe 2

- **Stufe 1 (naechster Schritt nach deinem OK):** `inspect`, `hydrate`, `dehydrate` ueber stdin/stdout + Zwischenablage. Kein Schreiben in OMrun-Files. Die verlustfreie `elem.text`-Write-Logik wird aber schon implementiert und getestet (Fundament fuer Stufe 2).
- **Stufe 2 (spaeter, separat):** `writeback` des entwickelten Body direkt in den `QueryA`/`QueryB`-Node der `.tob`. Vorher zu klaeren: ob OMrun die XML live liest oder offen/gecached haelt (Write-back nur bei geschlossenem OMrun; ggf. Lock-Datei-Check/Backup vor Schreiben).

---

## 6. Noch zu verifizieren (blockiert Stufe 1 nicht)
- `.env`-Layering-Praezedenz real in OMrun (Annahme: spezifisch gewinnt).
- Exaktes Wertfeld pro DbType bei Aufloesung (aktuell `Db` -> sonst `Server`); an weiteren Environments gegenpruefen.
- Ob `--side both` fuer Kontrolllisten eine kombinierte Ausgabe braucht oder zwei getrennte Bloecke.

---

Ende Deliverable 2. Ich stoppe und warte auf dein OK, bevor ich Stufe 1 implementiere.
