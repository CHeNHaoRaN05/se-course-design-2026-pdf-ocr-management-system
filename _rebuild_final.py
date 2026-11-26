# -*- coding: utf-8 -*-
"""一次生成两份交付物（原版文件为基础，最小改动）：

1. 设计方案汇报 PPT（12 页，保持原结构）
   P3 需求列表 +2 条；P8 文件库说明 +1 条；P12 演示顺序 +1 步。其余 9 页不动。

2. 汇报讲稿（原稿正文一字未动）
   第 3 页插入 1 句；第 6 节后整段新增「第 7 页 总体架构」；
   6 个节标题改页号；现场清单 +1 条。改动处红色加黄色高亮。
"""
import copy
import shutil
from pathlib import Path

from docx import Document
from docx.enum.text import WD_COLOR_INDEX
from docx.shared import RGBColor
from docx.text.paragraph import Paragraph
from docx.text.run import Run
from pptx import Presentation
from pptx.text.text import _Paragraph

DESK = Path(r"C:\Users\Administrator\Desktop")
PPT_SRC = DESK / "现代软件工程课程设计_03_设计方案汇报_第27组.pptx"
DOC_SRC = DESK / "现代软件工程课程设计_03_第27组_讲稿.docx"
PPT_DST = DESK / "现代软件工程课程设计_03_设计方案汇报_第27组_定稿.pptx"
DOC_DST = DESK / "现代软件工程课程设计_03_第27组_讲稿_标注版.docx"

RED = RGBColor(0xC0, 0x00, 0x00)


# ===================== PPT =====================
def build_deck():
    prs = Presentation(str(PPT_SRC))

    def shape(slide, name):
        for sh in slide.shapes:
            if sh.name == name:
                return sh
        raise KeyError(name)

    def insert_after(anchor, template, text):
        new_p = copy.deepcopy(template._p)
        anchor._p.addnext(new_p)
        para = _Paragraph(new_p, anchor._parent)
        for r in para.runs[1:]:
            r._r.getparent().remove(r._r)
        para.runs[0].text = text
        return para

    # P3 需求范围
    tf = shape(prs.slides[2], "TextBox 17").text_frame
    p3 = tf.paragraphs[3]
    a = insert_after(p3, p3, "• 文件可打标签，可按关键词全文检索并定位到页")
    insert_after(a, p3, "• 分享链接可设有效期与提取码，只读访问、随时撤销")
    shape(prs.slides[2], "TextBox 17").height = int(2.62 * 914400)

    # P8 文件库说明
    tf8 = shape(prs.slides[7], "TextBox 6").text_frame
    insert_after(tf8.paragraphs[1], tf8.paragraphs[3], "• 可打标签、生成分享链接，按关键词检索定位到页")

    # P12 演示顺序
    run = shape(prs.slides[11], "TextBox 9").text_frame.paragraphs[0].runs[0]
    if "复制分享链接" not in run.text:
        run.text = run.text.rstrip() + "\n6 复制分享链接，只读打开"

    prs.save(str(PPT_DST))
    print("deck ->", PPT_DST.name, len(prs.slides), "页")


# ===================== 讲稿 =====================
def build_doc():
    d = Document(str(DOC_SRC))
    P = d.paragraphs

    def style_new(p):
        for r in p.runs:
            r.font.color.rgb = RED
            r.font.highlight_color = WD_COLOR_INDEX.YELLOW

    def set_text(p, t):
        for r in p.runs[1:]:
            r._r.getparent().remove(r._r)
        p.runs[0].text = t

    def insert_after_str(p, anchor, new_text):
        full = p.runs[0].text
        i = full.index(anchor) + len(anchor)
        head, tail = full[:i], full[i:]
        r0 = p.runs[0]
        r0.text = head
        tail_el = copy.deepcopy(r0._r)
        new_el = copy.deepcopy(r0._r)
        r0._r.addnext(new_el)
        new_el.addnext(tail_el)
        rn = Run(new_el, p); rn.text = new_text; rn.font.color.rgb = RED
        rn.font.highlight_color = WD_COLOR_INDEX.YELLOW
        Run(tail_el, p).text = tail

    # 1) 第 3 页正文插入分享与检索
    insert_after_str(P[11], "完成后查看按页结果并导出文本。",
                     "文件可以按关键词全文检索并定位到页；分享链接能设有效期和提取码，只读访问、随时撤销。")

    # 2) 第 6 节之后整段新增第 7 页
    h_tpl, b_tpl = P[16], P[17]
    h_el = copy.deepcopy(h_tpl._p); b_tpl._p.addnext(h_el)
    h = Paragraph(h_el, b_tpl._parent)
    set_text(h, "第 7 页  总体架构  约 30 秒"); style_new(h)
    b_el = copy.deepcopy(b_tpl._p); h._p.addnext(b_el)
    b = Paragraph(b_el, b_tpl._parent)
    set_text(b, "这一页把分层架构落成具体进程。浏览器端是 React 应用；FastAPI 进程统一处理认证、文件、阅读器、任务和导出；"
                "SQLite 既存元数据也当任务队列；本地目录放原文件和模型权重；OCR worker 独立运行，逐页读取并回写结果。"
                "三句话总结：文件和识别结果不出本机；OCR 不阻塞页面请求，进度靠轮询；页结果和索引在同一事务写入。")
    style_new(b)

    # 3) 六个节标题改页号
    titles = {
        "第 7 页  文件管理与在线显示  约 25 秒": "第 8–9 页  文件库与上传阅读流程  约 50 秒",
        "第 8 页  PDF 与图片阅读器  约 25 秒": "第 10 页  PDF 与图片共用阅读器入口  约 25 秒",
        "第 9 页  OCR 任务与结果  约 30 秒": "第 11 页  OCR 异步任务链路  约 30 秒",
        "第 10 页  文件库与短演示  约 25 秒": "第 12 页  现场演示  约 25 秒",
        "第 11 页  OCR 状态与导出  约 25 秒": "第 12 页  续：识别状态与导出  约 25 秒",
        "第 12 页  总结  约 25 秒": "第 12 页  收束与总结  约 25 秒",
    }
    hit = 0
    for p in d.paragraphs:
        if p.text.strip() in titles:
            set_text(p, titles[p.text.strip()]); style_new(p); hit += 1
    assert hit == 6, hit

    # 4) 现场清单补一条
    last = d.paragraphs[-1]
    el = copy.deepcopy(last._p); last._p.addnext(el)
    p_new = Paragraph(el, last._parent)
    set_text(p_new, "复制分享链接，用无痕窗口只读打开"); style_new(p_new)

    # 5) 说明行
    set_text(d.paragraphs[5],
             "正文按约六分钟以上口播设计，括号内为翻页或演示提示，不属于必须朗读内容。"
             "文中红色高亮处为本次新增或修改，其余正文与原打印稿完全一致。")

    d.save(str(DOC_DST))
    print("doc ->", DOC_DST.name, len(d.paragraphs), "段")


if __name__ == "__main__":
    build_deck()
    build_doc()
