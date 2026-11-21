# -*- coding: utf-8 -*-
"""导出《系统设计文档》为 Word：
pandoc 转换 → python-docx 后处理（封面页、页眉页码、表格边框、A4、章级分页、
图片宽度约束、静态目录点引导线与 PAGEREF 页码域）。

与 scripts/export_req_docx.py 保持同一排版口径，便于两本文档配套提交。
目录页码为 Word 域结果，打开文档时选择「更新域」即显示实际页码。
"""
import os
import re
import subprocess

from docx import Document
from docx.shared import Pt, RGBColor, Mm, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT, WD_TAB_LEADER
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.style import WD_STYLE_TYPE
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

ROOT = r"c:\Users\Administrator\Desktop\se_course_design"
DOCS = os.path.join(ROOT, "docs")
DESIGN = os.path.join(DOCS, "design")
MD = os.path.join(DESIGN, "系统设计文档_V2.0.md")
OUT = os.path.join(DESIGN, "系统设计文档_V2.0_范围外清理版.docx")
FALLBACK = os.path.join(DESIGN, "系统设计文档_V2.0_范围外清理版_导出版.docx")
TMP = os.path.join(os.path.dirname(__file__), ".design_v2_tmp.docx")

# ---------- 第 1 步：pandoc 转换到临时文件 ----------
subprocess.run(
    ["pandoc", MD, "-f", "markdown-smart", "-o", TMP,
     "--resource-path", DOCS + os.pathsep + ROOT + os.pathsep + DESIGN],
    check=True, cwd=DESIGN,
)
print("pandoc 转换完成（表格语法与图片路径校验通过）")

doc = Document(TMP)


def set_style_font(style, size_pt, cjk, ascii_font, bold=None, color_black=True):
    """统一设置样式字体（含中文 eastAsia）。"""
    f = style.font
    f.size = Pt(size_pt)
    f.name = ascii_font
    if bold is not None:
        f.bold = bold
    if color_black:
        f.color.rgb = RGBColor(0, 0, 0)
    rpr = style.element.get_or_add_rPr()
    rfonts = rpr.get_or_add_rFonts()
    rfonts.set(qn("w:eastAsia"), cjk)


# ---------- 第 2 步：样式 ----------
set_style_font(doc.styles["Normal"], 12, "宋体", "Times New Roman")       # 小四
doc.styles["Normal"].paragraph_format.line_spacing = 1.5

set_style_font(doc.styles["Heading 1"], 22, "黑体", "Times New Roman", bold=True)
doc.styles["Heading 1"].paragraph_format.space_before = Pt(17)
doc.styles["Heading 1"].paragraph_format.space_after = Pt(16)
set_style_font(doc.styles["Heading 2"], 16, "黑体", "Times New Roman", bold=True)
set_style_font(doc.styles["Heading 3"], 14, "黑体", "Times New Roman", bold=True)
set_style_font(doc.styles["Heading 4"], 12, "黑体", "Times New Roman", bold=True)
for name in ("Compact", "Block Text", "Quote"):  # 表格单元格/引用文字
    try:
        set_style_font(doc.styles[name], 10.5, "宋体", "Times New Roman")
        doc.styles[name].paragraph_format.line_spacing = 1.0
    except KeyError:
        pass

# ---------- 第 3 步：表格边框与封面表 ----------
for tbl in doc.tables:
    try:
        tbl.style = doc.styles["Table Grid"]
    except KeyError:
        pass

if doc.tables:
    cover_tbl = doc.tables[0]
    cover_tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    for row in cover_tbl.rows:
        for cell in row.cells:
            for p in cell.paragraphs:
                p.alignment = (WD_ALIGN_PARAGRAPH.CENTER
                               if cell is row.cells[0] else WD_ALIGN_PARAGRAPH.LEFT)

# ---------- 第 4 步：封面页 ----------
TITLE = "基于本地 OCR 的 PDF 文件显示与管理系统"
paras = doc.paragraphs


def find_para(text, style=None):
    for p in paras:
        if text in p.text and (style is None or p.style.name == style):
            return p
    return None


title = find_para(TITLE)
if title is not None:
    title.style = doc.styles["Normal"]
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title.paragraph_format.space_before = Pt(150)
    title.paragraph_format.space_after = Pt(30)
    title.paragraph_format.line_spacing = 1.0
    for r in title.runs:
        r.font.size = Pt(22)
        r.font.bold = True
        r.font.name = "Times New Roman"
        r.font.color.rgb = RGBColor(0, 0, 0)
        r._element.get_or_add_rPr().get_or_add_rFonts().set(qn("w:eastAsia"), "黑体")

sub = find_para("系统设计文档")
if sub is not None:
    sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    sub.paragraph_format.space_after = Pt(6)
    sub.paragraph_format.line_spacing = 1.0
    for r in sub.runs:
        r.font.size = Pt(18)
        r.font.bold = True
        r.font.name = "Times New Roman"
        r.font.color.rgb = RGBColor(0, 0, 0)
        r._element.get_or_add_rPr().get_or_add_rFonts().set(qn("w:eastAsia"), "黑体")

eng = find_para("Software Design Document")
if eng is not None:
    eng.alignment = WD_ALIGN_PARAGRAPH.CENTER
    eng.paragraph_format.space_after = Pt(60)
    eng.paragraph_format.line_spacing = 1.0
    for r in eng.runs:
        r.font.size = Pt(12)
        r.font.bold = False
        r.font.name = "Times New Roman"

# ---------- 第 5 步：一级标题（章级）分页 ----------
for p in doc.paragraphs:
    if p.style.name == "Heading 1":
        p.paragraph_format.page_break_before = True

# ---------- 第 6 步：A4 页面 + 页眉页脚页码 ----------
def footer_text(paragraph, text):
    run = paragraph.add_run(text)
    run.font.size = Pt(9)
    run.font.name = "Times New Roman"
    run._element.get_or_add_rPr().get_or_add_rFonts().set(qn("w:eastAsia"), "宋体")
    return run


def footer_field_char(paragraph, kind):
    run = paragraph.add_run()
    run.font.size = Pt(9)
    el = OxmlElement("w:fldChar")
    el.set(qn("w:fldCharType"), kind)
    run._r.append(el)
    return run


for sec in doc.sections:
    sec.page_width = Mm(210)
    sec.page_height = Mm(297)
    sec.top_margin = Cm(2.54)
    sec.bottom_margin = Cm(2.54)
    sec.left_margin = Cm(3.18)
    sec.right_margin = Cm(3.18)

    hp = sec.header.paragraphs[0]
    hp.text = "基于本地 OCR 的 PDF 文件显示与管理系统 · 系统设计文档"
    hp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for r in hp.runs:
        r.font.size = Pt(9)
        r.font.name = "Times New Roman"
        r._element.get_or_add_rPr().get_or_add_rFonts().set(qn("w:eastAsia"), "宋体")

    fp = sec.footer.paragraphs[0]
    fp.text = ""
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER

    footer_text(fp, "第 ")
    footer_field_char(fp, "begin")
    instr_run = fp.add_run()
    instr_run.font.size = Pt(9)
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = " PAGE "
    instr_run._r.append(instr)
    footer_field_char(fp, "separate")
    footer_text(fp, "1")
    footer_field_char(fp, "end")
    footer_text(fp, " 页")

# ---------- 第 7 步：图片宽度约束与静态目录页码 ----------
USABLE_WIDTH = Mm(146)          # 正文可用宽度约 146.4 mm（A4 - 3.18 cm × 2）
MAX_INLINE_WIDTH = Mm(145)      # 留出余量，避免 Word 打开时二次缩放

# 目录专用样式：小四宋体、单倍行距、无首行缩进；不沿用 pandoc 的 Compact 列表样式
toc_style = doc.styles.add_style("TOC Entry", WD_STYLE_TYPE.PARAGRAPH)
set_style_font(toc_style, 12, "宋体", "Times New Roman")
toc_style.paragraph_format.line_spacing = 1.0
toc_style.paragraph_format.space_before = Pt(0)
toc_style.paragraph_format.space_after = Pt(0)
toc_style.paragraph_format.first_line_indent = Cm(0)

scaled = 0
for shape in doc.inline_shapes:
    if shape.width > MAX_INLINE_WIDTH:
        ratio = MAX_INLINE_WIDTH / shape.width
        shape.height = int(round(shape.height * ratio))
        shape.width = MAX_INLINE_WIDTH
        scaled += 1


def add_pageref(paragraph, bookmark):
    """右对齐点引导线 + PAGEREF 域；域标记 dirty，由 Word / WPS 打开时填入真实页码。"""
    paragraph.add_run(chr(9))
    for kind in ("begin", "instr", "separate", "end"):
        r = paragraph.add_run()
        r.font.size = Pt(12)
        if kind == "instr":
            el = OxmlElement("w:instrText")
            el.set(qn("xml:space"), "preserve")
            el.text = f" PAGEREF {bookmark} {chr(92)}h "
        else:
            el = OxmlElement("w:fldChar")
            el.set(qn("w:fldCharType"), kind)
            if kind == "begin":
                el.set(qn("w:dirty"), "true")
        r._r.append(el)


def add_bookmark(paragraph, name, bid):
    start = OxmlElement("w:bookmarkStart")
    start.set(qn("w:id"), str(bid))
    start.set(qn("w:name"), name)
    end = OxmlElement("w:bookmarkEnd")
    end.set(qn("w:id"), str(bid))
    ppr = paragraph._p.find(qn("w:pPr"))
    pos = list(paragraph._p).index(ppr) + 1 if ppr is not None else 0
    paragraph._p.insert(pos, start)
    paragraph._p.append(end)


all_paras = doc.paragraphs
body_start = next(
    (i for i, p in enumerate(all_paras)
     if p.style.name == "Heading 1" and p.text.strip().startswith("第 1 章")),
    len(all_paras),
)
heading_map = {}
for p in all_paras[body_start:]:
    if p.style.name.startswith("Heading"):
        heading_map.setdefault(p.text.strip(), p)

def strip_list_numbering(paragraph):
    """去掉 pandoc 列表项目符号，返回原列表层级用于目录缩进。"""
    ppr = paragraph._p.find(qn("w:pPr"))
    numpr = ppr.find(qn("w:numPr")) if ppr is not None else None
    level = 0
    if numpr is not None:
        ilvl = numpr.find(qn("w:ilvl"))
        if ilvl is not None:
            level = int(ilvl.get(qn("w:val")) or 0)
        ppr.remove(numpr)
    return level


for p in all_paras[:body_start]:
    if p.style.name == "Heading 1" and p.text.strip().replace(" ", "") == "目录":
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER

toc_count = 0
for p in all_paras[:body_start]:
    key = p.text.strip()
    if (p.style.name == "Compact" and key in heading_map
            and re.match(r"^(第 [0-9]+ 章|[0-9]+[.][0-9]+|附录)", key)):
        bookmark = f"_TocDesign{toc_count + 1}"
        add_bookmark(heading_map[key], bookmark, toc_count + 1)
        level = strip_list_numbering(p)
        p.style = toc_style
        p.paragraph_format.left_indent = Cm(0.74 * level)
        p.paragraph_format.first_line_indent = Cm(0)
        if level == 0:
            for run in p.runs:
                run.font.bold = True
        p.paragraph_format.tab_stops.add_tab_stop(
            USABLE_WIDTH, WD_TAB_ALIGNMENT.RIGHT, WD_TAB_LEADER.DOTS)
        add_pageref(p, bookmark)
        toc_count += 1

settings_el = doc.settings.element
if settings_el.find(qn("w:updateFields")) is None:
    update_fields = OxmlElement("w:updateFields")
    update_fields.set(qn("w:val"), "true")
    # CT_Settings 为有序序列：updateFields 须位于 compat / rsids 等元素之前，
    # 直接追加到末尾会被 Word 判为非法的 settings.xml。
    anchor = None
    for tag in ("w:compat", "w:docVars", "w:rsids", "w:mathPr", "w:themeFontLang"):
        anchor = settings_el.find(qn(tag))
        if anchor is not None:
            break
    if anchor is None:
        settings_el.append(update_fields)
    else:
        settings_el.insert(list(settings_el).index(anchor), update_fields)

print(f"图片等比缩放: {scaled} 张（上限 145 mm）；目录页码域: {toc_count} 条")

doc.save(TMP)
try:
    os.replace(TMP, OUT)
    result = OUT
    if os.path.exists(FALLBACK):
        try:
            os.remove(FALLBACK)
        except OSError:
            pass
except PermissionError:
    result = FALLBACK
    os.replace(TMP, FALLBACK)
    print("提示：目标 Word 文档正被占用，已输出导出版；关闭 Word 后重跑本脚本即可同步回原文件")
print("后处理完成：", result)
