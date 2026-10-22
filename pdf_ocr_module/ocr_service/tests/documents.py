"""Generate self-contained equipment inventory documents for verification."""
import io
import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


def inventory_image(sequence=1):
    sheet = Image.new("RGB", (960, 560), "white")
    pen = ImageDraw.Draw(sheet)
    font = ImageFont.truetype(os.getenv("OCR_TEST_FONT", "C:/Windows/Fonts/simhei.ttf"), 32)
    pen.text((48, 36), "设备借用登记", fill="black", font=font)
    pen.text((48, 94), f"INVENTORY {7000 + sequence}", fill="black", font=font)
    xs, ys = [48, 400, 850], [180, 270, 360, 450]
    for x in xs:
        pen.line((x, ys[0], x, ys[-1]), fill="black", width=3)
    for y in ys:
        pen.line((xs[0], y, xs[-1], y), fill="black", width=3)
    for y, values in zip([202, 292, 382], [("设备名称", "登记数量"), ("显微镜", str(sequence + 2)), ("传感器", str(sequence + 5))]):
        for x, value in zip([70, 425], values):
            pen.text((x, y), value, fill="black", font=font)
    return sheet


def image_bytes(sequence=1):
    target = io.BytesIO()
    with inventory_image(sequence) as sheet:
        sheet.save(target, "PNG")
    return target.getvalue()


def pdf_bytes():
    target = io.BytesIO()
    sheets = [inventory_image(i) for i in [4, 5, 6]]
    try:
        sheets[0].save(target, "PDF", resolution=120, save_all=True, append_images=sheets[1:])
    finally:
        for sheet in sheets:
            sheet.close()
    return target.getvalue()
