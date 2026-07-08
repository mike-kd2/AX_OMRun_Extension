from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures" / "configs"
COMP = FIXTURES / "Comp_ORA_PG" / "TestScripts" / "Comp_ORA-PG"
SELFTEST = FIXTURES / "SelfTest" / "TestScripts" / "OMrun_SelfTest"


@pytest.fixture
def comp_root() -> Path:
    return COMP


@pytest.fixture
def selftest_root() -> Path:
    return SELFTEST
