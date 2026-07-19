from __future__ import annotations

import re
import zipfile
from io import BytesIO
from xml.etree import ElementTree as ET

NS = {"a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
REL_NS = {"r": "http://schemas.openxmlformats.org/package/2006/relationships"}
OFFICE_REL = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
CELL_RE = re.compile(r"([A-Z]+)(\d+)")


def _col_index(ref: str) -> int:
    match = CELL_RE.match(ref)
    if not match:
        return 0
    letters = match.group(1)
    idx = 0
    for char in letters:
        idx = idx * 26 + (ord(char) - 64)
    return idx - 1


def _shared_strings(archive: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in archive.namelist():
        return []
    root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
    return ["".join((t.text or "") for t in si.findall(".//a:t", NS)) for si in root.findall("a:si", NS)]


def _sheet_path(target: str) -> str:
    if target.startswith("/"):
        return target.lstrip("/")
    if target.startswith("xl/"):
        return target
    return "xl/" + target.lstrip("/")


def _cell_text(cell: ET.Element, shared: list[str]) -> str:
    cell_type = cell.attrib.get("t")
    if cell_type == "inlineStr":
        return "".join((t.text or "") for t in cell.findall(".//a:t", NS))
    node = cell.find("a:v", NS)
    raw = node.text if node is not None else ""
    if cell_type == "s" and raw:
        return shared[int(raw)]
    if cell_type == "b":
        return "TRUE" if raw == "1" else "FALSE"
    return raw or ""


def _read_sheet(archive: zipfile.ZipFile, path: str, shared: list[str]) -> list[list[str]]:
    root = ET.fromstring(archive.read(path))
    rows: list[list[str]] = []
    for row in root.findall("a:sheetData/a:row", NS):
        values: dict[int, str] = {}
        sequential_idx = 0
        for cell in row.findall("a:c", NS):
            ref = cell.attrib.get("r")
            idx = _col_index(ref) if ref else sequential_idx
            values[idx] = _cell_text(cell, shared)
            sequential_idx = idx + 1
        if values:
            max_idx = max(values)
            rows.append([values.get(i, "") for i in range(max_idx + 1)])
    return rows


def read_workbook_xlsx(content: bytes) -> dict[str, list[list[str]]]:
    """Read values from every worksheet without evaluating formulas.

    Power BI exports sometimes omit A1 cell references and rely on cell order.
    The reader therefore supports both explicit references and positional cells.
    """
    with zipfile.ZipFile(BytesIO(content)) as archive:
        shared = _shared_strings(archive)
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        rels = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        rel_map = {rel.attrib["Id"]: rel.attrib["Target"] for rel in rels}
        result: dict[str, list[list[str]]] = {}
        for sheet in workbook.findall("a:sheets/a:sheet", NS):
            rel_id = sheet.attrib[OFFICE_REL]
            path = _sheet_path(rel_map[rel_id])
            result[sheet.attrib.get("name", "Sheet")] = _read_sheet(archive, path, shared)
        return result


def read_first_sheet_xlsx(content: bytes) -> list[list[str]]:
    workbook = read_workbook_xlsx(content)
    return next(iter(workbook.values()), [])
