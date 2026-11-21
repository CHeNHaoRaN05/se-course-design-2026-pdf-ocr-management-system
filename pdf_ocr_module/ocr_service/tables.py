"""Conservative reconstruction of closed, regular ruled grids (no merged cells)."""
import cv2
import numpy as np


def assign_cells(table, blocks, width, height):
    xs, ys = table["x_lines"], table["y_lines"]
    cells = [[[] for _ in xs[1:]] for _ in ys[1:]]
    for block in sorted(blocks, key=lambda b: (b["bbox"][1], b["bbox"][0], b.get("id", 0))):
        a, b, c, d = block["bbox"]
        a, c, b, d = a*width, c*width, b*height, d*height
        candidates = []
        for r, (top, bottom) in enumerate(zip(ys, ys[1:])):
            for col, (left, right) in enumerate(zip(xs, xs[1:])):
                area = max(0, min(c, right)-max(a, left))*max(0, min(d, bottom)-max(b, top))
                if area:
                    candidates.append((area, -r, -col))
        if candidates:
            _, r, col = max(candidates)
            cells[-r][-col].append(block["text"])
            if len(candidates) > 1:
                warning = "Cross-cell text assigned by largest overlap; review required"
                warnings = table.setdefault("warnings", [])
                if warning not in warnings:
                    warnings.append(warning)
    return [["\n".join(cell) for cell in row] for row in cells]



def ruled_tables(image, blocks, warnings=None):
    warnings = warnings if warnings is not None else []
    gray = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2GRAY)
    binary = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY_INV, 21, 10)
    h, w = gray.shape
    horizontal = cv2.morphologyEx(binary, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (max(30, w // 25), 1)))
    vertical = cv2.morphologyEx(binary, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(30, h // 25))))
    contours, _ = cv2.findContours(horizontal | vertical, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    def centers(values):
        groups = []
        for i in values:
            if groups and i - groups[-1][-1] <= 2:
                groups[-1].append(int(i))
            else:
                groups.append([int(i)])
        return [int(round(sum(g) / len(g))) for g in groups]

    tables = []
    for contour in sorted(contours, key=lambda c: (cv2.boundingRect(c)[1], cv2.boundingRect(c)[0])):
        x, y, width, height = cv2.boundingRect(contour)
        if width < 60 or height < 60:
            continue
        # Every separator must cover >= 90% of its entire table. Partial / merged grids are rejected.
        xs = centers(np.flatnonzero((vertical[y:y+height, x:x+width] > 0).sum(axis=0) >= .9 * height))
        ys = centers(np.flatnonzero((horizontal[y:y+height, x:x+width] > 0).sum(axis=1) >= .9 * width))
        if len(xs) < 3 or len(ys) < 3:
            continue
        if len(xs) > 51 or len(ys) > 101:
            warnings.append(f"Table omitted: {len(xs)-1} columns, {len(ys)-1} rows exceeds 50x100 limit")
            continue
        # Reject additional partial separators instead of inventing rectangular cells.
        all_x = centers(np.flatnonzero((vertical[y:y+height, x:x+width] > 0).sum(axis=0) >= .2 * height))
        all_y = centers(np.flatnonzero((horizontal[y:y+height, x:x+width] > 0).sum(axis=1) >= .2 * width))
        if len(xs) != len(all_x) or len(ys) != len(all_y):
            warnings.append("Partial/merged grid omitted; review original page")
            continue
        table = {"id": len(tables) + 1, "strategy": "ruled_grid", "needs_review": True,
                 "x_lines": [x + i for i in xs], "y_lines": [y + i for i in ys]}
        table["cells"] = assign_cells(table, blocks, w, h)
        tables.append(table)
    return tables

