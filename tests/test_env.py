from omrun_paramtool.env import Environment


def _load(comp_root, precedence="specific"):
    return Environment.load(
        specific=comp_root / "Environment/Demo.env",
        global_env=comp_root / "Environment/Global.env",
        precedence=precedence,
    )


def test_schema_alias_resolves(comp_root):
    env = _load(comp_root)
    r = env.resolve("@SCHEMA_Source")
    assert r.resolved and r.value == "demo_source"


def test_recursive_chain(comp_root):
    # @USER_Source -> Db=@SCHEMA_Source -> demo_source
    env = _load(comp_root)
    r = env.resolve("@USER_Source")
    assert r.resolved and r.value == "demo_source"
    assert "@SCHEMA_Source" in r.chain


def test_layering_precedence_specific_vs_global(comp_root):
    # @DB_Source ist in beiden Dateien mit anderem Wert definiert.
    spec = _load(comp_root, "specific").resolve("@DB_Source")
    glob = _load(comp_root, "global").resolve("@DB_Source")
    # unterschiedliche Praezedenz -> unterschiedliche Aufloesung
    assert spec.value != glob.value


def test_unknown_alias_unresolved(comp_root):
    env = _load(comp_root)
    r = env.resolve("@DOES_NOT_EXIST")
    assert not r.resolved and r.value is None
