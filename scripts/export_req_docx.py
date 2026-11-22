# -*- coding: utf-8 -*-
"""导出需求分析文档为 Word：
pandoc 转换 → python-docx 后处理（封面页、标题二号、A4、章级分页）。
"""
import os
import subprocess

from docx import Document
from docx.shared import Pt, RGBColor, Mm, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(ROOT, "docs")
REQ = os.path.join(DOCS, "requirements")
MD = os.path.join(REQ, "需求分析文档.md")
OUT = os.path.join(REQ, "需求分析文档_V1.1.docx")
FALLBACK = os.path.join(REQ, "需求分析文档_V1.1_导出版.docx")
TMP = os.path.join(os.path.dirname(__file__), ".req_docx_tmp.docx")

# ---------- 第 1 步：pandoc 转换到临时文件 ----------
subprocess.run(
    ["pandoc", MD, "-f", "markdown-smart", "-o", TMP,
     "--resource-path", DOCS + os.pathsep + ROOT + os.pathsep + REQ],
    check=True, cwd=REQ,
)
print("pandoc 转换完成（表格语法校验通过）")

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
pf = doc.styles["Normal"].paragraph_format
pf.line_spacing = 1.5

# 标题：H1 二号(22pt) 黑体加粗，H2 三号(16pt)，H3 四号(14pt)
set_style_font(doc.styles["Heading 1"], 22, "黑体", "Times New Roman", bold=True)
doc.styles["Heading 1"].paragraph_format.space_before = Pt(17)
doc.styles["Heading 1"].paragraph_format.space_after = Pt(16)
set_style_font(doc.styles["Heading 2"], 16, "黑体", "Times New Roman", bold=True)
set_style_font(doc.styles["Heading 3"], 14, "黑体", "Times New Roman", bold=True)
for name in ("Compact", "Block Text", "Quote"):  # 表格单元格/引用文字
    try:
        set_style_font(doc.styles[name], 10.5, "宋体", "Times New Roman")
        doc.styles[name].paragraph_format.line_spacing = 1.0
    except KeyError:
        pass

# ---------- 第 3 步：封面页 ----------
TITLE = "基于本地 OCR 的 PDF 文件显示与管理系统"
paras = doc.paragraphs

def find_para(text, style=None):
    for p in paras:
        if text in p.text and (style is None or p.style.name == style):
            return p
    return None

# 3.1 主标题：降为普通段落（不进目录），居中、二号黑体加粗
title = find_para(TITLE)
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

# 3.2 副标题"需求分析文档"：居中、小二黑体
sub = find_para("需求分析文档")
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

# 3.3 英文副题：居中、小四
eng = find_para("Software Requirements Specification")
if eng is not None:
    eng.alignment = WD_ALIGN_PARAGRAPH.CENTER
    eng.paragraph_format.space_after = Pt(60)
    eng.paragraph_format.line_spacing = 1.0
    for r in eng.runs:
        r.font.size = Pt(12)
        r.font.bold = False
        r.font.name = "Times New Roman"

# 3.4 封面信息表：水平居中
if doc.tables:
    cover_tbl = doc.tables[0]
    cover_tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    for row in cover_tbl.rows:
        for cell in row.cells:
            for p in cell.paragraphs:
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER if cell is row.cells[0] else WD_ALIGN_PARAGRAPH.LEFT

# ---------- 第 4 步：一级标题（章级）分页 ----------
h1_list = [p for p in doc.paragraphs if p.style.name == "Heading 1"]
for p in h1_list:
    p.paragraph_format.page_break_before = True

# ---------- 第 5 步：A4 页面 ----------
for sec in doc.sections:
    sec.page_width = Mm(210)
    sec.page_height = Mm(297)
    sec.top_margin = Cm(2.54)
    sec.bottom_margin = Cm(2.54)
    sec.left_margin = Cm(3.18)
    sec.right_margin = Cm(3.18)

doc.save(TMP)
try:
    os.replace(TMP, OUT)          # 目标未被 Word 占用时直接覆盖
    result = OUT
except PermissionError:
    result = FALLBACK
    os.replace(TMP, FALLBACK)     # 被占用则落到新文件名
    print("提示：目标文件正被 Word 占用，已输出到新文件")
print("后处理完成：", result)
