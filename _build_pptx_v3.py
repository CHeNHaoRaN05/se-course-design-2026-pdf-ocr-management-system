# -*- coding: utf-8 -*-
"""第27组 设计方案汇报 PPT 构建脚本 v3

相对上一版的改动：
1. 合并/压缩演示截图页（5 页 -> 2 页），为架构与功能页腾出时间预算；
2. 新增「运行架构：进程与两条路径」整页，补讲稿缺失的架构讲解；
3. 新增「分享 / 检索 / 标注」功能页，覆盖 2.0 已实现但未上讲台的能力；
4. 数据库页补 share_links 与 file_tags 两个实体；
5. 所有截图按原始宽高比等比放置。
"""
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Inches, Pt

root = Path(r"C:\Users\Administrator\Desktop\se_course_design")
img = root / "ppt_img"
out = root / "现代软件工程课程设计_03_设计方案汇报_第27组_修订版.pptx"

NAVY = RGBColor(0x1A, 0x30, 0x53)
TEXT = RGBColor(0x23, 0x2D, 0x3C)
MUTED = RGBColor(0x67, 0x71, 0x7F)
PURPLE = RGBColor(0x69, 0x4C, 0x91)
BLUE = RGBColor(0x2F, 0x66, 0xA4)
TEAL = RGBColor(0x26, 0x80, 0x7D)
LIGHT = RGBColor(0xF4, 0xF7, 0xFB)
BORDER = RGBColor(0xD6, 0xDE, 0xE9)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
FONT = "微软雅黑"

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)
blank = prs.slide_layouts[6]
TOTAL = 11


def tbox(s, x, y, w, h, anchor=MSO_ANCHOR.TOP):
    sh = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = sh.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = 0
    tf.margin_right = 0
    tf.margin_top = 0
    tf.margin_bottom = 0
    return sh


def para(tf, text, size, color=TEXT, bold=False, align=PP_ALIGN.LEFT, space=6, first=False, line=None):
    p = tf.paragraphs[0] if first else tf.add_paragraph()
    p.alignment = align
    p.space_before = Pt(0)
    p.space_after = Pt(space)
    if line:
        p.line_spacing = line
    r = p.add_run()
    r.text = text
    r.font.name = FONT
    r.font.size = Pt(size)
    r.font.color.rgb = color
    r.font.bold = bold
    return p


def text(s, x, y, w, h, body, size=13, color=TEXT, bold=False, align=PP_ALIGN.LEFT,
         anchor=MSO_ANCHOR.TOP, line=None, space=4):
    sh = tbox(s, x, y, w, h, anchor)
    tf = sh.text_frame
    lines = body.split("\n")
    for i, ln in enumerate(lines):
        para(tf, ln, size, color, bold, align, space if i < len(lines) - 1 else 0, i == 0, line)
    return sh


def header(s, title, sub, num):
    s.background.fill.solid()
    s.background.fill.fore_color.rgb = WHITE
    bar = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, Inches(0.14))
    bar.fill.solid()
    bar.fill.fore_color.rgb = PURPLE
    bar.line.fill.background()
    bar.shadow.inherit = False
    text(s, 0.65, 0.42, 12.0, 0.55, title, 27, NAVY, True)
    text(s, 0.67, 0.98, 11.5, 0.28, sub, 11, RGBColor(0x5F, 0x69, 0x78))
    text(s, 12.15, 7.08, 0.55, 0.22, str(num), 9, MUTED, False, PP_ALIGN.RIGHT)


def card(s, x, y, w, h, title, body, color=BLUE, ts=16, bs=12.5, fill=LIGHT, gap=0.5, line=None):
    sh = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    sh.adjustments[0] = 0.06
    sh.fill.solid()
    sh.fill.fore_color.rgb = fill
    sh.line.color.rgb = BORDER
    sh.line.width = Pt(0.75)
    sh.shadow.inherit = False
    st = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x), Inches(y), Inches(0.075), Inches(h))
    st.fill.solid()
    st.fill.fore_color.rgb = color
    st.line.fill.background()
    st.shadow.inherit = False
    text(s, x + 0.2, y + 0.13, w - 0.38, 0.3, title, ts, NAVY, True)
    if body:
        text(s, x + 0.2, y + gap, w - 0.38, h - gap - 0.1, body, bs, TEXT, line=line)


def plain(s, x, y, w, h, title, body, color=BLUE, ts=15, bs=12):
    text(s, x, y, w, 0.3, title, ts, color, True)
    text(s, x, y + 0.36, w, h - 0.36, body, bs, TEXT, line=1.25)


def arrow(s, x1, y1, x2, y2, color=BLUE, width=1.25, dash=False, head="triangle"):
    ln = s.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(x1), Inches(y1), Inches(x2), Inches(y2))
    ln.line.color.rgb = color
    ln.line.width = Pt(width)
    lnEl = ln.line._get_or_add_ln()
    if dash:
        d = lnEl.makeelement(qn("a:prstDash"), {"val": "dash"})
        lnEl.append(d)
    h = lnEl.makeelement(qn("a:tailEnd"), {"type": head, "w": "med", "len": "med"})
    lnEl.append(h)
    return ln


def pic(s, name, x, y, w):
    """等比放置：按图片真实宽高算高度。"""
    from PIL import Image

    with Image.open(img / name) as im:
        pw, ph = im.size
    h = w * ph / pw
    s.shapes.add_picture(str(img / name), Inches(x), Inches(y), width=Inches(w), height=Inches(h))
    return h


# ---------------------------------------------------------------- 1 封面
s = prs.slides.add_slide(blank)
s.background.fill.solid()
s.background.fill.fore_color.rgb = WHITE
bar = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, Inches(0.18))
bar.fill.solid()
bar.fill.fore_color.rgb = PURPLE
bar.line.fill.background()
bar.shadow.inherit = False
text(s, 1.0, 1.3, 11.3, 0.7, "现代软件工程课程设计_03", 31, NAVY, True, PP_ALIGN.CENTER)
text(s, 1.0, 2.22, 11.3, 0.62, "基于本地 OCR 的 PDF 文件显示与管理系统", 26, BLUE, True, PP_ALIGN.CENTER)
text(s, 1.0, 3.16, 11.3, 0.4, "项目设计方案汇报", 18, MUTED, False, PP_ALIGN.CENTER)
text(s, 1.0, 5.35, 11.3, 0.35,
     "第27组    陈浩然（2024141460570）  黄俞富（2024141460074）  岳浩睿（2024141460114）",
     14, TEXT, False, PP_ALIGN.CENTER)
text(s, 1.0, 6.35, 11.3, 0.3, "上传 · 阅读 · 管理 · 识别 · 检索 · 分享", 12, MUTED, False, PP_ALIGN.CENTER)

# ---------------------------------------------------------------- 2 项目定位与需求范围
s = prs.slides.add_slide(blank)
header(s, "项目定位与需求范围", "先说明痛点，再界定本期做什么、不做什么", 2)
card(s, 0.75, 1.45, 3.78, 1.55, "现实问题",
     "扫描件和图片型 PDF 只是“图片壳”，能存不能查；云端 OCR 又有数据出域的顾虑。", PURPLE)
card(s, 4.78, 1.45, 3.78, 1.55, "设计目标",
     "纯本地部署、离线可用，把上传、阅读、管理、识别、检索、分享串成可验收闭环。", BLUE)
card(s, 8.81, 1.45, 3.78, 1.55, "范围边界",
     "只做单机最小必须功能集；高级阅读、表格还原、批量处理列入范围外。", TEAL)
text(s, 0.85, 3.2, 5.3, 0.3, "本期范围内", 16, NAVY, True)
text(s, 0.85, 3.68, 5.55, 1.75,
     "• 注册登录、JWT 鉴权、角色与账号禁用\n"
     "• 三类文件上传校验、下载、重命名、标签、回收站\n"
     "• 阅读器分页、跳页、50%–300% 缩放、书签与批注\n"
     "• OCR 任务提交、进度、取消、重试、按页结果",
     13, TEXT, line=1.45)
text(s, 6.95, 3.2, 5.2, 0.3, "本期范围内（续）", 16, NAVY, True)
text(s, 6.95, 3.68, 5.5, 1.75,
     "• TXT / JSON / CSV / HTML / XLSX 五种结果导出\n"
     "• 关键词检索与建议，可按文件、标签、时间过滤\n"
     "• 分享链接：有效期、提取码、下载开关、访问计数\n"
     "• 审计日志与配额查询（管理员视角）",
     13, TEXT, line=1.45)
text(s, 0.85, 5.62, 11.9, 0.7,
     "明确裁剪  连续阅读与目录侧栏、文本层叠加选中、表格还原与校对、批量处理、统计看板、生产部署脚本。",
     13, TEXT)
text(s, 0.85, 6.42, 11.9, 0.3, "判断标准：课程设计 12 周、三人团队，主链路必须先跑通并可验收。", 11.5, MUTED)

# ---------------------------------------------------------------- 3 模块划分与分工
s = prs.slides.add_slide(blank)
header(s, "模块划分与小组分工", "模块边界对应设计文档，三条开发线通过共享契约协作", 3)
card(s, 0.75, 1.45, 3.78, 1.78, "用户与权限",
     "注册、登录、令牌刷新、角色与禁用\n分享链接：令牌、有效期、提取码\n审计日志与访问计数", PURPLE)
card(s, 4.78, 1.45, 3.78, 1.78, "文件与阅读",
     "上传校验、列表、下载、重命名\n标签与回收站、还原、彻底删除\nPDF / 图片阅读、书签与批注", BLUE)
card(s, 8.81, 1.45, 3.78, 1.78, "OCR 与检索",
     "任务队列、按页结果、取消与重试\n五种格式导出、关键词检索与建议\n能力探测与使用量统计", TEAL)
text(s, 0.85, 3.48, 11.4, 0.3, "小组分工", 16, NAVY, True)
card(s, 0.75, 3.9, 3.78, 1.05, "陈浩然",
     "用户与权限、分享、系统整合与前后端联调", PURPLE, 15, 12.5, gap=0.42)
card(s, 4.78, 3.9, 3.78, 1.05, "岳浩睿",
     "文件管理、上传校验、PDF 与图片阅读器", BLUE, 15, 12.5, gap=0.42)
card(s, 8.81, 3.9, 3.78, 1.05, "黄俞富",
     "OCR 引擎适配、任务生命周期、全文检索", TEAL, 15, 12.5, gap=0.42)
text(s, 0.85, 5.22, 11.6, 0.3, "共享契约", 16, NAVY, True)
text(s, 0.85, 5.62, 5.6, 0.95,
     "接口契约  统一 HTTP 请求出口；资源权限统一返回；\n下载、导出、分享都走同一套鉴权入口。", 12.5, TEXT, line=1.3)
text(s, 6.95, 5.62, 5.5, 0.95,
     "数据契约  files.id、storage_key、media_type、page_count；\nOCR generation 与页状态；索引来源 job_id。", 12.5, TEXT, line=1.3)
text(s, 0.85, 6.45, 11.6, 0.3, "模块化的收益：替换 OCR 引擎或数据库实现，用户主流程不需要改。", 11.5, MUTED)

# ---------------------------------------------------------------- 4 分层架构
s = prs.slides.add_slide(blank)
header(s, "系统分层架构", "五层职责单一，依赖只向下，耗时的识别不进入请求链路", 4)
card(s, 0.8, 1.42, 11.75, 0.82, "展现层",
     "React + Vite：登录、文件库、上传、阅读器、OCR 面板、检索、我的分享", BLUE, 15, 12.5, gap=0.44)
card(s, 0.8, 2.38, 11.75, 0.82, "接口层",
     "FastAPI：JWT 鉴权、文件 API、阅读器 API、任务 API、检索与分享 API、导出", PURPLE, 15, 12.5, gap=0.44)
card(s, 0.8, 3.34, 5.72, 0.98, "业务服务层",
     "用户与权限 / 文件管理 / 阅读器 / OCR 生命周期 / 检索 / 分享", TEAL, 15, 12, gap=0.46)
card(s, 6.83, 3.34, 5.72, 0.98, "任务执行层",
     "SQLite 队列表 + 独立 OCR worker：领取、逐页识别、回写", PURPLE, 15, 12, gap=0.46)
card(s, 0.8, 4.48, 11.75, 0.95, "数据与存储层",
     "SQLite：元数据、任务、页结果、全文索引、分享记录　　本地目录：原文件、模型权重", BLUE, 15, 12.5, gap=0.46)
for y in (2.24, 3.2, 4.32):
    arrow(s, 6.67, y, 6.67, y + 0.14, MUTED, 1.0)
text(s, 0.85, 5.62, 11.7, 0.35, "两条设计取舍", 15, NAVY, True)
text(s, 0.85, 6.0, 5.7, 0.85,
     "鉴权集中  权限判断只写在接口层，服务层只接收已确认的\n主体，避免每个模块各写一套越权检查。", 12, TEXT, line=1.25)
text(s, 6.83, 6.0, 5.7, 0.85,
     "识别外置  OCR 不在请求进程里执行，接口写完队列即返回，\n进程崩溃不会留下半截任务状态。", 12, TEXT, line=1.25)

# ---------------------------------------------------------------- 5 运行架构
s = prs.slides.add_slide(blank)
header(s, "运行架构：三个进程与两条路径", "单机部署，同步路径管页面，异步路径管识别，两者只在数据库上交接", 5)
card(s, 0.7, 1.45, 2.95, 1.5, "浏览器",
     "React + Vite 单页应用\npdf.js 渲染 PDF\n按固定间隔轮询任务进度", BLUE, 15, 11.5, gap=0.46)
card(s, 4.1, 1.45, 3.6, 1.5, "FastAPI 应用进程",
     "路由层：64 个接口，统一 JWT 鉴权\n服务层：按业务域拆分，单模块单目录\nORM：单请求单事务，查询上做权限过滤", PURPLE, 15, 11.5, gap=0.46)
card(s, 9.05, 1.45, 3.55, 1.5, "数据与存储",
     "SQLite：元数据、队列、页结果、索引\n本地目录：原文件、模型权重\n不依赖任何外部服务", TEAL, 15, 11.5, gap=0.46)
arrow(s, 3.67, 2.2, 4.07, 2.2, BLUE, 1.5)
text(s, 3.55, 1.9, 0.65, 0.2, "HTTP", 8.5, MUTED, False, PP_ALIGN.CENTER)
arrow(s, 7.72, 2.2, 9.02, 2.2, PURPLE, 1.5)
text(s, 7.95, 1.9, 0.85, 0.2, "ORM", 8.5, MUTED, False, PP_ALIGN.CENTER)
card(s, 9.05, 3.5, 3.55, 1.05, "OCR worker（独立进程）",
     "轮询队列 → 渲染页面 → 引擎识别 → 回写结果", PURPLE, 13.5, 11, gap=0.42)
arrow(s, 10.82, 2.98, 10.82, 3.46, PURPLE, 1.25)
text(s, 10.95, 3.05, 1.9, 0.25, "领取任务 / 回写结果", 8.5, MUTED)
card(s, 0.7, 3.5, 3.9, 1.05, "① 同步路径",
     "页面请求进程内完成，毫秒级返回，不等识别", BLUE, 13.5, 11, gap=0.42)
card(s, 4.78, 3.5, 3.9, 1.05, "② 异步路径",
     "任务落库 → worker 领取 → 回写 → 前端轮询", TEAL, 13.5, 11, gap=0.42)
text(s, 0.8, 4.95, 11.9, 1.5,
     "• 三个进程同机：浏览器、FastAPI 应用、OCR worker，离线可运行，无外部依赖\n"
     "• 队列不引入消息中间件：单机规模下，数据库表加状态字段即可支撑领取、重试与取消\n"
     "• 鉴权只发生在接口层：worker 只访问本机数据库与文件目录，不对外暴露端口",
     12.5, TEXT, line=1.5)
text(s, 0.8, 6.35, 11.9, 0.3, "架构收益：识别慢、识别失败、worker 重启，都不会改变页面请求的响应时间。", 11.5, MUTED)

# ---------------------------------------------------------------- 6 数据库
s = prs.slides.add_slide(blank)
header(s, "数据库实体关系", "主系统管理资源与分享，OCR 侧管理识别过程，文件编号贯穿两侧", 6)
ents = [
    ("users", "账号·角色·禁用", PURPLE),
    ("files", "名称·类型·页数", BLUE),
    ("file_tags", "标签·多对多", TEAL),
    ("share_links", "令牌·有效期", BLUE),
    ("ocr_jobs", "状态·代次", PURPLE),
    ("ocr_pages", "页文本·识别框", TEAL),
    ("text_index", "全文索引", BLUE),
]
x = 0.7
for name, desc, c in ents:
    card(s, x, 1.45, 1.62, 1.0, name, desc, c, 13, 10.5, gap=0.42)
    x += 1.75
text(s, 0.85, 2.72, 11.6, 0.3, "四条关键关系", 16, NAVY, True)
rels = [
    ("用户拥有文件", "users 1 —— N files\nowner_id 用于权限过滤", PURPLE),
    ("文件产生任务", "files 1 —— N ocr_jobs\n同时只允许一个活动任务", BLUE),
    ("任务产生页结果", "ocr_jobs 1 —— N ocr_pages\n页结果与索引同一事务", TEAL),
    ("文件产生分享", "files 1 —— N share_links\n只存令牌，不复制文件", BLUE),
]
x = 0.7
for t, b, c in rels:
    card(s, x, 3.15, 2.85, 1.15, t, b, c, 14, 11, gap=0.44)
    x += 3.07
text(s, 0.8, 4.6, 11.9, 1.55,
     "一致性字段  files.id 是 OCR 镜像的关联键；generation 区分新旧识别结果，旧任务晚完成也不能覆盖；\n"
     "deleted_at 支持回收站并保留关联数据；页结果与全文索引在同一事务写入，避免“任务成功但结果缺失”。",
     12.5, TEXT, line=1.35)
text(s, 0.8, 5.95, 11.9, 0.85,
     "分享的存储口径  share_links 只保存令牌、有效期、提取码、下载开关与访问计数，引用 file_id；\n"
     "撤销分享只是置为失效，原文件与识别结果不受影响。",
     12.5, TEXT, line=1.35)
text(s, 0.8, 6.85, 11.9, 0.3, "两张 OCR 表由 OCR 模块独占写入，主系统只读索引，避免两套模型争用同一张表。", 11, MUTED)

# ---------------------------------------------------------------- 7 OCR 链路
s = prs.slides.add_slide(blank)
header(s, "上传到 OCR 的异步链路", "把用户操作、后端校验、队列、worker 和结果回写连成闭环", 7)
steps = [
    ("1 上传", "浏览器提交文件", BLUE),
    ("2 校验", "内容·大小·页数", PURPLE),
    ("3 入队", "写入 ocr_jobs", TEAL),
    ("4 执行", "worker 逐页识别", PURPLE),
    ("5 回写", "页结果 + 索引", BLUE),
    ("6 展示", "进度·结果·导出", TEAL),
]
x = 0.55
for i, (t, b, c) in enumerate(steps):
    card(s, x, 1.9, 1.85, 1.05, t, b, c, 14, 11, gap=0.42)
    if i < 5:
        arrow(s, x + 1.87, 2.42, x + 2.1, 2.42, MUTED, 1.1)
    x += 2.12
text(s, 0.85, 3.25, 11.6, 0.3, "三个容易出错的地方", 16, NAVY, True)
card(s, 0.75, 3.7, 3.78, 1.35, "取消",
     "先释放队列状态再删文件，避免删除中的文件仍被 worker 读取。", BLUE, 14.5, 11.5, gap=0.44)
card(s, 4.78, 3.7, 3.78, 1.35, "重试",
     "只重跑失败页，成功页不重复计算，避免重复计费与重复写索引。", PURPLE, 14.5, 11.5, gap=0.44)
card(s, 8.81, 3.7, 3.78, 1.35, "防覆盖",
     "代次 generation 单调递增，旧任务回写时校验代次，不匹配即丢弃。", TEAL, 14.5, 11.5, gap=0.44)
text(s, 0.85, 5.35, 11.8, 0.9,
     "为什么异步  识别一册文档是分钟级操作，占满请求进程会让页面卡死；拆成队列加 worker 之后，\n"
     "进度可被轮询观察，失败可单独重试，前端也不需要长连接。",
     12.5, TEXT, line=1.4)
text(s, 0.85, 6.45, 11.8, 0.3, "本版目标是链路跑通，不承诺准确率指标；准确率评测与表格还原列入范围外。", 11, MUTED)

# ---------------------------------------------------------------- 8 分享 / 检索 / 标注
s = prs.slides.add_slide(blank)
header(s, "三条容易被忽略的能力：分享、检索、标注", "2.0 版本已落地，都复用同一套权限规则", 8)
card(s, 0.7, 1.45, 3.85, 2.0, "分享与协作",
     "不复制文件实体，只为文件生成一条\n带随机令牌的分享记录；可设有效期、\n提取码，可关闭下载；访问累计计数，\n撤销立即失效。", PURPLE, 15, 11.5, gap=0.46)
card(s, 4.78, 1.45, 3.85, 2.0, "全文检索",
     "直接读 OCR 回写的索引表，不改 OCR\n表结构；MySQL 用 ngram 分词，SQLite\n降级为子串匹配；可按文件、标签、时间、\n媒体类型过滤，并提供关键词建议。", BLUE, 15, 11.5, gap=0.46)
card(s, 8.86, 1.45, 3.85, 2.0, "书签与批注",
     "按“文件 + 用户”隔离，只影响本人；\n坐标归一化存储，缩放不错位；批注\n可增可删，阅读位置与页面解耦。", TEAL, 15, 11.5, gap=0.46)
text(s, 0.85, 3.66, 11.6, 0.3, "分享的一次访问经过哪些校验", 15, NAVY, True)
chain = [
    ("创建分享", "有效期、提取码、\n下载开关"),
    ("生成令牌", "随机串 + 数据库记录"),
    ("打开链接", "令牌存在且未撤销"),
    ("校验", "未过期 + 提取码正确"),
    ("只读访问", "按设置允许或禁止下载"),
]
x = 0.72
for i, (t, b) in enumerate(chain):
    card(s, x, 4.1, 2.15, 1.2, t, b, PURPLE if i % 2 == 0 else BLUE, 13.5, 10.5, gap=0.44)
    if i < 4:
        arrow(s, x + 2.17, 4.7, x + 2.36, 4.7, MUTED, 1.1)
    x += 2.38
text(s, 0.85, 5.55, 11.8, 0.9,
     "权限口径  访问他人资源返回 404 而不是 403，避免资源探测；分享访问以令牌为主体，不提升原文件权限；\n"
     "检索在 SQL 层就按 owner_id 过滤，未登录用户无法通过任何入口读到未分享的内容。",
     12.5, TEXT, line=1.4)
text(s, 0.85, 6.65, 11.8, 0.3, "这三项都不新增数据实体，只复用 files 与权限模型，因此没有扩大验收范围。", 11, MUTED)

# ---------------------------------------------------------------- 9 界面：文件库与阅读器
s = prs.slides.add_slide(blank)
header(s, "界面：文件库与阅读器", "文件库是主工作台，阅读器把 PDF 与图片收进同一入口", 9)
h1 = pic(s, "use_lib.png", 0.7, 1.35, 5.95)
h2 = pic(s, "use_reader_pdf.png", 6.75, 1.35, 5.95)
text(s, 0.75, 1.35 + h1 + 0.12, 5.9, 0.3, "文件库：分类、标签、识别状态与操作入口", 11.5, MUTED)
text(s, 6.8, 1.35 + h2 + 0.12, 5.9, 0.3, "阅读器：PDF 分页、跳页、缩放与 OCR 入口", 11.5, MUTED)
text(s, 0.75, 5.35, 11.85, 0.95,
     "· 列表按需展示名称、大小、页数、识别状态与上传日期，操作列收敛为“打开 + 更多”\n"
     "· 回收站与“我的分享”是并列入口，删除先入回收站，正在识别的任务需要先取消\n"
     "· 阅读器用 pdf.js 渲染，50%–300% 按 10% 步进缩放，书签与批注在侧栏统一管理",
     12, TEXT, line=1.3)
text(s, 0.75, 6.75, 11.85, 0.3, "截图取自本机运行实例，左侧导航与页面标题保持中文一致。", 11, MUTED)

# ---------------------------------------------------------------- 10 界面：OCR 与导出
s = prs.slides.add_slide(blank)
header(s, "界面：识别任务与结果导出", "先给状态再给结果，导出直接消费页结果，不重复识别", 10)
h3 = pic(s, "use_ocr.png", 0.7, 1.35, 5.95)
h4 = pic(s, "use_export.png", 6.75, 1.35, 5.95)
text(s, 0.75, 1.35 + h3 + 0.12, 5.9, 0.3, "任务面板：排队、执行、完成与按页结果", 11.5, MUTED)
text(s, 6.8, 1.35 + h4 + 0.12, 5.9, 0.3, "导出结果：按页分段的纯文本，可在外部编辑器打开", 11.5, MUTED)
three = [
    ("TXT / JSON", "供外部程序复用，JSON 保留坐标与页码"),
    ("CSV / XLSX", "供表格核对，转义防止公式注入"),
    ("HTML", "保留分页结构，适合直接投屏查看"),
]
x = 0.7
for t, b in three:
    card(s, x, 5.55, 3.85, 1.0, t, b, TEAL, 14, 11, gap=0.44)
    x += 4.05
text(s, 0.75, 6.75, 11.85, 0.3, "同一份页结果支持五种格式，导出不触发重新识别。", 11, MUTED)

# ---------------------------------------------------------------- 11 收束
s = prs.slides.add_slide(blank)
header(s, "汇报收束", "三句话说明这套设计解决什么问题", 11)
card(s, 0.75, 1.45, 3.78, 1.85, "架构",
     "前端负责交互，FastAPI 负责业务与鉴权，SQLite 与本地目录负责数据，OCR worker 负责耗时识别；两条路径在数据库上交接。", BLUE, 17, 12.5, gap=0.52)
card(s, 4.78, 1.45, 3.78, 1.85, "数据",
     "users、files、share_links、ocr_jobs、ocr_pages、text_index 构成从资源到结果再到共享的可追踪链路。", PURPLE, 17, 12.5, gap=0.52)
card(s, 8.81, 1.45, 3.78, 1.85, "能力",
     "上传、阅读、管理、识别、检索、分享六个动作都在本机完成，受同一套权限约束。", TEAL, 17, 12.5, gap=0.52)
text(s, 0.9, 3.62, 11.6, 0.6,
     "核心结论  最小功能集完成可运行、可解释、可扩展的本地文档管理与 OCR 方案。",
     21, NAVY, True, PP_ALIGN.CENTER)
text(s, 0.9, 4.5, 11.6, 0.6,
     "后续工作  接入版面分析模型补表格还原，OCR 引擎做成可插拔适配层，检索补页内高亮。",
     12.5, TEXT, False, PP_ALIGN.CENTER)
text(s, 0.9, 5.55, 11.6, 0.5, "谢谢各位老师，请提问。", 18, MUTED, False, PP_ALIGN.CENTER)
text(s, 0.9, 6.7, 11.6, 0.3, "第27组   陈浩然 · 黄俞富 · 岳浩睿", 11.5, MUTED, False, PP_ALIGN.CENTER)

prs.save(out)
print(out, len(prs.slides.__iter__.__self__._sldIdLst))
