# Analysebericht OMrun Test-Configs (Deliverable 1)

Analysiert: zwei Test-Config-Baeume aus `OMRun Test Configuration/`
- `SelfTest/` (OMrun-Selbsttest, Excel-basiert)
- `Comp_ORA_PG/` (Migration/Vergleich Oracle -> PostgreSQL)

Alle Aussagen sind aus den Files belegt. Werte in Snippets sind anonymisiert/gekuerzt.

---

## 1. Ordnerstruktur, Dateitypen, Groessen

Beide Baeume folgen demselben OMrun-Projektlayout:

```
<Projekt>/TestScripts/<Suite>/
  Configuration/   *.cfg   (Provider-/Publish-Config, kein SQL-Param-Inhalt)
  Environment/     *.env   (Alias-Tabelle DbAlias -> Wert; Environment-Ebene)
  TestScenario/    *.tsc   (bindet TestObject -> RunTimeList-Variante)
  <Object>/        *.tob   (TestObject: enthaelt das SQL)
    RunTimeList/   *.rtl   (Parameterwerte @paramN pro Zeile)
    Result/        *.tor   (Ergebnis-Dumps, fuer das Tool irrelevant)
```

Dateityp-Inventar (Anzahl / Rolle):

| Ext   | n  | Rolle | Relevanz Tool |
|-------|----|-------|---------------|
| `.tob` | 13 | TestObject, **traegt das SQL** (`QueryA`/`QueryB`) | **Kern** |
| `.rtl` | 18 | RunTimeList, **Werte fuer `@paramN`** | **Kern** |
| `.env` |  5 | Environment, **Werte fuer `@DB_*`/`@SCHEMA_*`/OM-Variablen** | **Kern** |
| `.tsc` |  2 | TestScenario, Zuordnung Object->RTL-Variante | Kontext |
| `.cfg` |  6 | Provider/Publish-Config | nein |
| `.tor` |  2 | Ergebnis-Output | nein |
| `.xlsx`|  2 | Testdaten (SelfTest) | nein |
| `.bat` |  1 | Launcher | nein |

Groessen: `.tob` 9-18 KB, `.rtl` 3-16 KB, `.env` 2.7-6 KB. Alles klein, kein Streaming noetig.

---

## 2. XML-Struktur (mit konkreten Pfaden und Belegen)

### 2.0 Gemeinsames Dialekt-Fundament

Alle vier relevanten Typen sind **ADO.NET/.NET-`DataSet`-XML** (typed DataSet):
- `standalone="yes"`, Wurzel `DataSet<Typ>` im Default-Namespace `http://tempuri.org/DataSet<Typ>.xsd`.
- Zuerst ein Inline-`<xs:schema>` (Struktur + Captions), danach die Datenzeilen als wiederholte Elemente.
- **Konsequenz fuer lxml:** Datenelemente liegen im Default-Namespace (kein Prefix). XPath braucht eine Namespace-Map bzw. `local-name()`. Beim Schreiben nur das Ziel-Element anfassen, Rest des Baums unveraendert lassen.

### 2.1 Wo steht das SQL? (Frage a)

Im `.tob` unter zwei festen Elementen:

- Query Quelle: `/DataSetTestObject/ConfigurationA/QueryA`
- Query Ziel:   `/DataSetTestObject/ConfigurationB/QueryB`
- zugehoeriger DB-Alias je Query: `.../ConfigurationA/AliasDbA`, `.../ConfigurationB/AliasDbB`

Beleg (`SelfTest/.../Data_TestDataObject1.tob`):

```xml
<ConfigurationA>
  <AliasDbA>@DB_Quote</AliasDbA>
  <QueryA>SELECT 'Test1' AS Environment ... FROM [T_Quote$] Q WHERE Q.Id IN (@param1)</QueryA>
</ConfigurationA>
<ConfigurationB>
  <AliasDbB>@DB_Quote1</AliasDbB>
  <QueryB>SELECT '@ENV' AS Environment ... WHERE Q.Id IN (@param2)</QueryB>
  <Active>true</Active>
</ConfigurationB>
```

Das SQL ist der **reine Text-Content** dieser Elemente (keine Attribute, keine Kindknoten).

### 2.2 CDATA oder Entity-Escaping? (Frage b) -- entscheidend

**Kein einziges CDATA im gesamten Projekt** (`grep CDATA` -> 0 Treffer).
SQL wird als **entity-escapter Element-Text** abgelegt. `<`, `>`, `&` erscheinen als `&lt;`, `&gt;`, `&amp;`.

Beleg (`Comp_ORA_PG/.../GetTableRowCount/Data_GetTableRowCount.tob`, roh von Platte):

```xml
<QueryA>SELECT ...
    AND CAST(t.NUM_ROWS AS INT) &gt;= @param2 -- untere Row-Grenze
    AND CAST(t.NUM_ROWS AS INT) &lt;  @param3 -- obere Row-Grenze
ORDER BY first_key_data_type</QueryA>
```

Folge fuer Extraktion/Write-back: lxml entschaerft beim Lesen automatisch (`elem.text` liefert echtes `<`/`>`), und re-escapet beim Serialisieren. **Verlustfreier Round-Trip ist mit lxml gegeben**, solange nur `.text` des Ziel-Elements gesetzt und der Rest nicht neu formatiert wird. `strip_cdata=False` ist trotzdem sinnvoll fuer den Fall, dass kuenftig doch CDATA auftaucht.

### 2.3 Wie sind Parameter->Werte abgelegt? (Frage c)

Quelle der `@paramN`-Werte ist das `.rtl` (nicht das `.tob`). Zwei Stellen:

1. **Schema-Sektion** deklariert die Spalten und liefert die **explizite Zuordnung** Element -> Platzhaltername via `msdata:Caption`:

```xml
<xs:element name="_x0040_key1" msdata:Caption="@param1" type="xs:string" .../>
<xs:element name="_x0040_key2" msdata:Caption="@param2" type="xs:string" .../>
<xs:element name="_x0040_key3" msdata:Caption="@param3" type="xs:string" .../>
<xs:element name="_x0040_key4" msdata:Caption="@param4" type="xs:string" .../>
```

`_x0040_` ist das .NET-XML-Encoding fuer `@`; der Element-Localname ist also `@key1`, die **Caption ist der echte Platzhalter** `@param1`. Die Caption ist die autoritative Bindung (nicht auf N==N verlassen, Caption lesen).

2. **Datenzeile** `DataTableRunTime` traegt die Werte:

```xml
<DataTableRunTime>
  <Number>10</Number>
  <_x0040_key1>v_GetCompareQueryOra</_x0040_key1>
  <_x0040_key2>v_GetCompareQueryPg</_x0040_key2>
  <_x0040_key3>DataCompare</_x0040_key3>
  <_x0040_key4>//text()</_x0040_key4>
  <Remark>Create data compare view</Remark>
</DataTableRunTime>
```

Mapping-Regel: fuer jedes `_x0040_keyN` die `Caption` (= `@paramN`) aus dem Schema lesen, den Wert aus der gewaehlten `DataTableRunTime`-Zeile nehmen.

**Mehrere Zeilen moeglich:** `.rtl` kann mehrere `DataTableRunTime` enthalten (z. B. `GetTableRowCount/.../Extensive.rtl` = 3 Zeilen, `CreateTob/.../TableList.rtl` = 12 Zeilen). Ein Parameter-Set ist damit eindeutig erst ueber (`.rtl`-Datei + `<Number>`-Zeile). Hydrate muss die Zeile waehlen koennen.

### 2.4 Environment-Zuordnung (Frage d)

`@DB_*`, `@SCHEMA_*`, `@USER_*` sowie die OM-System-Variablen kommen aus `.env`. Jede `<Environment>`-Zeile ist ein Alias-Eintrag:

```xml
<Environment>
  <Server>localhost:1521</Server>
  <Db>@DB_Source_Name</Db>          <!-- Wert kann selbst ein Alias sein -> Kette -->
  <DbType>Oracle</DbType>
  <DbAlias>@DB_Source</DbAlias>     <!-- Schluessel -->
  ...
</Environment>
<Environment>
  <Db>demo_source</Db>
  <DbType>Omis Variable (OM)</DbType>
  <DbAlias>@SCHEMA_Source</DbAlias> <!-- @SCHEMA_Source -> demo_source -->
</Environment>
```

Erkenntnisse:
- **Schluessel** = `<DbAlias>`, **Wert** = kontextabhaengig `<Db>` (bei OM-Variablen/Schema) bzw. die Verbindung (Server/Db/DbType/User bei echten DBs).
- **Verkettung/Rekursion:** `@USER_Source` -> `<Db>@SCHEMA_Source</Db>` -> `demo_source`. Aliase koennen auf Aliase zeigen; Aufloesung muss iterativ/rekursiv sein (mit Zyklus-Schutz).
- **Layering:** pro Suite gibt es eine spezifische `.env` **plus** eine `Global.env`. Global definiert OM-System-Variablen (`@SCRIPT`, `@BSS`, `@ENV`, `@DATA`, `@REPORT`, ...), die auf `#OMrunProjectPath#\...`- bzw. `#OMrun...#`-Tokens zeigen.
- **Environment-Wahl = Wahl der spezifischen `.env`.** Comp: `Demo.env`. SelfTest: `TestEnvironment1.env` **oder** `TestEnvironment2.env` (zwei Environments als getrennte Dateien im selben Ordner).

Belegte Platzhalter-Klassen (Comp_ORA_PG/CreateCompareView, `grep '@...'`):
`@param1..4`, `@DB_Source`, `@DB_Target`, `@DB_Source_Name`, `@SCHEMA_Source`, `@SCHEMA_Target`, `@SCRIPT`, `@BSS`, sowie `@A_view_*` (siehe 2.6).

### 2.5 /*BODY*/-Marker (Frage e)

- Kommt **nicht ueberall** vor: nur in 3 von 13 `.tob` (`CreateCompareView`, `DropCompareView`, `SetCryptoConfig`). Der Marker ist also **optional** und muss so behandelt werden.
- Wo vorhanden, konsistent als eigene Zeile `/*BODY*/`. Darueber der Kopf-Query (erzeugt die Vergleichs-/Log-Spalten), darunter die eigentliche Migrationslogik.

Beleg (`CreateCompareView`, QueryA):

```sql
/* Original Oracle script for OMrun */
SELECT DISTINCT
    '@DB_Source_Name' AS view_catalog,
    '@SCHEMA_Source'  AS view_schema,
    'v_CreateCompareView' AS view_name
FROM dual

/*BODY*/
CREATE OR REPLACE VIEW @SCHEMA_Source.@param1 (...) AS
SELECT ...
```

Weiterer strukturgebender Marker: der fuehrende Kommentar `/* Original <Dialekt> script for OMrun */` als erste Zeile. Kein weiterer verbindlicher Marker gefunden. `@param3.@param4` bzw. `@SCHEMA_Source.@param1` bestaetigen das beschriebene `schema.objekt`-Muster (Objektbezeichner, nicht als T-SQL-Variable darstellbar).

### 2.6 Nicht-Substitutions-Platzhalter (Abgrenzung)

`@A_*` (z. B. `@A_view_catalog`, im SelfTest `@A_Environment`, `@A_Id`) sind **BusinessMapping-Rule-Aliase** aus `.tob/BusinessMapping/Rule` bzw. `TabAliasA/AliasA`. Sie sind OMrun-interne Spaltenzuordnungen fuer den Vergleich, **keine** Ziele fuer die SQL-Hydration. Beleg (`.tob`):

```xml
<TabAliasA><AliasA_Id>1</AliasA_Id><NameA>SourceA.Id</NameA><AliasA>A_Id</AliasA></TabAliasA>
<BusinessMapping>...<Rule>@A_Id</Rule>...</BusinessMapping>
```
-> Diese Klasse muss das Tool erkennen und **bewusst nicht** ersetzen (sonst zerstoert Dehydrate die Rules).

---

## 3. Strukturelle Unterschiede zwischen den beiden Ordnern

| Merkmal | SelfTest | Comp_ORA_PG | Tool-Konsequenz |
|---|---|---|---|
| Zweck | Selbsttest, Excel | Migration ORA->PG | -- |
| `@paramN` | 2 (`@param1/2`) | bis 4 (`@param1..4`) | N variabel, dynamisch aus Schema |
| `/*BODY*/` | fehlt | teils vorhanden | Marker optional |
| Escaped SQL-Operatoren | keine im SQL | `&gt;`, `&lt;` im SQL | Escaping zwingend verlustfrei |
| `.env` | 1 Alias-Quelle (`@DB_Quote`/`@DB_Quote1`, beide Excel) + Global | Oracle+PG dual, `@SCHEMA_*`, `@USER_*`, Ketten + Global | Aufloesung: rekursiv + Layering |
| Environments | `TestEnvironment1.env`, `TestEnvironment2.env` (getrennt) | `Demo.env` | Environment = Datei-Wahl |
| `.rtl`-Varianten | 5 (Adhoc/Extensive/Regression/Sample/Smoke) | meist nur `Extensive` (+ `TableList`) | Variante = Datei-Wahl |
| Multi-Row `.rtl` | 1 Zeile | bis 12 Zeilen | Zeilen-Wahl via `<Number>` |
| Versionsstrings | Dataset 5.1.0.2 / cfg 5.6 | Dataset 5.1.0.2 / cfg 5.5 | nur informativ |

**Wichtig:** Trotz dieser Unterschiede ist der **XML-Dialekt identisch** (gleiche Wurzeln, gleiche Element-Namen `ConfigurationA/QueryA`, `DataTableRunTime/_x0040_keyN`, `Environment/DbAlias`). Ein einziger Parser deckt beide Baeume ab; die Unterschiede sind Daten-, nicht Strukturunterschiede.

---

## 4. Offene Punkte / Ambiguitaeten (bitte entscheiden, statt dass ich rate)

1. **Env-Layering-Praezedenz:** `@DB_Source`/`@DB_Target` sind in `Global.env` (PostgreSQL, localhost:5433) **und** in `Demo.env` (Oracle bzw. PG, andere Ports) mit unterschiedlichen Werten definiert. Welche Ebene gewinnt? Vermutung: spezifische `.env` ueberschreibt `Global.env`. Bitte OMrun-Regel bestaetigen (Override vs. `<Number>`-Reihenfolge).

2. **Was ist der "Wert" eines Alias fuer die Hydration?** Fuer `@SCHEMA_Source` klar `<Db>` = `demo_source`. Fuer echte Verbindungs-Aliase (`@DB_Source`, DbType Oracle) ist unklar, ob im SQL der `<Db>`-Name, der Server oder gar nichts eingesetzt werden soll. Fuer SSMS/Cursor-Entwicklung brauchst du real vermutlich nur die **Schema-/Objektnamen** (`@SCHEMA_*`, `@paramN`), nicht die Connection-Aliase. Bestaetigst du: Connection-Aliase (`@DB_*`) werden **nicht** in den SQL-Text hydriert?

3. **OM-System-Variablen** (`@SCRIPT`, `@BSS`, `@ENV`, `@DATA`, ...) loesen auf `#OMrunProjectPath#\...`-Tokens auf, also nicht auf echte DB-Werte. Sollen die (a) unveraendert bleiben, (b) auf die `#...#`-Tokens hydriert werden, oder (c) ueber eine kleine Zusatz-Config auf lokale Pfade gemappt werden? Fuer reine Query-Entwicklung wuerde ich sie unangetastet lassen.

4. **Header vs. Body:** Entwickelst du typischerweise nur den Teil **unter** `/*BODY*/`, waehrend der Kopf konstantes Template bleibt? Default-Verhalten von `hydrate`/`dehydrate`: ganzer Query oder nur Body? (Ich wuerde `--body-only` als Option vorsehen, Default = ganzer Query.)

5. **`@A_*`-Klasse:** Bestaetigung, dass BusinessMapping-/Alias-Rules (`@A_*`) grundsaetzlich **nie** hydriert/dehydriert werden (nur `@paramN` und die Environment-Aliase gemaess Punkt 2/3).

6. **Dehydrate-Risiko konkret:** Werte wie `@param4 = //text()` oder `@param3 = DataCompare` sind gewoehnliche Strings, die auch als Literal im SQL vorkommen koennten. Bestaetigst du die Strategie: nur Whole-Token-Ersetzung, longest-match-first, ausschliesslich bekannte Werte der aktiven Map, und im Zweifel Konflikte melden statt still ersetzen?

---

## 5. Fazit fuer die Architektur (Vorschau, Details in Deliverable 2)

- **Eine** Parser-Schicht (lxml, `strip_cdata=False`) fuer alle DataSet-XML; Zugriff ueber Namespace-Map bzw. `local-name()`.
- **Param-Map** speist sich aus drei Quellen mit klaren Zustaendigkeiten: `.tob` (SQL + AliasDb + `@A_*`-Ausschlussliste), `.rtl` (`@paramN` via Caption, zeilenweise), `.env` (`@DB_*`/`@SCHEMA_*`/OM, rekursiv, gelayert).
- **Selektoren** fuer eindeutige Aufloesung: (Suite, TestObject, Environment=`.env`, RunTimeList=`.rtl`, Row=`<Number>`).
- **Write-back-tauglich by design:** nur `elem.text` des Ziel-Query-Elements ersetzen, Restbaum unveraendert -> verlustfreies Escaping.

---

Ende Deliverable 1. Ich stoppe hier und warte auf dein OK, bevor ich den Architekturvorschlag (Deliverable 2) ausarbeite.
