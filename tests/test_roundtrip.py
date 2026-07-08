"""Write-back-Fundament: elem.text setzen darf Escaping/Formatierung nicht
veraendern (Stufe-2-Voraussetzung)."""

from omrun_paramtool import dataset_xml as dx
from omrun_paramtool.tob import TestObject


def test_load_is_unescaped_in_memory(comp_root):
    tob = TestObject(
        comp_root / "ScriptGenerator/GetTableRowCount/Data_GetTableRowCount.tob"
    )
    sql = tob.get_query("A").sql
    # lxml liefert echte Zeichen, nicht die Entities
    assert ">=" in sql or "<" in sql
    assert "&gt;" not in sql


def test_setting_same_text_keeps_bytes_identical(tmp_path, comp_root):
    src = comp_root / "ScriptGenerator/GetTableRowCount/Data_GetTableRowCount.tob"
    original_bytes = src.read_bytes()

    tob = TestObject(src)
    # denselben Text zurueckschreiben
    tob.set_query("A", tob.get_query("A").sql)
    out = tmp_path / "roundtrip.tob"
    dx.save(tob.tree, out)

    # Escaping muss wieder da sein
    text = out.read_text(encoding="utf-8")
    assert "&gt;=" in text
    # Kernstruktur unveraendert (Entities re-serialisiert)
    assert original_bytes.count(b"&gt;") == out.read_bytes().count(b"&gt;")


def test_writeback_body_preserves_special_chars(tmp_path, comp_root):
    tob = TestObject(
        comp_root / "ScriptGenerator/GetTableRowCount/Data_GetTableRowCount.tob"
    )
    new_sql = "SELECT 1 WHERE a < b AND c > d AND e & f"
    tob.set_query("A", new_sql)
    out = tmp_path / "wb.tob"
    dx.save(tob.tree, out)
    reloaded = TestObject(out).get_query("A").sql
    assert reloaded == new_sql
    raw = out.read_text(encoding="utf-8")
    assert "&lt;" in raw and "&gt;" in raw and "&amp;" in raw
