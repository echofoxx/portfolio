from __future__ import annotations

import re
import zipfile
from io import BytesIO
from xml.etree import ElementTree as ET

NS = {"a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
CELL_RE = re.compile(r"([A-Z]+)(\d+)")


def _col_index(ref: str) -> int:
    letters = CELL_RE.match(ref).group(1)
    idx = 0
    for char in letters:
        idx = idx * 26 + (ord(char) - 64)
    return idx - 1


def read_first_sheet_xlsx(content: bytes) -> list[list[str]]:
    with zipfile.ZipFile(BytesIO(content)) as archive:
        shared = []
        if "xl/sharedStrings.xml" in archive.namelist():
            root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            for si in root.findall("a:si", NS):
                shared.append("".join((t.text or "") for t in si.findall(".//a:t", NS)))
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        rels = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        rel_map = {rel.attrib["Id"]: rel.attrib["Target"] for rel in rels}
        first_sheet = workbook.find("a:sheets/a:sheet", NS)
        rel_id = first_sheet.attrib["{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"]
        target = rel_map[rel_id]
        if target.startswith("/"):
            sheet_path = target.lstrip("/")
        elif target.startswith("xl/"):
            sheet_path = target
        else:
            sheet_path = "xl/" + target
        root = ET.fromstring(archive.read(sheet_path))
        rows: list[list[str]] = []
        for row in root.findall("a:sheetData/a:row", NS):
            values: dict[int, str] = {}
            for cell in row.findall("a:c", NS):
                ref = cell.attrib.get("r", "A1")
                idx = _col_index(ref)
                cell_type = cell.attrib.get("t")
                if cell_type == "inlineStr":
                    text = "".join((t.text or "") for t in cell.findall(".//a:t", NS))
                else:
                    node = cell.find("a:v", NS)
                    raw = node.text if node is not None else ""
                    if cell_type == "s" and raw:
                        text = shared[int(raw)]
                    elif cell_type == "b":
                        text = "TRUE" if raw == "1" else "FALSE"
                    else:
                        text = raw or ""
                values[idx] = text
            if values:
                max_idx = max(values)
                rows.append([values.get(i, "") for i in range(max_idx + 1)])
        return rows
