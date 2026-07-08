"""TestObject (.tob): liefert das SQL aus ConfigurationA/QueryA und
ConfigurationB/QueryB samt DB-Alias (AliasDbA/AliasDbB)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from . import dataset_xml as dx
from .errors import ConfigNotFoundError

# side -> (Configuration-Element, Query-Element, AliasDb-Element)
_SIDE_MAP = {
    "A": ("ConfigurationA", "QueryA", "AliasDbA"),
    "B": ("ConfigurationB", "QueryB", "AliasDbB"),
}


@dataclass(frozen=True)
class Query:
    side: str
    sql: str
    alias_db: str | None


class TestObject:
    __test__ = False  # kein pytest-Testfall trotz "Test"-Praefix

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.tree = dx.load(self.path)
        self.root = self.tree.getroot()

    def _config_elem(self, side: str):
        cfg_name, _, _ = _SIDE_MAP[side]
        return dx.local_find(self.root, cfg_name)

    def has_side(self, side: str) -> bool:
        return self._config_elem(side) is not None

    def get_query(self, side: str) -> Query:
        side = side.upper()
        if side not in _SIDE_MAP:
            raise ValueError(f"side muss A oder B sein, nicht {side!r}")
        cfg = self._config_elem(side)
        if cfg is None:
            raise ConfigNotFoundError(
                f"{self.path.name}: keine Configuration{side} vorhanden"
            )
        _, query_name, alias_name = _SIDE_MAP[side]
        sql = dx.child_text(cfg, query_name)
        if sql is None:
            raise ConfigNotFoundError(
                f"{self.path.name}: {query_name} ist leer/fehlt"
            )
        alias = dx.child_text(cfg, alias_name)
        return Query(side=side, sql=sql, alias_db=alias)

    def set_query(self, side: str, sql: str) -> None:
        """Setzt nur elem.text des Query-Elements (verlustfrei). Stufe-2-Fundament;
        das Speichern selbst uebernimmt der Aufrufer via dataset_xml.save."""
        side = side.upper()
        cfg = self._config_elem(side)
        if cfg is None:
            raise ConfigNotFoundError(f"{self.path.name}: keine Configuration{side}")
        _, query_name, _ = _SIDE_MAP[side]
        for child in dx.direct_children(cfg):
            if dx.local_name(child) == query_name:
                child.text = sql
                return
        raise ConfigNotFoundError(f"{self.path.name}: {query_name} nicht gefunden")
