import csv
from copy import deepcopy
import html
import io
import json
import re


def spreadsheet_safe(value):
    # Neutralize formulas when CSV/XLSX are opened in office applications.
    value = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", str(value))
    return "'" + value if value.lstrip().startswith(("=", "+", "-", "@")) or value.startswith(("\t", "\r", "\n")) else value


def export_pages(pages, fmt, include_coordinates=True):
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
        rows.extend([[p["page_no"], b["id"], spreadsheet_safe(b["text"]), b["confidence"]]
                     + (b["bbox"] if include_coordinates else []) for b in p["result"]["blocks"]])
    if fmt == "csv":
        output = io.StringIO(newline="")
        csv.writer(output).writerows(rows)
        return output.getvalue().encode("utf-8-sig"), "text/csv; charset=utf-8"
    from openpyxl import Workbook
    book = Workbook()
    sheet = book.active
    sheet.title = "OCR文本"
    for row in rows:
        sheet.append(row)
    for p in pages:
        for table in p["result"].get("tables", []):
            sheet = book.create_sheet(f"P{p['page_no']}_T{table['id']}")
            for row in table["cells"]:
                sheet.append([spreadsheet_safe(c) for c in row])
    output = io.BytesIO()
    book.save(output)
    return output.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

