import csv
from copy import deepcopy
import html
import io
import json
import re
import unicodedata
from .result_validation import check_export_size


def spreadsheet_safe(value):
    # Neutralize formulas when CSV/XLSX are opened in office applications.
    value = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", str(value))
    probe = "".join(c for c in value if not (c.isspace() or unicodedata.category(c) in {"Cf", "Cc"})).lstrip(";")
    return "'" + value if probe.startswith(("=", "+", "-", "@")) or value.startswith(("\t", "\r", "\n")) else value



def export_pages(pages, fmt, include_coordinates=True):
    check_export_size(pages)
    if fmt == "json":
        output = deepcopy(pages)
        if not include_coordinates:
            for page in output:
                for block in page["result"]["blocks"]:
                    block.pop("bbox", None)
                for table in page["result"].get("tables", []):
                    table.pop("x_lines", None)
                    table.pop("y_lines", None)
        return json.dumps(output, ensure_ascii=False, indent=2).encode(), "application/json"
    if fmt == "txt":
        return "\n\n".join(f"--- 第 {p['page_no']} 页 ---\n{p['result']['text']}" for p in pages).encode(), "text/plain; charset=utf-8"
    if fmt == "html":
        parts = ['<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>OCR 结果</title><body>']
        for p in pages:
            parts.append(f"<h2>第 {p['page_no']} 页</h2><pre>{html.escape(p['result']['text'])}</pre>")
            for table in p["result"].get("tables", []):
                parts.append('<table border="1">')
                parts.extend("<tr>" + "".join("<td>" + html.escape(c) + "</td>" for c in row) + "</tr>" for row in table["cells"])
                parts.append("</table>")
        return ("".join(parts) + "</body></html>").encode(), "text/html; charset=utf-8"
    rows = [["page", "block_id", "text", "confidence"] + (["left", "top", "right", "bottom"] if include_coordinates else [])]
    for p in pages:
        rows.extend([[p["page_no"], b["id"], spreadsheet_safe(b["text"]) if fmt == "csv" else b["text"], b.get("confidence", "")]
                     + (b.get("bbox", ["", "", "", ""]) if include_coordinates else []) for b in p["result"]["blocks"]])
    if fmt == "csv":
        for p in pages:
            for index, table in enumerate(p["result"].get("tables", []), 1):
                for r, cells in enumerate(table["cells"], 1):
                    for c, value in enumerate(cells, 1):
                        rows.append([p["page_no"], f"table:{index}:{r}:{c}", spreadsheet_safe(value), ""]
                                    + (["", "", "", ""] if include_coordinates else []))
        output = io.StringIO(newline="")
        csv.writer(output).writerows(rows)
        return output.getvalue().encode("utf-8-sig"), "text/csv; charset=utf-8"
    # Validate before starting write-only XML generators, so a rejected cell
    # cannot leave half-written temporary worksheets behind.
    texts = (cell for p in pages for table in p["result"].get("tables", [])
             for row in table["cells"] for cell in row)
    for value in list(texts) + [b["text"] for p in pages for b in p["result"]["blocks"]]:
        if len(value) > 32767 or re.search(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", value):
            raise ValueError("XLSX cannot preserve this text; export JSON instead")
    from openpyxl import Workbook
    from openpyxl.cell import WriteOnlyCell
    book = Workbook(write_only=True)
    sheet = book.create_sheet("OCR文本")
    def append_literal(sheet, row):
        cells = []
        for value in row:
            cell = WriteOnlyCell(sheet, value=value)
            if isinstance(value, str):
                cell.data_type = "s"
            cells.append(cell)
        sheet.append(cells)
    for row in rows:
        append_literal(sheet, row)
    for p in pages:
        for index, table in enumerate(p["result"].get("tables", []), 1):
            sheet = book.create_sheet(f"P{p['page_no']}_T{index}")
            for row in table["cells"]:
                append_literal(sheet, row)
    output = io.BytesIO()
    book.save(output)
    return output.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

