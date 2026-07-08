from omrun_paramtool import segments as seg


def test_split_with_marker():
    sql = "HEAD\n/*BODY*/\nTAIL"
    s = seg.split(sql)
    assert s.has_body
    assert s.header == "HEAD\n"
    assert s.body == "\nTAIL"
    assert s.recombine() == sql


def test_split_without_marker():
    sql = "SELECT 1"
    s = seg.split(sql)
    assert not s.has_body
    assert s.header == sql
    assert s.body == ""
    assert s.recombine() == sql


def test_select_body_default():
    sql = "H/*BODY*/B"
    text, part, warn = seg.select(sql, "body")
    assert text == "B" and part == "body" and warn is None


def test_select_body_fallback_when_no_marker():
    sql = "ONLYHEAD"
    text, part, warn = seg.select(sql, "body")
    assert text == "ONLYHEAD" and part == "header" and warn is not None


def test_select_full_is_lossless():
    sql = "H/*BODY*/B"
    text, part, _ = seg.select(sql, "full")
    assert text == sql and part == "full"
