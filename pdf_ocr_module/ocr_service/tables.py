"""Conservative reconstruction of closed, regular ruled grids (no merged cells)."""
import cv2
import numpy as np


def assign_cells(table, blocks, width, height):
    rows = []
    xs, ys = table["x_lines"], table["y_lines"]
    for top, bottom in zip(ys, ys[1:]):
        row = []
        for left, right in zip(xs, xs[1:]):
            texts = []
            for block in blocks:
                a, b, c, d = block["bbox"]
                cx, cy = (a + c) * width / 2, (b + d) * height / 2
                if left <= cx < right and top <= cy < bottom:
                    texts.append(block["text"])
            row.append("\n".join(texts))
        rows.append(row)
    return rows


def ruled_tables(image, blocks):
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
        if not (3 <= len(xs) <= 51 and 3 <= len(ys) <= 101):
            continue
        # Reject additional partial separators instead of inventing rectangular cells.
        all_x = centers(np.flatnonzero((vertical[y:y+height, x:x+width] > 0).sum(axis=0) >= .2 * height))
        all_y = centers(np.flatnonzero((horizontal[y:y+height, x:x+width] > 0).sum(axis=1) >= .2 * width))
        if len(xs) != len(all_x) or len(ys) != len(all_y):
            continue
        table = {"id": len(tables) + 1, "strategy": "ruled_grid", "needs_review": True,
                 "x_lines": [x + i for i in xs], "y_lines": [y + i for i in ys]}
        table["cells"] = assign_cells(table, blocks, w, h)
        tables.append(table)
    return tables

