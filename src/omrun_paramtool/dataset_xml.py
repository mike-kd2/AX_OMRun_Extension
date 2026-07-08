"""lxml-Zugriff auf OMrun ADO.NET-DataSet-XML.

Alle OMrun-Configs (.tob/.rtl/.env/.tsc) sind typed .NET DataSets: Datenelemente
liegen im Default-Namespace (kein Prefix). Statt Namespace-Prefixe zu jonglieren,
adressieren wir konsequent ueber local-name().

Write-back-Prinzip: nur elem.text setzen, nie den Baum neu aufbauen. So bleiben
Entity-Escaping (&lt; &gt; &amp;), Formatierung und alle uebrigen Knoten erhalten.
"""

from __future__ import annotations

from pathlib import Path

from lxml import etree

# msdata-Namespace, in dem die Caption-Attribute der Schema-Sektion liegen.
MSDATA_NS = "urn:schemas-microsoft-com:xml-msdata"


def make_parser() -> etree.XMLParser:
    # strip_cdata=False: falls doch mal CDATA auftaucht, nicht stillschweigend
    # aufloesen. remove_blank_text=False: Formatierung erhalten.
    return etree.XMLParser(strip_cdata=False, remove_blank_text=False)


def load(path: str | Path) -> etree._ElementTree:
    return etree.parse(str(path), make_parser())


def save(tree: etree._ElementTree, path: str | Path) -> None:
    tree.write(
        str(path),
        xml_declaration=True,
        encoding=tree.docinfo.encoding or "utf-8",
        standalone=tree.docinfo.standalone,
    )


def local_findall(root: etree._Element, localname: str) -> list[etree._Element]:
    """Alle Elemente mit gegebenem local-name (Namespace-agnostisch).

    Trifft nur echte Datenelemente wie <QueryA>, nicht die Schema-Deklaration
    <xs:element name="QueryA"> (deren Tag ist 'xs:element').
    """
    return root.xpath(".//*[local-name()=$n]", n=localname)


def local_find(root: etree._Element, localname: str) -> etree._Element | None:
    hits = local_findall(root, localname)
    return hits[0] if hits else None


def direct_children(elem: etree._Element) -> list[etree._Element]:
    return [c for c in elem if isinstance(c.tag, str)]


def local_name(elem: etree._Element) -> str:
    return etree.QName(elem).localname


def child_text(elem: etree._Element, localname: str) -> str | None:
    """Text des ersten direkten Kindes mit gegebenem local-name (oder None)."""
    for c in direct_children(elem):
        if local_name(c) == localname:
            return c.text
    return None


def caption_of(schema_element: etree._Element) -> str | None:
    """msdata:Caption eines xs:element (Namespace-agnostisch gelesen)."""
    for key, val in schema_element.attrib.items():
        qn = etree.QName(key)
        if qn.localname == "Caption":
            return val
    return None
