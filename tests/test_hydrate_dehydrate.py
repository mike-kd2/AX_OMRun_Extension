from omrun_paramtool import segments as seg
from omrun_paramtool.dehydrate import dehydrate
from omrun_paramtool.env import Environment
from omrun_paramtool.hydrate import hydrate
from omrun_paramtool.parammap import build
from omrun_paramtool.rtl import RunTimeList
from omrun_paramtool.tob import TestObject


def _ctx(comp_root, obj="CreateCompareView", side="A"):
    tob = TestObject(
        comp_root / f"ScriptGenerator/{obj}/Data_{obj}.tob"
    )
    rtl = RunTimeList(
        comp_root / f"ScriptGenerator/{obj}/RunTimeList/Extensive.rtl"
    )
    env = Environment.load(
        specific=comp_root / "Environment/Demo.env",
        global_env=comp_root / "Environment/Global.env",
    )
    return build(tob, side, rtl, env)


def test_hydrate_replaces_scoped_tokens(comp_root):
    sql, pmap = _ctx(comp_root)
    body, _, _ = seg.select(sql, "body")
    res = hydrate(body, pmap)
    assert "demo_source.v_GetCompareQueryOra" in res.text
    assert "@param1" not in res.text
    assert "@SCHEMA_Source" not in res.text
    # nicht-Scope-Tokens bleiben stehen
    assert "@SCRIPT" in res.text


def test_token_boundary_no_overshoot():
    # @param1 darf nicht in @param12 hineinersetzen
    from omrun_paramtool.parammap import Entry, ParamMap

    pmap = ParamMap(
        entries=[Entry("@param1", "X", "param", True, "t")],
        unresolved_env=[],
    )
    res = hydrate("a @param1 b @param12 c", pmap)
    assert res.text == "a X b @param12 c"


def test_dehydrate_skips_unsafe_and_reports_conflict(comp_root):
    sql, pmap = _ctx(comp_root)
    body, _, _ = seg.select(sql, "body")
    hy = hydrate(body, pmap).text
    de = dehydrate(hy, pmap, force=False)
    # //text() ist unsicher -> uebersprungen
    assert any(tok == "@param4" for tok, _ in de.skipped_unsafe)
    # demo_source kommt mehrfach vor -> Konflikt ohne force
    assert any(tok == "@SCHEMA_Source" for tok, _ in de.conflicts)
    assert "@param1" in de.replaced


def test_dehydrate_force_replaces_all(comp_root):
    sql, pmap = _ctx(comp_root)
    body, _, _ = seg.select(sql, "body")
    hy = hydrate(body, pmap).text
    de = dehydrate(hy, pmap, force=True)
    assert de.replaced.get("@SCHEMA_Source") == 5
    assert "demo_source" not in de.text


def test_star_value_never_dehydrated(selftest_root):
    # @param3 = '*' darf niemals automatisch zurueckgesetzt werden
    tob = TestObject(
        selftest_root / "Component1/TestDataObject1/Data_TestDataObject1.tob"
    )
    rtl = RunTimeList(
        selftest_root / "Component1/TestDataObject1/RunTimeList/Extensive.rtl"
    )
    env = Environment.load(
        specific=selftest_root / "Environment/TestEnvironment1.env",
        global_env=selftest_root / "Environment/Global.env",
    )
    _, pmap = build(tob, "A", rtl, env)
    de = dehydrate("SELECT * FROM t", pmap, force=True)
    assert de.text == "SELECT * FROM t"  # unveraendert
    assert any(tok == "@param3" for tok, _ in de.skipped_unsafe)
