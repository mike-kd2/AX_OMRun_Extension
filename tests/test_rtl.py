from omrun_paramtool.rtl import RunTimeList


def test_caption_mapping(comp_root):
    rtl = RunTimeList(
        comp_root / "ScriptGenerator/CreateCompareView/RunTimeList/Extensive.rtl"
    )
    pm = rtl.param_map()
    assert pm["@param1"] == "v_GetCompareQueryOra"
    assert pm["@param3"] == "DataCompare"
    assert pm["@param4"] == "//text()"


def test_multi_row_selection_by_number(comp_root):
    rtl = RunTimeList(
        comp_root / "ScriptGenerator/GetTableRowCount/RunTimeList/Extensive.rtl"
    )
    rows = rtl.rows()
    assert len(rows) == 3
    numbers = {r.number for r in rows}
    # jede Zeile ueber ihre Number eindeutig waehlbar
    for n in numbers:
        assert rtl.select_row(n).number == n


def test_default_row_is_first_active(selftest_root):
    rtl = RunTimeList(
        selftest_root
        / "Component1/TestDataObject1/RunTimeList/Extensive.rtl"
    )
    row = rtl.select_row()
    assert row.active
    assert row.values["@param1"] == "1,2,3,4,5"
