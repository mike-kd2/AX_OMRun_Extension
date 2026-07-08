"""RunTimeList (.rtl): liefert @paramN -> Wert.

Die Bindung Element -> Platzhaltername steht in der Schema-Sektion als
msdata:Caption (z.B. Element _x0040_key1 hat Caption @param1). Die Werte
stehen in den DataTableRunTime-Zeilen. Es kann mehrere Zeilen geben; die
Auswahl erfolgt ueber <Number> (Default: erste mit Active=true, sonst erste).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from . import dataset_xml as dx
from .errors import ConfigNotFoundError


@dataclass(frozen=True)
class RunTimeRow:
    number: str | None
    active: bool
    remark: str | None
    values: dict[str, str]   # Caption (@paramN) -> Wert


class RunTimeList:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.tree = dx.load(self.path)
        self.root = self.tree.getroot()
        self._captions = self._read_captions()

    def _read_captions(self) -> dict[str, str]:
        """localname (_x0040_keyN) -> Caption (@paramN) aus der Schema-Sektion."""
        captions: dict[str, str] = {}
        # Nur Schema-Deklarationen: xs:element mit name-Attribut.
        for el in dx.local_findall(self.root, "element"):
            name = el.get("name")
            if not name:
                continue
            cap = dx.caption_of(el)
            if cap and cap.startswith("@"):
                captions[name] = cap
        return captions

    def rows(self) -> list[RunTimeRow]:
        result: list[RunTimeRow] = []
        for row in dx.local_findall(self.root, "DataTableRunTime"):
            values: dict[str, str] = {}
            number = None
            active = True
            remark = None
            for child in dx.direct_children(row):
                ln = dx.local_name(child)
                if ln == "Number":
                    number = child.text
                elif ln == "Active":
                    active = (child.text or "").strip().lower() != "false"
                elif ln == "Remark":
                    remark = child.text
                elif ln in self._captions and child.text is not None:
                    values[self._captions[ln]] = child.text
            result.append(
                RunTimeRow(number=number, active=active, remark=remark, values=values)
            )
        return result

    def select_row(self, number: str | None = None) -> RunTimeRow:
        rows = self.rows()
        if not rows:
            raise ConfigNotFoundError(f"{self.path.name}: keine DataTableRunTime-Zeile")
        if number is not None:
            for r in rows:
                if r.number == str(number):
                    return r
            raise ConfigNotFoundError(
                f"{self.path.name}: keine Zeile mit Number={number}"
            )
        for r in rows:
            if r.active:
                return r
        return rows[0]

    def param_map(self, number: str | None = None) -> dict[str, str]:
        return dict(self.select_row(number).values)
