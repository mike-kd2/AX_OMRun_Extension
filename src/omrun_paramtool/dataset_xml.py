"""XML-Zugriff auf OMrun ADO.NET-DataSet-XML.

Wichtig fuer airgapped Betrieb: das Tool laeuft **ohne externe Abhaengigkeit**
auf der Python-Standardbibliothek (xml.etree.ElementTree). Ist lxml vorhanden,
wird es als Backend genutzt (bessere Serialisierungstreue fuer spaeteren
Write-back, Stufe 2). Der Rest des Codes ist backend-agnostisch, weil wir hier
ausschliesslich ueber local-name()-artige Baumlaeufe zugreifen statt ueber
Namespace-Prefixe.

Alle OMrun-Configs (.tob/.rtl/.env/.tsc) sind typed .NET DataSets. Es kommt kein
CDATA vor; das SQL ist entity-escaped abgelegt (&lt; &gt; &amp;). Beide Backends
schreiben Text verlustfrei escaped zurueck.

Write-back-Prinzip: nur elem.text setzen, nie den Baum neu aufbauen.
"""

from __future__ import annotations

import os
import xml.etree.ElementTree as _ET
from pathlib import Path

# msdata-Namespace, in dem die Caption-Attribute der Schema-Sektion liegen.
MSDATA_NS = "urn:schemas-microsoft-com:xml-msdata"
_XS_NS = "http://www.w3.org/2001/XMLSchema"
_MSPROP_NS = "urn:schemas-microsoft-com:xml-msprop"

# Backend-Wahl: lxml wenn verfuegbar, sonst stdlib. Ueber Umgebungsvariable
# OMRUN_XML_BACKEND=stdlib|lxml erzwingbar (nuetzlich fuer Tests).
_forced = os.environ.get("OMRUN_XML_BACKEND", "").strip().lower()
try:  # pragma: no cover - umgebungsabhaengig
    from lxml import etree as _lxml
except ImportError:  # pragma: no cover
    _lxml = None

if _forced == "stdlib":
    _lxml = None
elif _forced == "lxml" and _lxml is None:  # pragma: no cover
    raise RuntimeError("OMRUN_XML_BACKEND=lxml verlangt, aber lxml nicht installiert")

BACKEND = "lxml" if _lxml is not None else "stdlib"


# --- Laden / Speichern ---------------------------------------------------
def make_parser():
    """Nur relevant fuer lxml (strip_cdata=False). stdlib: None."""
    if _lxml is not None:
        return _lxml.XMLParser(strip_cdata=False, remove_blank_text=False)
    return None


def load(path: str | Path):
    if _lxml is not None:
        return _lxml.parse(str(path), make_parser())
    return _ET.parse(str(path))


def _root_namespace(root) -> str | None:
    tag = root.tag
    if isinstance(tag, str) and tag.startswith("{"):
        return tag[1:].split("}", 1)[0]
    return None


def save(tree, path: str | Path) -> None:
    root = tree.getroot()
    if _lxml is not None:
        tree.write(
            str(path),
            xml_declaration=True,
            encoding=tree.docinfo.encoding or "utf-8",
            standalone=tree.docinfo.standalone,
        )
        return

    # stdlib: bekannte Namespaces registrieren, damit Prefixe stabil bleiben.
    default_ns = _root_namespace(root)
    if default_ns:
        _ET.register_namespace("", default_ns)
    _ET.register_namespace("xs", _XS_NS)
    _ET.register_namespace("msdata", MSDATA_NS)
    _ET.register_namespace("msprop", _MSPROP_NS)
    body = _ET.tostring(root, encoding="unicode")
    # Alle OMrun-DataSets sind standalone="yes".
    text = '<?xml version="1.0" standalone="yes"?>\n' + body
    Path(path).write_text(text, encoding="utf-8")


# --- backend-agnostische Baum-Helfer -------------------------------------
def local_name(elem) -> str:
    tag = elem.tag
    if isinstance(tag, str) and tag.startswith("{"):
        return tag.split("}", 1)[1]
    return tag


def _iter_elements(root):
    for e in root.iter():
        if isinstance(e.tag, str):
            yield e


def local_findall(root, localname: str) -> list:
    """Alle Elemente mit gegebenem local-name (Namespace-agnostisch).

    Trifft nur echte Datenelemente wie <QueryA>, nicht die Schema-Deklaration
    <xs:element name="QueryA"> (deren local-name ist 'element').
    """
    return [e for e in _iter_elements(root) if local_name(e) == localname]


def local_find(root, localname: str):
    for e in _iter_elements(root):
        if local_name(e) == localname:
            return e
    return None


def direct_children(elem) -> list:
    return [c for c in elem if isinstance(c.tag, str)]


def child_text(elem, localname: str) -> str | None:
    """Text des ersten direkten Kindes mit gegebenem local-name (oder None)."""
    for c in direct_children(elem):
        if local_name(c) == localname:
            return c.text
    return None


def _attr_localname(key: str) -> str:
    if key.startswith("{"):
        return key.split("}", 1)[1]
    return key


def caption_of(schema_element) -> str | None:
    """msdata:Caption eines xs:element (Namespace-agnostisch gelesen)."""
    for key, val in schema_element.attrib.items():
        if _attr_localname(key) == "Caption":
            return val
    return None
