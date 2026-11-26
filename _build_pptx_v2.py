
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE, MSO_CONNECTOR
from pathlib import Path

root=Path(r"C:\Users\Administrator\Desktop\se_course_design")
out=root/"现代软件工程课程设计_03_设计方案汇报.pptx"
img=root/"ppt_img"
prs=Presentation(); prs.slide_width=Inches(13.333); prs.slide_height=Inches(7.5)
blank=prs.slide_layouts[6]
NAVY=RGBColor(24,48,84); BLUE=RGBColor(47,102,164); PURPLE=RGBColor(103,74,145); TEAL=RGBColor(38,128,125); TEXT=RGBColor(37,47,62); MUTED=RGBColor(103,113,127); LIGHT=RGBColor(244,247,251); BORDER=RGBColor(211,220,232); WHITE=RGBColor(255,255,255); PALEBLUE=RGBColor(233,241,250); PALEPURPLE=RGBColor(241,235,248)

def txt(s,x,y,w,h,t,size=18,c=TEXT,b=False,align=PP_ALIGN.LEFT):
    sh=s.shapes.add_textbox(Inches(x),Inches(y),Inches(w),Inches(h)); tf=sh.text_frame; tf.word_wrap=True
    p=tf.paragraphs[0]; p.alignment=align; r=p.add_run(); r.text=t; r.font.name='Microsoft YaHei'; r.font.size=Pt(size); r.font.color.rgb=c; r.font.bold=b
    return sh
def header(s,title,sub,num):
    s.background.fill.solid(); s.background.fill.fore_color.rgb=WHITE
    top=s.shapes.add_shape(MSO_SHAPE.RECTANGLE,0,0,prs.slide_width,Inches(.14)); top.fill.solid(); top.fill.fore_color.rgb=PURPLE; top.line.fill.background()
    txt(s,.65,.4,12,.5,title,27,NAVY,True)
    txt(s,.67,.95,11.7,.3,sub,11,MUTED)
    txt(s,12.2,7.08,.5,.2,str(num),9,MUTED,False,PP_ALIGN.RIGHT)
def box(s,x,y,w,h,title,body,color=BLUE,fill=LIGHT,ts=15,bs=12):
    sh=s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE,Inches(x),Inches(y),Inches(w),Inches(h)); sh.fill.solid(); sh.fill.fore_color.rgb=fill; sh.line.color.rgb=BORDER
    stripe=s.shapes.add_shape(MSO_SHAPE.RECTANGLE,Inches(x),Inches(y),Inches(.07),Inches(h)); stripe.fill.solid(); stripe.fill.fore_color.rgb=color; stripe.line.fill.background()
    txt(s,x+.18,y+.12,w-.35,.28,title,ts,NAVY,True)
    txt(s,x+.18,y+.5,w-.35,h-.62,body,bs,TEXT)
def bullets(s,x,y,w,h,items,size=16):
    sh=s.shapes.add_textbox(Inches(x),Inches(y),Inches(w),Inches(h)); tf=sh.text_frame; tf.word_wrap=True
    for i,it in enumerate(items):
        p=tf.paragraphs[0] if i==0 else tf.add_paragraph(); p.space_after=Pt(8)
        r=p.add_run(); r.text="• "+it; r.font.name='Microsoft YaHei'; r.font.size=Pt(size); r.font.color.rgb=TEXT
def line(s,x1,y1,x2,y2,c=MUTED,width=1.5):
    l=s.shapes.add_connector(MSO_CONNECTOR.STRAIGHT,Inches(x1),Inches(y1),Inches(x2),Inches(y2)); l.line.color.rgb=c; l.line.width=Pt(width)
def pic(s,name,x,y,w,h):
    s.shapes.add_picture(str(img/name),Inches(x),Inches(y),width=Inches(w),height=Inches(h))

# Cover
s=prs.slides.add_slide(blank); s.background.fill.solid(); s.background.fill.fore_color.rgb=WHITE
bar=s.shapes.add_shape(MSO_SHAPE.RECTANGLE,0,0,prs.slide_width,Inches(.18)); bar.fill.solid(); bar.fill.fore_color.rgb=PURPLE; bar.line.fill.background()
txt(s,1,1.35,11.3,.7,"现代软件工程课程设计_03",31,NAVY,True,PP_ALIGN.CENTER)
txt(s,1.1,2.3,11.1,.65,"基于本地 OCR 的 PDF 文件显示与管理系统",26,BLUE,True,PP_ALIGN.CENTER)
txt(s,1.1,3.25,11.1,.4,"项目设计方案汇报",18,MUTED,False,PP_ALIGN.CENTER)
txt(s,1.1,5.55,11.1,.3,"汇报人  陈浩然",15,TEXT,False,PP_ALIGN.CENTER)
txt(s,1.1,6.4,11.1,.25,"本地部署 · 分层架构 · SQLite 数据模型 · 异步 OCR",12,MUTED,False,PP_ALIGN.CENTER)

# Problem
s=prs.slides.add_slide(blank); header(s,"1  为什么做这个系统","先说明痛点，再给出设计边界",2)
box(s,.8,1.45,3.7,2.0,"输入问题","扫描件和图片型 PDF 是“图片壳”，文件能保存，却难以复制、检索和复用。",PURPLE,PALEPURPLE,16,15)
box(s,4.8,1.45,3.7,2.0,"约束条件","课程周期有限，系统需要本机运行，文件和 OCR 结果不能依赖云端服务。",BLUE,PALEBLUE,16,15)
box(s,8.8,1.45,3.7,2.0,"设计目标","用最小必须功能集完成上传、下载、显示、管理、OCR 识别和结果导出闭环。",TEAL,RGBColor(232,246,245),16,15)
txt(s,.85,4.15,11.5,.4,"范围内功能",18,NAVY,True)
bullets(s,1.0,4.65,5.5,1.55,["用户登录与资源权限","PDF / PNG / JPEG 文件管理","在线阅读、分页、跳页、缩放","OCR 任务、按页结果和导出"],16)
txt(s,7.0,4.15,5.2,.4,"明确裁剪",18,NAVY,True)
bullets(s,7.1,4.65,5.0,1.55,["连续阅读、目录侧栏","表格还原、校对、文本层叠加","批量处理、合并拆分、统计看板"],16)

# Architecture
s=prs.slides.add_slide(blank); header(s,"2  总体架构","四层职责清楚，所有组件在本机协作",3)
# layers
box(s,.8,1.45,11.8,.85,"展现层","React + Vite：登录、文件库、阅读器、OCR 面板、导出操作",BLUE,PALEBLUE,16,13)
box(s,.8,2.55,11.8,.85,"接口层","FastAPI：JWT 鉴权、文件 API、阅读器 API、OCR 任务 API、搜索与导出 API",PURPLE,PALEPURPLE,16,13)
box(s,.8,3.65,5.75,1.05,"业务服务层","用户与权限 / 文件管理 / 阅读器 / OCR 生命周期 / 全文检索",TEAL,RGBColor(232,246,245),16,13)
box(s,6.85,3.65,5.75,1.05,"任务执行层","SQLite 队列表 + 独立 OCR worker，逐页读取、识别、回写",PURPLE,PALEPURPLE,16,13)
box(s,.8,5.05,11.8,1.05,"数据与存储层","SQLite：元数据、任务、页结果、全文索引　　本地文件目录：原文件与模型权重",BLUE,PALEBLUE,16,13)
for y in [2.3,3.4,4.75,5.95]: line(s,6.7,y,6.7,y+.22)
txt(s,1,6.45,11.2,.35,"核心原则  页面请求与 OCR 执行解耦，文件与识别结果始终留在本机。",15,NAVY,True,PP_ALIGN.CENTER)

# Database
s=prs.slides.add_slide(blank); header(s,"3  数据库设计","主系统表管理资源，OCR 表管理识别过程，文件编号贯穿两侧",4)
# entities
box(s,.65,1.45,2.15,1.0,"users","账号、角色、禁用状态",PURPLE,PALEPURPLE,15,12)
box(s,3.15,1.45,2.25,1.0,"files","文件名、类型、页数、存储键",BLUE,PALEBLUE,15,12)
box(s,5.8,1.45,2.25,1.0,"ocr_jobs","任务状态、代次、尝试次数",PURPLE,PALEPURPLE,15,12)
box(s,8.45,1.45,2.25,1.0,"ocr_pages","页状态、文本、识别框",TEAL,RGBColor(232,246,245),15,12)
box(s,11.1,1.45,1.55,1.0,"text_index","全文检索",BLUE,PALEBLUE,14,11)
line(s,2.8,1.95,3.15,1.95); line(s,5.4,1.95,5.8,1.95); line(s,8.05,1.95,8.45,1.95); line(s,10.7,1.95,11.1,1.95)
txt(s,1.0,2.75,11.4,.35,"关键关系",18,NAVY,True)
box(s,.8,3.25,3.6,1.55,"用户拥有文件","users 1 —— N files\n权限查询始终按 owner_id 过滤",PURPLE,PALEPURPLE,16,14)
box(s,4.85,3.25,3.6,1.55,"文件产生任务","files 1 —— N ocr_jobs\n同一文件同时只允许一个活动任务",BLUE,PALEBLUE,16,14)
box(s,8.9,3.25,3.6,1.55,"任务产生页结果","ocr_jobs 1 —— N ocr_pages\n页结果与全文索引同一事务写入",TEAL,RGBColor(232,246,245),16,14)
txt(s,1.0,5.35,11.2,.75,"数据一致性设计  files.id 同时作为 OCR 镜像关联键，generation 区分新旧识别结果，deleted_at 支持回收站而不立即破坏关联数据。",15,TEXT,False,PP_ALIGN.CENTER)

# Workflow
s=prs.slides.add_slide(blank); header(s,"4  上传到 OCR 的业务流程","把用户操作、后端校验、队列和结果回写串成一条链",5)
steps=[("1 上传","浏览器提交文件",BLUE),("2 校验","魔数、大小、页数、类型",PURPLE),("3 入队","写入 ocr_jobs",TEAL),("4 执行","worker 逐页识别",PURPLE),("5 回写","ocr_pages + text_index",BLUE),("6 展示","轮询进度、按页查看、导出",TEAL)]
x=.55
for i,(t,b,c) in enumerate(steps):
    box(s,x,2.0,1.85,1.55,t,b,c,PALEBLUE if i%2==0 else PALEPURPLE,15,11)
    if i<5: line(s,x+1.85,2.78,x+2.12,2.78)
    x+=2.12
txt(s,.9,4.4,11.5,.35,"失败处理",18,NAVY,True)
bullets(s,1.0,4.9,5.5,1.25,["取消任务释放队列状态","失败任务支持重试","成功页不重复计算"],16)
txt(s,7.0,4.4,5.2,.35,"为什么要异步",18,NAVY,True)
bullets(s,7.1,4.9,5.0,1.25,["OCR 不阻塞页面请求","进度可被轮询观察","代次防止旧结果覆盖新结果"],16)

# Modules/team
s=prs.slides.add_slide(blank); header(s,"5  模块边界与小组分工","一人主责一个模块，跨模块依靠共享契约协作",6)
box(s,.8,1.45,3.75,1.35,"陈浩然","用户与权限、分享、系统整合",PURPLE,PALEPURPLE,16,15)
box(s,4.8,1.45,3.75,1.35,"岳浩睿","文件管理、上传校验、PDF / 图片阅读器",BLUE,PALEBLUE,16,15)
box(s,8.8,1.45,3.75,1.35,"黄俞富","OCR 引擎适配、任务生命周期、全文检索",TEAL,RGBColor(232,246,245),16,15)
txt(s,.9,3.35,11.5,.4,"共享契约",18,NAVY,True)
box(s,.8,3.9,5.7,1.55,"接口契约","统一 HTTP 请求出口\n资源权限统一返回\n下载与导出统一走鉴权接口",BLUE,PALEBLUE,16,14)
box(s,6.8,3.9,5.7,1.55,"数据契约","files.id、storage_key、media_type、page_count\nOCR generation、页结果状态、全文索引来源",PURPLE,PALEPURPLE,16,14)
txt(s,1.0,6.15,11.2,.4,"模块化的目的  后续可以替换 OCR 引擎或数据库，而不改变用户的主流程。",15,NAVY,True,PP_ALIGN.CENTER)

# File management demo
s=prs.slides.add_slide(blank); header(s,"6  文件管理与在线显示","方案落到页面上，文件库是统一入口",7)
pic(s,"Snipaste_2026-11-26_10-22-06.png",.7,1.35,6.3,4.95)
pic(s,"Snipaste_2026-11-26_10-57-58.png",7.35,1.35,5.25,4.95)
txt(s,.85,6.45,6.1,.3,"横向文件列表：管理入口、类型和 OCR 状态",13,MUTED)
txt(s,7.45,6.45,5.0,.3,"图片阅读器：统一显示与 OCR 结果",13,MUTED)

# OCR demo
s=prs.slides.add_slide(blank); header(s,"7  OCR 任务与结果导出","展示程序只是验证设计闭环，重点仍是任务状态和数据回写",8)
pic(s,"Snipaste_2026-11-26_10-32-14.png",.7,1.35,5.8,4.9)
pic(s,"Snipaste_2026-11-26_10-59-12.png",6.9,1.35,5.7,4.9)
txt(s,.85,6.4,5.6,.35,"排队状态：任务尚未执行时的可解释反馈",13,MUTED)
txt(s,7.05,6.4,5.3,.35,"导出结果：TXT 文件可在外部编辑器打开",13,MUTED)

# Summary
s=prs.slides.add_slide(blank); header(s,"8  汇报收束","用三句话总结系统设计",9)
box(s,.8,1.5,3.75,2.0,"架构","前端负责交互，FastAPI 负责业务，SQLite 和本地目录负责数据，OCR worker 负责耗时识别。",BLUE,PALEBLUE,17,15)
box(s,4.8,1.5,3.75,2.0,"数据","users、files、ocr_jobs、ocr_pages 和 text_index 形成从资源到结果的可追踪链路。",PURPLE,PALEPURPLE,17,15)
box(s,8.8,1.5,3.75,2.0,"演示","文件库 → 阅读器 → 新建 OCR 任务 → 进度 → 结果 → TXT 导出，五步完成短演示。",TEAL,RGBColor(232,246,245),17,15)
txt(s,1.1,4.45,11,.7,"核心结论  本项目用最小功能集完成了一个可在本机运行、可解释、可扩展的文档管理与 OCR 方案。",23,NAVY,True,PP_ALIGN.CENTER)
txt(s,1.1,5.75,11,.4,"谢谢各位老师",18,MUTED,False,PP_ALIGN.CENTER)

prs.save(out); print(out)

