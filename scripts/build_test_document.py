"""生成《软件测试文档》V1.1（纯黑白、无“现场记录”栏、用例全部实测可过）。

用法：python scripts/build_test_document.py
输出：docs/testing/软件测试文档_V1.1.docx
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT, WD_TAB_LEADER
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "testing" / "软件测试文档_V1.0.docx"

BLACK = RGBColor(0, 0, 0)
BODY_FONT_CN = "宋体"
HEAD_FONT_CN = "黑体"
LATIN = "Times New Roman"

# ---------------------------------------------------------------- 用例数据
AUTH = [
    ("TC-AUTH-01", "新用户注册并自动登录", "FR-USER-01", "P0",
     "数据库可用；邮箱未注册。",
     "demo-<唯一编号>@example.com；Password123",
     ["POST /api/v1/auth/register 提交邮箱与密码。",
      "用返回的令牌请求 GET /api/v1/auth/me。"],
     ["201，响应仅含 access_token、expires_in、role=user，不含 password_hash。",
      "me 返回 200，role=user。"],
     "响应体不得回显任何口令字段。"),
    ("TC-AUTH-02", "登录成功与错误口令拦截", "FR-USER-02", "P0",
     "已注册账号。",
     "同一邮箱；错误口令 Wrong123；正确口令 Password123",
     ["用错误口令调用 POST /api/v1/auth/login。",
      "用正确口令登录，携带令牌请求 /auth/me。"],
     ["401，响应头 WWW-Authenticate: Bearer，detail=邮箱或密码不正确。",
      "200，token_type=bearer；me 200。"],
     "错误口令不得返回 422（那是请求体校验失败的语义）。"),
    ("TC-AUTH-03", "注册输入校验与重复账号", "FR-USER-01", "P1",
     "服务正常；邮箱与口令规则见表 3-4。",
     "非法邮箱 bad-email；短口令 123；已注册邮箱",
     ["依次提交三类非法注册。"],
     ["非法邮箱 422；短口令 422；重复邮箱 409；均不产生第二个账号。"],
     ""),
    ("TC-AUTH-04", "登出吊销服务端令牌", "FR-USER-04", "P0",
     "已登录。",
     "当前访问令牌",
     ["POST /api/v1/auth/logout。",
      "用同一令牌再请求 /auth/me。"],
     ["204。", "me 返回 401，说明服务端已吊销，不只是前端清凭据。"],
     ""),
    ("TC-AUTH-05", "修改密码与旧令牌失效", "FR-USER-05", "P1",
     "已登录，持有旧令牌。",
     "错误旧口令；正确旧口令；NewPassword123",
     ["用错误旧口令改密。", "用正确旧口令改密。",
      "用旧口令登录、用旧令牌请求 me、用新口令登录。"],
     ["错误旧口令 403（不用 401，避免前端误判会话过期）。",
      "改密 200。", "旧口令 401；旧令牌 401；新口令 200。"],
     ""),
    ("TC-AUTH-06", "刷新令牌并轮换旧令牌", "FR-USER-03", "P1",
     "已登录。",
     "当前访问令牌",
     ["POST /api/v1/auth/refresh。", "用新令牌请求 me；用旧令牌请求 me。"],
     ["200，返回新的 access_token。", "新令牌 200；旧令牌 401（轮换即吊销）。"],
     "需求写的是“刷新令牌”，实现为当前令牌换取新令牌并吊销旧的。"),
]

FILE = [
    ("TC-FILE-01", "上传两页 PDF 并写入分类与标签", "FR-FILE-01/05/06", "P0",
     "已登录；样本 D-01 存在。",
     "D-01-两页正常.pdf；folder=/课程设计；tags=[验收]",
     ["POST /api/v1/files 上传。", "PATCH /api/v1/files/{id} 写入分类与标签。",
      "GET 详情核对。"],
     ["201，media_type=application/pdf，page_count=2，按内容判定而非扩展名。",
      "PATCH 200。", "详情 folder=/课程设计，tags 含“验收”。"],
     "界面把“上传 + 归档”合成一步，接口是两次调用。"),
    ("TC-FILE-02", "同名 PDF 上传生成唯一名称", "FR-FILE-01", "P1",
     "已登录。",
     "同一份文件以 same.pdf 连续上传 4 次",
     ["连续上传 4 次，刷新列表。"],
     ["四条记录并存，名称依次为 same.pdf、same(1).pdf、same(2).pdf、same(3).pdf，不互相覆盖。"],
     ""),
    ("TC-FILE-03", "非法、损坏与加密 PDF 一律拒绝", "FR-FILE-01", "P0",
     "已登录；样本 D-03、D-04、D-05 存在。",
     "改扩展名文本、截断 PDF、AES 加密 PDF",
     ["分别上传三类文件。"],
     ["文本改名 422，detail=invalid_image。",
      "损坏 PDF 422，detail=invalid_or_encrypted_pdf。",
      "加密 PDF 422，detail=invalid_or_encrypted_pdf；三条都不留记录、不留半成品。"],
     "加密样本由 prepare_demo 用 pypdf 生成（口令 demo123）。"),
    ("TC-FILE-04", "列表分页、关键词筛选与空态", "FR-FILE-02", "P1",
     "当前用户已上传 14 个 document-NN.pdf（prepare_demo --seed）。",
     "limit=12、offset=0 与 offset=12；q=document-13",
     ["打开文件库，记录总数与首页条数。", "翻到第二页。",
      "输入关键词 document-13 检索。"],
     ["total≥14，首页 12 条，第二页为剩余条目。",
      "关键词只命中 1 条。", "服务异常时显示加载失败，不显示为“空库”。"],
     ""),
    ("TC-FILE-05", "重命名、分类与标签持久化", "FR-FILE-03/05/06", "P0",
     "已有文件。",
     "name=after.pdf；folder=/真实/验收；tags=[test, 验收]",
     ["PATCH 后 GET 详情。", "另开标签页刷新列表核对同一文件。"],
     ["PATCH 200；详情名称、分类、标签与提交值一致；另一标签页刷新后一致。"],
     "分类为最多 5 级的路径字符串，不是树控件。"),
    ("TC-FILE-06", "软删除、回收站、还原与彻底删除", "FR-FILE-04", "P0",
     "已有文件，且该文件可能关联过 OCR 任务。",
     "可删除文件 A",
     ["DELETE /files/{id} 软删除。", "GET /files/trash?envelope=true 查看回收站。",
      "POST /files/{id}/restore 还原。", "再次删除后 DELETE /files/{id}/purge。"],
     ["200，列表不再显示，回收站可见。", "还原 200，文件回到列表。",
      "彻底删除 204；再次 GET 返回 404。",
      "若文件带历史 OCR 任务，purge 仍须 204，不得 500。"],
     "带历史 OCR 任务的文件也必须能彻底删除，不得因配额账本缺口返回 500。"),
    ("TC-FILE-07", "原文件下载与响应头", "FR-FILE-11", "P0",
     "已有正常 PDF。",
     "download.pdf",
     ["GET /api/v1/files/{id}/content。", "未登录状态重复一次。"],
     ["200，Content-Type=application/pdf，Content-Disposition 带原文件名。",
      "未登录 401；他人令牌 404。"],
     "响应为 inline，页面“下载”按钮由前端把流另存为文件。"),
    ("TC-FILE-08", "越权访问他人文件统一 404", "NFR-SEC-02/03", "P0",
     "用户 A、B 均已注册，A 有文件。",
     "B 的令牌 + A 的 file_id",
     ["用 B 依次请求 A 文件的详情、内容、删除、还原。"],
     ["四个接口全部 404，不泄露文件是否存在。"],
     ""),
]

READ = [
    ("TC-READ-01", "阅读器渲染、翻页、跳页与缩放", "FR-READ-01/02/03", "P0",
     "已有两页 PDF，已登录。",
     "D-01-两页正常.pdf",
     ["GET /files/{id}/pages 取页尺寸。", "打开 /files/{id}，观察页码与画布。",
      "点上一页/下一页，输入越界页码跳转。", "连续点缩小/放大到底。"],
     ["200，返回 2 项页尺寸。", "画布按页渲染，页码显示 1/2，首页“上一页”禁用。",
      "页码被钳制在 1–2，不会越界。", "缩放范围 50%–300%，到达端点后按钮不再改变数值。"],
     "缩放上限按设计 V2.0 取 300%（需求原文 400%，设计阶段已作调整）；上下限钳制由 verify-demo-ui.mjs 的 full 模式在浏览器里实测。"),
    ("TC-READ-02", "添加与删除书签", "FR-READ-06", "P1",
     "已打开第 2 页。",
     "page_no=2；title=第 2 页",
     ["POST /files/{id}/reader/bookmarks。", "GET 同一路径核对。", "DELETE 该 id。"],
     ["201，返回 id 与页码。", "列表含 1 条。", "204，列表清空。"],
     "验证书签的增删查；阅读位置由前端本地保存，不在接口层判定。"),
    ("TC-READ-03", "添加与删除批注", "FR-READ-07", "P1",
     "已打开 PDF。",
     "page_no=1; kind=note; text=本机验收批注",
     ["POST /files/{id}/reader/annotations。", "GET 列表。", "DELETE 该 id。"],
     ["201。", "列表含该条批注与页码。", "204；当前页提示暂无批注。"],
     ""),
]

SHARE = [
    ("TC-SHARE-01", "创建带提取码且禁止下载的分享", "FR-SHR-01/04", "P0",
     "已登录且拥有文件。",
     "expires_in_days=7；access_code=abc123；allow_download=false",
     ["POST /api/v1/share 创建。", "用错误提取码访问 token。",
      "用正确提取码访问 token。", "用正确提取码请求第 1 页预览图。"],
     ["201，返回 token 与 share_url。", "错误提取码 404（与不存在同码，不泄露）。",
      "200，Content-Type=application/json，仅元数据，不返回原文件。",
      "200，Content-Type=image/png，游客可只读浏览；请求第 3 页 422。"],
     "禁下载的语义是“不给原文件、给页面图”；页面提示不提供下载入口。"),
    ("TC-SHARE-02", "撤销分享后链接立即失效", "FR-SHR-02", "P0",
     "已有分享链接。",
     "正确提取码；撤销后的同一 token",
     ["DELETE /api/v1/share/{id}。", "再次访问 token。"],
     ["204。", "404，链接立即失效。"],
     ""),
    ("TC-SHARE-03", "提取码字符集与长度校验", "FR-SHR-01", "P1",
     "已登录。",
     "1 位、32 位、空格、零宽字符、特殊字符、33 位",
     ["依次用六种取值创建分享。"],
     ["1 位与 32 位字母数字 201；空格、零宽、ab@#、33 位全部 422。"],
     "规则为 1–32 位字母数字；需求未规定更短的下限，故不期望拦截 1 位。"),
    ("TC-SHARE-04", "允许下载时游客直接取原文件", "FR-SHR-01/04", "P1",
     "已创建 allow_download=true 的分享。",
     "同一 token，无提取码",
     ["GET /api/v1/share/token/{token}。"],
     ["200，Content-Type=application/pdf，游客可直接打开原文件。"],
     ""),
]

SEARCH = [
    ("TC-SEARCH-01", "关键词检索、片段与权限过滤", "FR-SEA-01/02/07", "P0",
     "已执行 prepare_demo --seed-index（模拟已完成识别，用于验证链路，不证明准确率）。",
     "q=验收",
     ["GET /api/v1/search?q=验收。", "换另一账号重复检索。"],
     ["200，backend=substring，命中 ≥3 条，每条含 file_name、page_no、snippet。",
      "只返回本人文件；他人文件不出现。"],
     "夹具只在演示库写入，真实识别仍以 OCR worker 实测为准。"),
    ("TC-SEARCH-02", "建议与参数校验", "FR-SEA-01", "P1",
     "服务正常。",
     "suggest q=doc；q=空格；q=101 字符；tag=空格",
     ["依次调用 /search/suggest 与 /search。"],
     ["建议 200；空白查询 422；101 字符 422（上限 100）；空白标签 422。"],
     "边界取 101 而不是 256：100 是上限，101 才是第一个越界值。"),
    ("TC-SEARCH-03", "特殊字符按字面处理", "FR-SEA-01", "P1",
     "索引中存在含特殊字符的文本。",
     "q=100%_\\；q=<script>alert(1)</script>",
     ["分别检索。", "在检索页查看片段渲染结果。"],
     ["两者均按字面命中（各 ≥1 条），接口返回的 snippet 原样包含该字符串。",
      "页面以文本节点渲染片段，不弹出脚本对话框。"],
     "片段按文本节点渲染（前端用文本插值，不拼 HTML）；verify-demo-ui.mjs 实测无脚本对话框。"),
    ("TC-SEARCH-04", "OCR 未挂载时的降级提示", "FR-SEA-01", "P1",
     "以 PDF_OCR_ENABLED=false 启动服务。",
     "q=验收；GET /ocr-host/capabilities",
     ["在未挂载实例上检索。", "查看能力探测。"],
     ["200，backend=ocr_not_ready，items 为空。",
      "mounted=false；页面提示“OCR 服务尚未就绪，请启动服务后重试。”，"
      "不显示为“没有找到匹配内容”。"],
     "用于区分“没索引”和“没命中”，避免现场误判。"),
]

OCR = [
    ("TC-OCR-01", "能力探测与挂载状态", "FR-OCR-07", "P0",
     "主系统已启动。",
     "mounted=true 与 false 两种实例",
     ["GET /api/v1/ocr-host/capabilities。", "在未挂载实例打开阅读器，观察右侧面板。"],
     ["200，返回 mounted、storage、device、quota_per_month。",
      "mounted=false 时页面提示“OCR 服务未挂载”，开始识别按钮禁用。"],
     "未挂载分支由 verify-demo-ui.mjs 的 degraded 模式实测（第二个实例 PDF_OCR_ENABLED=false）。"),
    ("TC-OCR-02", "提交整册与指定页任务", "FR-OCR-02/04", "P0",
     "文件已同步到 OCR 侧；同一文件同时只允许一个活动任务。",
     "pages 留空；pages=[1]；pages=[99]",
     ["提交整册任务。", "同一文件立刻再次提交。", "提交页码 99。"],
     ["202，job_id 有效，status=queued，pages=[1,2]。",
      "重复提交 409（File already has an active OCR job）。",
      "越界 422（Page number out of range）。"],
     "取消任务后文件被释放，可以再次提交。"),
    ("TC-OCR-03", "轮询进度与按页结果", "FR-OCR-04", "P0",
     "存在 queued 任务；无 worker 时任务停留在排队态。",
     "job_id",
     ["GET /ocr/jobs/{id} 轮询。", "GET /ocr/jobs/{id}/pages。"],
     ["200，status∈{queued,running}，progress.percent 在 0–100，succeeded=0。",
      "页列表每页为 pending/running；未完成不得显示成功。"],
     "有 worker 时此处应观察到 percent 递增与 succeeded 页，属环境条件项。"),
    ("TC-OCR-04", "取消任务与重复取消", "FR-OCR-05", "P1",
     "任务处于 queued 或 running。",
     "job_id",
     ["POST /ocr/jobs/{id}/cancel。", "再次取消同一任务。"],
     ["200，status=cancelled。", "409（Job is already terminal），提示可解释。"],
     ""),
    ("TC-OCR-05", "重试的前置条件", "FR-OCR-06", "P1",
     "分别准备 queued 任务与 cancelled 任务。",
     "job_id",
     ["对 queued 任务重试。", "对 cancelled 任务重试。"],
     ["409（Only failed or partially successful jobs may be retried）。",
      "同样 409；说明重试只对失败/部分成功开放。"],
     "真实失败页重试需 worker，属环境条件项。"),
    ("TC-OCR-06", "导出在结果未就绪时拒绝", "FR-EXP-01~06", "P1",
     "存在 cancelled 任务（无成功页）。",
     "format=xlsx；format=txt&allow_partial=true；format=xml",
     ["请求 format=xlsx。", "请求 format=txt&allow_partial=true。", "请求 format=xml。"],
     ["409（Result incomplete）。",
      "即使 allow_partial=true 仍 409，因为没有任何成功页。",
      "format 非法 422。"],
     "五种格式的成功导出需 worker，属环境条件项。"),
    ("TC-OCR-07", "任务结算的时机与幂等", "FR-LOG-02", "P1",
     "存在 queued 任务；另准备一个两页全部成功的任务。",
     "job_id；成功任务的 2 个已成功页",
     ["未终态时 POST /ocr-host/jobs/{id}/settle。",
      "取消后结算，并重复一次。",
      "对成功任务结算，再结算一次，核对配额账本与已用页数。"],
     ["409（任务尚未结束，暂不结算）。",
      "200，settled=false（取消任务无成功页，不产生扣减）。",
      "成功任务结算 200、settled=true；账本新增 1 条 job_close，pages_used 等于成功页数，pages_reserved 归零；"
      "再次结算 200、settled=false，job_close 仍为 1 条，pages_used 不变。"],
     ""),
]

SEC = [
    ("TC-SEC-01", "路径穿越与文件名净化", "NFR-SEC-05", "P0",
     "已登录。",
     "../secret.pdf",
     ["以带路径片段的文件名上传。"],
     ["201，返回名称已净化为 secret.pdf；物理文件落在存储目录 uploads/ 下，存储目录之外不产生同名文件。"],
     "存储键固定为 uploads/{uid}.bin，原文件名不参与路径；脚本会遍历存储目录核对。"),
    ("TC-SEC-02", "只读角色阻断一切写操作", "NFR-SEC-02", "P0",
     "viewer 账号已由 prepare_demo 创建。",
     "viewer 令牌",
     ["GET /files 查看列表。", "尝试上传、改名、加书签、删除。", "访问他人文件详情。"],
     ["200，返回空列表（viewer 不拥有文件）。",
      "四个写操作全部 403，数据不变。", "404。"],
     "viewer 在归属模型下没有自有文件，故只验证“读不越权、写全拒绝”。"),
    ("TC-SEC-03", "管理员接口与审计分页", "FR-USER-06 + FR-LOG-06", "P1",
     "user 与 admin 账号已准备。",
     "GET /auth/users?envelope=true；GET /audit?limit=1",
     ["用普通用户请求用户列表。", "用 admin 请求用户列表（envelope=true）与审计。"],
     ["403。",
      "用户列表 200，返回 items/total/limit/offset 且不含 password_hash；"
      "审计 200，未带 envelope 时返回数组，limit=1 即 1 条。"],
     ""),
    ("TC-SEC-04", "未登录访问受保护资源", "NFR-SEC-01", "P1",
     "不携带 Authorization。",
     "GET /auth/me；GET /files；GET /files/{id}/content",
     ["依次请求三个受保护资源。"],
     ["全部 401；前端跳转登录页并保留来源路径。"],
     "未登录访问一律 401；不依赖任何注入手段，现场可直接复现。"),
]

CASES = [("5.1", "用户与权限", AUTH), ("5.2", "文件上传与管理", FILE),
         ("5.3", "阅读器与标注", READ), ("5.4", "分享", SHARE),
         ("5.5", "全文检索", SEARCH), ("5.6", "OCR 任务", OCR),
         ("5.7", "安全与可靠性", SEC)]


# ---------------------------------------------------------------- 基础工具
def set_run(run, size=10.5, bold=False, cn=BODY_FONT_CN):
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = BLACK
    run.font.name = LATIN
    run._element.rPr.rFonts.set(qn("w:eastAsia"), cn)


def body(doc, text, *, size=10.5, bold=False, indent=True, align=None, space_after=4):
    p = doc.add_paragraph()
    fmt = p.paragraph_format
    fmt.space_before = Pt(0)
    fmt.space_after = Pt(space_after)
    fmt.line_spacing = 1.4
    if indent:
        fmt.first_line_indent = Pt(size * 2)
    if align is not None:
        p.alignment = align
    set_run(p.add_run(text), size=size, bold=bold)
    return p


def bullet(doc, text, size=10.5):
    p = doc.add_paragraph(style="List Bullet")
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.line_spacing = 1.3
    set_run(p.add_run(text), size=size)
    return p


HEADINGS: list[tuple[int, str]] = []


def heading(doc, text, level):
    sizes = {1: 16, 2: 13.5, 3: 11.5}
    if level <= 2:
        HEADINGS.append((level, text))
    p = doc.add_heading(level=level)
    p.paragraph_format.space_before = Pt(12 if level == 1 else 8)
    p.paragraph_format.space_after = Pt(6)
    p.paragraph_format.keep_with_next = True      # 标题不得单独留在页底
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    for run in p.runs:
        run.text = ""
    set_run(p.add_run(text), size=sizes[level], bold=True, cn=HEAD_FONT_CN)
    return p


def caption(doc, text):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after = Pt(3)
    p.paragraph_format.keep_with_next = True      # 表题必须与表体同页
    set_run(p.add_run(text), size=9, bold=True)
    return p


def _cell_borders(cell):
    tcPr = cell._tc.get_or_add_tcPr()
    borders = OxmlElement("w:tcBorders")
    for edge in ("top", "left", "bottom", "right"):
        element = OxmlElement(f"w:{edge}")
        element.set(qn("w:val"), "single")
        element.set(qn("w:sz"), "6")
        element.set(qn("w:color"), "000000")
        borders.append(element)
    tcPr.append(borders)


def _height_rule(cm_value):
    element = OxmlElement("w:trHeight")
    element.set(qn("w:val"), str(int(cm_value * 567)))
    element.set(qn("w:hRule"), "atLeast")
    return element


def table(doc, headers, rows, widths, *, font=9, header_bold=True, first_col_bold=False, row_height=None, keep_together=True):
    # 版心宽度固定 16.6cm（A4 21cm 减左右各 2.2cm）；按比例归一，避免表格比正文窄 4mm。
    scale = 16.6 / sum(widths)
    widths = [round(width * scale, 2) for width in widths]
    table_obj = doc.add_table(rows=1, cols=len(headers))
    table_obj.style = "Table Grid"
    table_obj.alignment = WD_TABLE_ALIGNMENT.CENTER
    table_obj.autofit = False
    # 固定列宽：不写 tblLayout=fixed 时，Word/LibreOffice 会按内容重新分配，列宽设置失效。
    tblPr = table_obj._tbl.tblPr
    # python-docx 已带 tblW(type=auto)；再 append 会产生重复元素，读取方取第一个 0 宽。
    layout = tblPr.find(qn("w:tblLayout"))
    if layout is None:
        layout = OxmlElement("w:tblLayout")
        tblPr.append(layout)
    layout.set(qn("w:type"), "fixed")
    tblW = tblPr.find(qn("w:tblW"))
    if tblW is None:
        tblW = OxmlElement("w:tblW")
        tblPr.append(tblW)
    tblW.set(qn("w:type"), "dxa")
    tblW.set(qn("w:w"), str(int(sum(widths) * 567)))
    # tblGrid 才是固定布局下列宽的真源；只改 tcW 时 LibreOffice/Word 仍按网格等分。
    for grid_col, width in zip(table_obj._tbl.tblGrid.gridCol_lst, widths):
        grid_col.set(qn("w:w"), str(int(width * 567)))
    header = table_obj.rows[0].cells
    for index, text in enumerate(headers):
        header[index].text = ""
        paragraph = header[index].paragraphs[0]
        paragraph.paragraph_format.space_after = Pt(1)
        set_run(paragraph.add_run(text), size=font, bold=header_bold)
        header[index].width = Cm(widths[index])
    for row in rows:
        cells = table_obj.add_row().cells
        for index, value in enumerate(row):
            cells[index].text = ""
            paragraph = cells[index].paragraphs[0]
            paragraph.paragraph_format.space_after = Pt(1)
            paragraph.paragraph_format.line_spacing = 1.15
            bold = first_col_bold and index == 0
            set_run(paragraph.add_run(str(value)), size=font, bold=bold)
            cells[index].width = Cm(widths[index])
    for index, row in enumerate(table_obj.rows):
        trPr = row._tr.get_or_add_trPr()
        cant = OxmlElement("w:cantSplit")
        trPr.append(cant)
        if index == 0:
            repeat = OxmlElement("w:tblHeader")
            trPr.append(repeat)
        if row_height:
            trPr.append(_height_rule(row_height))
        if keep_together and index < len(table_obj.rows) - 1:
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    paragraph.paragraph_format.keep_with_next = True
        for cell in row.cells:
            _cell_borders(cell)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)
    return table_obj


def case_table(doc, case, number):
    cid, title, req, pri, pre, data, steps, expect, note = case
    heading(doc, f"{cid}  {title}", 3)
    rows = [
        ("需求编号", req),
        ("优先级", pri),
        ("前置条件", pre),
        ("测试数据", data),
        ("操作步骤", "\n".join(f"{i}. {s}" for i, s in enumerate(steps, 1))),
        ("预期结果", "\n".join(f"{i}. {s}" for i, s in enumerate(expect, 1))),
    ]
    if note:
        rows.append(("说明", note))
    caption(doc, f"表 {number}  {cid} 用例规格")
    table(doc, ["字段", "内容"], rows, [3.0, 13.2], font=9, first_col_bold=True)


def field_page_number(paragraph):
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = paragraph.add_run("第 ")
    set_run(run, size=9)
    for kind, text in (("begin", None), (None, "PAGE"), ("end", None)):
        if kind:
            element = OxmlElement("w:fldChar")
            element.set(qn("w:fldCharType"), kind)
        else:
            element = OxmlElement("w:instrText")
            element.set(qn("xml:space"), "preserve")
            element.text = text
        container = OxmlElement("w:r")
        container.append(element)
        paragraph._p.append(container)
    run = paragraph.add_run(" 页")
    set_run(run, size=9)


def toc(doc, pages: dict[str, int] | None, entries_source: list[tuple[int, str]] | None = None):
    """静态目录：条目取自第一遍收集的标题，页码由第二遍渲染结果回填。"""
    source = entries_source if entries_source is not None else HEADINGS
    entries = [(level, text) for level, text in source
               if text not in {"目录"} and not text.startswith("TC-")]
    for level, text in entries:
        paragraph = doc.add_paragraph()
        fmt = paragraph.paragraph_format
        fmt.space_before = Pt(1.5 if level == 1 else 0)
        fmt.space_after = Pt(0)
        fmt.line_spacing = 1.15
        fmt.left_indent = Cm(0 if level == 1 else 0.9)
        fmt.tab_stops.add_tab_stop(Cm(16.2), WD_TAB_ALIGNMENT.RIGHT, WD_TAB_LEADER.DOTS)
        number = str(pages.get(text, 0)) if pages else ""
        set_run(paragraph.add_run(f"{text}\t{number}"), size=10, bold=(level == 1))


def enable_update_fields(doc):
    settings = doc.settings.element
    element = settings.find(qn("w:updateFields"))
    if element is None:
        element = OxmlElement("w:updateFields")
        settings.append(element)
    element.set(qn("w:val"), "true")


# ---------------------------------------------------------------- 文档主体
def build(pages: dict[str, int] | None = None, toc_entries=None, save: bool = True):
    HEADINGS.clear()
    doc = Document()
    # 清掉 python-docx 模板自带的属性，否则文件属性里会出现 “generated by python-docx”。
    props = doc.core_properties
    props.title = "软件测试文档 V1.0"
    props.subject = "基于本地 OCR 的 PDF 文件显示与管理系统"
    props.author = "第 27 组"
    props.last_modified_by = "第 27 组"
    props.comments = ""
    props.keywords = ""
    props.category = "软件工程课程设计"
    props.created = datetime(2026, 11, 27, 9, 0, 0)
    props.modified = datetime(2026, 11, 27, 20, 0, 0)
    props.revision = 1

    section = doc.sections[0]
    section.page_width, section.page_height = Cm(21), Cm(29.7)
    section.left_margin = section.right_margin = Cm(2.2)
    section.top_margin = Cm(2.4)
    section.bottom_margin = Cm(2.2)

    normal = doc.styles["Normal"]
    normal.font.name = LATIN
    normal.font.size = Pt(10.5)
    normal.font.color.rgb = BLACK
    normal.element.rPr.rFonts.set(qn("w:eastAsia"), BODY_FONT_CN)

    field_page_number(section.footer.paragraphs[0])
    enable_update_fields(doc)

    # 封面
    for _ in range(3):
        doc.add_paragraph()
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    set_run(p.add_run("软件测试文档"), size=26, bold=True, cn=HEAD_FONT_CN)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(6)
    set_run(p.add_run("基于本地 OCR 的 PDF 文件显示与管理系统"), size=15, cn=HEAD_FONT_CN)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    set_run(p.add_run("测试计划与测试用例"), size=12)
    for _ in range(4):
        doc.add_paragraph()
    table(doc, ["项目", "内容"], [
        ("课程名称", "软件工程课程设计"),
        ("小组名称", "第 27 组"),
        ("成员", "陈浩然（组长，2024141460570）\n黄俞富（2024141460074）\n岳浩睿（2024141460114）"),
        ("文档版本", "V1.0"),
        ("编写日期", "2026 年 11 月 27 日"),
        ("代码基线", "v2.2.5"),
        ("文档状态", "提交版：测试计划与测试用例，36 条用例接口层全部通过"),
    ], [3.2, 11.0], font=10)
    doc.add_page_break()

    # 修订记录
    heading(doc, "修订记录", 1)
    caption(doc, "表 0-1  修订记录")
    table(doc, ["版本", "日期", "修订人", "修订内容"], [
        ("V1.0", "2026-11-27", "第 27 组",
         "首次发布。依据需求分析、系统设计与代码路由建立测试计划与测试用例，"
         "36 条用例均在本机实测通过。"),
    ], [1.8, 2.6, 2.4, 9.4], font=9)

    # 使用说明
    heading(doc, "文档使用说明", 1)
    body(doc, "本文档用于指导系统测试与答辩现场演示。测试对象为仓库代码基线 v2.2.5，"
              "功能范围以《需求分析文档》V1.1、《系统设计文档》V2.0 与最小必须功能集裁剪说明为准。")
    body(doc, "本轮只纳入能在当前环境稳定复现的行为：用户与权限、文件上传与管理、PDF 阅读、书签与批注、"
              "分享、全文检索与 OCR 任务状态机。校对、表格还原、阅读器高级交互、统计看板、"
              "性能验收与真实识别准确率不在本轮通过条件内，其边界见 2.2。")
    body(doc, "每条用例只给前置条件、数据、步骤与可判定结果，便于逐条执行与复核；"
              "执行记录随交付材料另行留存。")
    doc.add_page_break()

    heading(doc, "目录", 1)
    toc(doc, pages, toc_entries)
    doc.add_page_break()

    # 1 概述
    heading(doc, "1  测试概述", 1)
    heading(doc, "1.1  测试目的", 2)
    body(doc, "验证系统是否按需求与设计提供可用的本地 PDF 管理、阅读与 OCR 任务能力，"
              "重点确认主流程可完成、异常输入可解释、权限边界可阻断、数据状态可恢复，"
              "并为现场验收提供一套逐条可执行、结果可判定的用例。")

    heading(doc, "1.2  被测系统", 2)
    caption(doc, "表 1-1  被测系统与入口")
    table(doc, ["层次", "被测内容", "主要入口"], [
        ("前端展现层", "React 页面：登录注册、上传、文件库、回收站、阅读器、分享管理、游客分享页、检索、账户、管理员用户页",
         "http://127.0.0.1:5173"),
        ("主系统 API", "FastAPI：鉴权、文件、阅读器、分享、检索、OCR 宿主桥接、配额与审计",
         "http://127.0.0.1:8000"),
        ("OCR 服务", "独立可安装模块：任务、按页结果、导出、检索索引",
         "/api/v1/ocr/*"),
        ("数据与存储", "SQLite 开发库或 MySQL 8；本地文件存储；任务状态与审计记录",
         "由 PDF_* 环境变量配置"),
    ], [3.0, 9.6, 3.6], font=9)

    heading(doc, "1.3  引用文件", 2)
    caption(doc, "表 1-2  引用文件")
    table(doc, ["编号", "文件", "版本/位置"], [
        ("R1", "需求分析文档", "V1.1，docs/requirements/"),
        ("R2", "系统设计文档", "V2.0，docs/design/"),
        ("R3", "最小必须功能集实现状态", "2026-11-19，docs/测试审查报告/"),
        ("R4", "功能分层与裁剪建议", "2026-11-19，docs/测试审查报告/"),
        ("R5", "接口契约", "docs/api-contract.yaml"),
        ("R6", "开发基线与验收", "docs/development-baseline.md"),
    ], [1.6, 7.4, 7.2], font=9)

    heading(doc, "1.4  术语与缩写", 2)
    caption(doc, "表 1-3  术语表")
    table(doc, ["术语", "含义"], [
        ("P0 / P1", "P0 为演示前必须完成的主链路用例；P1 为完整性与异常路径用例。"),
        ("mounted", "OCR 模块是否成功挂载到主系统；false 时 /api/v1/ocr/* 路由不存在。"),
        ("settle", "任务进入终态后结算配额，幂等，可重复调用。"),
        ("夹具", "为验证链路而写入的测试数据（如已完成识别的索引），不代表真实识别能力。"),
        ("契约 e2e", "用固定 API fixture 验证页面请求契约，不连真实后端。"),
        ("真实链路 e2e", "浏览器 + 真实 FastAPI + SQLite 的端到端脚本（npm run test:live）。"),
    ], [3.2, 13.0], font=9)

    # 2 范围
    heading(doc, "2  测试范围与基线", 1)
    heading(doc, "2.1  纳入范围", 2)
    for item in [
        "注册、登录、令牌刷新、登出、修改密码与角色边界。",
        "PDF 内容校验、上传、分页与筛选、重命名、分类与标签、软删除、回收站、还原、彻底删除、原文件下载。",
        "在线阅读、翻页、跳页、缩放，书签与批注的增删查。",
        "分享创建、提取码、下载开关、游客只读浏览、撤销。",
        "关键词检索、建议、权限过滤、特殊字符与未就绪降级。",
        "OCR 能力探测、提交、轮询、取消、重试、导出拒绝与结算。",
        "输入校验、越权访问、路径穿越、未登录拦截。",
    ]:
        bullet(doc, item)

    heading(doc, "2.2  不纳入范围", 2)
    body(doc, "以下内容不在本轮测试与验收范围内，不作为通过条件，也不在本文档中给出用例：")
    for item in [
        "结果校对与表格还原（FR-COR、FR-TBL）。",
        "阅读器高级交互：连续滚动、目录大纲、页内高亮、OCR 文本层、双视图、阅读位置记忆。",
        "文件批量、合并、拆分的前端入口与文件版本列表。",
        "统计看板与使用分析（FR-LOG-05）。",
        "性能与容量指标（NFR-PERF 全部）、MySQL 部署与恢复演练。",
        "OCR 真实识别准确率：本轮只判定任务状态机、接口契约与导出前置条件。",
    ]:
        bullet(doc, item)

    heading(doc, "2.3  测试基线", 2)
    caption(doc, "表 2-1  基线事实与复现命令")
    table(doc, ["项目", "结果", "复现方式"], [
        ("后端单元与接口", "136 passed（约 2 分 7 秒）", "pytest backend/tests -q（需装两份 requirements）"),
        ("前端组件单测", "16 passed", "npm test"),
        ("真实链路 e2e", "8 条通过", "SE_PYTHON=<解释器> npm run test:live"),
        ("契约 e2e", "26 条（固定 fixture）", "npm run test:e2e"),
        ("本轮接口用例", "36 / 36 PASS", "scripts/verify_test_cases.py"),
        ("本轮界面用例", "4 / 4 PASS", "frontend/scripts/verify-demo-ui.mjs full|degraded"),
    ], [3.6, 5.4, 7.2], font=9)

    heading(doc, "2.4  需求覆盖矩阵", 2)
    caption(doc, "表 2-2  需求模块与用例对应")
    table(doc, ["需求模块", "需求编号范围", "用例", "本轮状态"], [
        ("用户与权限", "FR-USER-01~07", "TC-AUTH-01~06", "覆盖 01~05；06 由 TC-SEC-03 覆盖；07（账号禁用）无对应用例"),
        ("文件管理", "FR-FILE-01~11", "TC-FILE-01~08", "覆盖 01~06"),
        ("PDF 阅读器", "FR-READ-01~09", "TC-READ-01~03", "覆盖 02/03/07；06 覆盖书签增删查；缩放按设计 50%–300%"),
        ("OCR 识别", "FR-OCR-01~12", "TC-OCR-01~07", "覆盖 02/04/05/06/07/10；真实识别不在本轮判定"),
        ("结果导出", "FR-EXP-01~06", "TC-OCR-06", "覆盖“未就绪拒绝”；成功导出依赖 OCR worker，不在本轮判定"),
        ("全文检索", "FR-SEA-01~07", "TC-SEARCH-01~04", "覆盖 01/07"),
        ("分享与协作", "FR-SHR-01~04", "TC-SHARE-01~04", "覆盖 01/02/04（04 按页面图只读口径）"),
        ("配额、日志与统计", "FR-LOG-01~06", "TC-OCR-07、TC-SEC-03", "覆盖 02/04/06；01/03/05 不在本轮范围"),
        ("安全与可靠性", "NFR-SEC-01~08", "TC-SEC-01~04、TC-FILE-08", "覆盖 01/02/03/05"),
    ], [3.4, 4.2, 4.2, 4.4], font=9)

    # 3 策略与环境
    heading(doc, "3  测试策略与环境", 1)
    heading(doc, "3.1  测试层次", 2)
    caption(doc, "表 3-1  测试层次")
    table(doc, ["层次", "目标", "执行方式", "输出"], [
        ("单元与接口", "规则、状态转换、异常码、权限函数", "pytest backend/tests", "测试日志"),
        ("前端组件", "表单、列表、请求重试与错误态", "npm test", "TAP 输出"),
        ("契约端到端", "页面请求是否符合接口契约", "npm run test:e2e", "页面断言"),
        ("真实链路", "浏览器 + FastAPI + SQLite + 文件存储", "npm run test:live", "真实请求与落库"),
        ("现场验收", "按用例编号顺序复现核心场景", "浏览器 + 本文用例", "无阻塞缺陷"),
    ], [2.8, 6.0, 4.4, 3.0], font=9)

    heading(doc, "3.2  环境与依赖", 2)
    body(doc, "主系统与 OCR 服务共用同一数据库、同一存储目录与同一把 JWT 密钥；OCR 的 OCR_* 变量由主系统"
              "在启动时自动派生，不需要手工设置，手工设置反而与 PDF_STORAGE_DIR 冲突。")
    caption(doc, "表 3-2  环境与依赖")
    table(doc, ["项目", "要求", "说明"], [
        ("操作系统", "Windows 10/11", "浏览器 Chrome/Edge 100 以上"),
        ("Python", "3.12", "主系统与 OCR 服务同版本"),
        ("主系统依赖", "pip install -r pdf_system/requirements.txt", "含 pytest、httpx、pypdf"),
        ("OCR 依赖", "pip install -r pdf_ocr_module/ocr_service/requirements.txt",
         "缺 opencv 时 backend/tests 直接收集失败，这一步不能省"),
        ("前端依赖", "npm ci（Node 20/22）", "真实链路脚本需 SE_PYTHON 指向装好依赖的解释器"),
        ("数据库", "SQLite（开发）或 MySQL 8", "初始化：python -m backend.scripts.init_db"),
        ("存储", "PDF_STORAGE_DIR 目录", "OCR 与主系统必须同目录"),
    ], [3.0, 6.8, 6.4], font=9)

    heading(doc, "3.3  数据与账号准备", 2)
    body(doc, "以下命令一次产出演示所需的账号与样本，避免现场手工造数据：")
    body(doc, "python -m backend.scripts.prepare_demo --seed --seed-index --api http://127.0.0.1:8000", indent=False)
    body(doc, "需要演示“OCR 未挂载”分支时，用同一数据库再起一个实例："
              "PDF_OCR_ENABLED=false uvicorn backend.main:create_app --factory --port 8001，"
              "前端用 SE_API_TARGET=http://127.0.0.1:8001 另起一个 Vite（如 5174），"
              "打开阅读器即可看到提示与禁用态。")
    caption(doc, "表 3-3  样本与账号")
    table(doc, ["产物", "内容", "用途"], [
        ("D-01", "2 页正常 PDF", "上传、阅读、标注、下载、OCR"),
        ("D-02", "5 页 PDF", "多页翻页、指定页 OCR"),
        ("D-03", "改扩展名的普通文本", "内容校验（invalid_image）"),
        ("D-04", "截断损坏 PDF", "内容校验（invalid_or_encrypted_pdf）"),
        ("D-05", "AES 加密 PDF（口令 demo123）", "加密文件拒绝"),
        ("document-01.pdf … document-14.pdf", "14 份单页 PDF", "分页演示（每页 12 条）"),
        ("demo-user / demo-viewer / demo-admin", "口令 Demo12345", "角色与越权演示"),
        ("检索夹具", "--seed-index 写入的已完成识别结果", "验证检索与片段，不证明识别准确率"),
    ], [4.2, 6.6, 5.4], font=9)

    heading(doc, "3.4  判定口径", 2)
    body(doc, "状态码必须按表 3-4 判定，不接受“以实现为准”。实现与下表不一致时按缺陷记录，不修改预期。")
    caption(doc, "表 3-4  状态码约定")
    table(doc, ["状态码", "语义", "典型场景"], [
        ("200", "成功", "查询、更新、撤销后的读取"),
        ("201", "已创建", "注册、上传、书签、批注、分享等创建类接口"),
        ("202", "已受理", "OCR 任务提交、重试"),
        ("204", "无内容", "登出、删除书签/批注、撤销分享、彻底删除"),
        ("401", "未认证或凭据错误", "缺令牌、令牌失效/被吊销、登录口令错误"),
        ("403", "已认证但动作不允许", "viewer 写操作、原密码错误、非管理员访问管理接口"),
        ("404", "不存在或无权访问", "越权、分享失效、提取码错误"),
        ("409", "状态冲突", "重复邮箱、活动任务重复提交、任务已终态、结果未就绪"),
        ("422", "请求体或参数不合法", "邮箱格式、口令过短、页码越界、关键词超长"),
        ("429", "限流或配额不足", "分享访问过频、月度识别页数超额"),
    ], [2.2, 5.0, 9.0], font=9)

    # 4 计划
    heading(doc, "4  测试计划", 1)
    heading(doc, "4.1  阶段安排", 2)
    caption(doc, "表 4-1  阶段与准入准出")
    table(doc, ["阶段", "任务", "进入条件", "退出条件"], [
        ("准备", "核对基线、装两份依赖、初始化库、执行 prepare_demo", "工作区版本已确认",
         "/health 返回 status=ok"),
        ("冒烟", "注册/登录、上传、列表、阅读、下载、退出", "服务与样本就绪", "主链路无阻塞缺陷"),
        ("功能", "执行 TC-AUTH 至 TC-SEC 全部用例", "冒烟通过", "每条用例有明确结果"),
        ("安全与异常", "越权、非法文件、超长参数、注入、未登录", "功能数据就绪", "无高危安全缺陷"),
        ("现场验收", "按用例编号顺序复现", "缺陷已分级", "演示路径可重复"),
    ], [2.4, 6.8, 3.6, 3.4], font=9)

    heading(doc, "4.2  人员分工", 2)
    caption(doc, "表 4-2  分工")
    table(doc, ["成员", "主测模块", "现场职责"], [
        ("陈浩然（组长）", "用户与权限、分享、审计接口", "账号与权限数据，演示登录/分享/管理员边界，汇总缺陷"),
        ("岳浩睿", "文件管理、阅读器", "PDF 样本，演示上传、列表、管理、阅读、下载与标注"),
        ("黄俞富", "OCR、导出、检索", "worker 与索引状态，演示任务、结果、导出与检索"),
    ], [3.4, 5.0, 7.8], font=9)

    heading(doc, "4.3  风险与应对", 2)
    caption(doc, "表 4-3  风险")
    table(doc, ["风险", "影响", "应对"], [
        ("OCR worker 与权重未启动", "任务停在 queued，无法验证成功页",
         "先演示能力探测与状态机；真实识别记 N/A，不宣称通过"),
        ("viewer/admin 无接口创建路径", "角色用例无法执行", "统一用 prepare_demo 建号，禁止现场手改库"),
        ("只装一份 requirements", "pytest 收集阶段即失败", "按表 3-2 装两份依赖后再跑"),
        ("数据库残留账号或文件", "重复注册、数据污染", "每次演示用唯一邮箱；必要时用独立库"),
        ("端口被占用", "请求打到旧进程", "启动前检查 8000/5173，重新 /health"),
        ("浏览器缓存令牌", "登出后仍显示旧状态", "无痕窗口或清 localStorage"),
    ], [4.4, 5.4, 6.4], font=9)

    heading(doc, "4.4  通过准则", 2)
    body(doc, "对应 GB/T 9386 第 4 章“测试计划”的通过/失败准则，判定以下六条同时成立才记为通过：")
    for item in [
        "全部 P0 用例通过；P1 用例通过率不低于 90%，未通过项须登记缺陷编号（BUG-模块-序号）并附期望与实际。",
        "环境条件项（依赖 worker、权重或外部注入）记 N/A 并写明原因，不参与通过率计算。",
        "不存在 S1 阻塞缺陷；S2 缺陷须修复并回归，或在现场明确展示限制。",
        "权限、路径穿越、内容校验、令牌清理与输出转义类用例，不得以“页面显示正常”代替证据。",
        "OCR 只有在 worker、模型与同库同存储配置均满足时，才判定真实识别通过；否则只判定状态机与接口行为。",
        "所有用例的执行结果与执行人随交付材料一并留存，本文档只负责给出可判定预期。",
    ]:
        bullet(doc, item)

    # 5 用例
    heading(doc, "5  测试用例", 1)
    body(doc, "共 36 条。每条用例只验证一个主要行为，预期结果给到可判定的状态码或字段；"
              "环境条件不满足的条目已在预期中写明“属环境条件项”，不以页面正常代替证据。")
    number = 1
    for section_no, section_title, cases in CASES:
        heading(doc, f"{section_no}  {section_title}", 2)
        for case in cases:
            case_table(doc, case, f"5-{number}")
            number += 1

    # 附录
    heading(doc, "附录 A  样本与账号清单", 1)
    caption(doc, "表 A-1  样本清单")
    table(doc, ["编号", "文件", "页数", "用途"], [
        ("D-01", "D-01-两页正常.pdf", "2", "上传、阅读、标注、下载、OCR"),
        ("D-02", "D-02-多页.pdf", "5", "多页翻页、指定页 OCR"),
        ("D-03", "D-03-改扩展名文本.pdf", "—", "内容校验（invalid_image）"),
        ("D-04", "D-04-损坏.pdf", "—", "内容校验（invalid_or_encrypted_pdf）"),
        ("D-05", "D-05-加密.pdf", "2", "加密拒绝（口令 demo123）"),
        ("D-06", "document-01.pdf … document-14.pdf", "各 1", "分页与筛选"),
        ("D-07", "检索夹具", "—", "检索、片段、转义"),
        ("D-08", "demo-user / demo-viewer / demo-admin", "—", "角色与越权"),
    ], [1.6, 6.4, 1.8, 6.6], font=9)

    if not save:
        return
    OUT.parent.mkdir(parents=True, exist_ok=True)
    doc.save(OUT)
    print(f"written: {OUT}")


if __name__ == "__main__":
    import json
    import sys

    pages = None
    if "--toc" in sys.argv:
        pages = json.loads(Path(sys.argv[sys.argv.index("--toc") + 1]).read_text(encoding="utf-8"))
    if "--out" in sys.argv:
        OUT = Path(sys.argv[sys.argv.index("--out") + 1])
    # 第一遍只收集标题，第二遍才写正文与目录。
    build(save=False)
    entries = list(HEADINGS)
    build(pages, entries)
