# 02 线复测报告处理记录（2026-11-13）

输入：用户提供的 `验收结果/02线_复测报告.md`，原报告不改写。

## 基线与证据来源

- 本轮实际fetch：main仍为`8cf647f`，远端02分支及PR #9 head均为`613be22`。`613be22`已于前次操作推送，不再称其“未推送”。本记录描述的是该提交之后的新修复。
- 用户复测报告记录：此前GitHub CI在2026-11-11 08:13:54 UTC成功，PR #9当时Open、0 review。本轮GitHub REST请求仍限流，无法独立刷新review/CI详情；不将这份历史报告当成实时API响应。
- 本轮修复环境是macOS/Apple Silicon；复测者使用的win32是另一环境。Windows验证由CI矩阵执行，不混淆机器与时间。
- 不代替01/03线审批，不合并PR。跨线增量继续需要维护者评审。

## 逐项处理

| 编号 | 状态 | 修复或判读 |
|---|---|---|
| B1 | 外部评审待完成 | 用户授权本地修复不代表维护者review。未强行恢复已有功能或伪造批准，保留逐项diff和归属说明。 |
| S1 | 传输分类与恢复已修；原偶发根因未据日志定性 | fetch与body读取取消保留AbortError/TimeoutError；连接中断不武断等同“断网”。仅幂等元数据PATCH对连接失败/408/502/503/504最多3次重试，4xx/500和非幂等POST不重试。上传传signal、重试复用fileId；Vite预扫描依赖避免临时扫描触发页面reload。故障注入验证一次连接重置后自动成功且只上传一次；独立真实流程重复运行另见验证记录。 |
| S2 | 已修复测试缺口 | `npm run test:e2e`包含contract与real-api两项目。real-api没有page.route/fulfill，真实FastAPI+SQLite验证total、并发、PDF内容、版本来源、bulk、权限和分页。contract中未知API即失败，测试Vite拒绝未拦截API，防止静默穿透代理；不把故障注入测试称真实联调。 |
| S3 | 已修复并明确状态码 | 预检只校验归属/存在；本人软删文件进入逐项错误，其他有效项继续。他人/不存在ID仍全批404不修改，避免资源泄露。全部成功200、混合207、全部操作失败409，均带items/succeeded/failed；UI能展示409里的逐项失败。 |
| S4 | 已修复 | 旧files的q/folder最长255、tag64；query同样有上限；前端文件名搜索maxlength255，超长请求422而非SQLite异常。 |
| S5 | 已修复SQLite并发 | 上传命名改用User行的真实SQL UPDATE获取SQLite写锁/MySQL行锁，持有到提交；SQLite不再依赖无效FOR UPDATE。四线程真实上传返回四个不同名称；重命名/还原复用命名规则。未增加模型唯一约束；超出数据库锁等待上限仍应报错而非无界重试。 |
| S6 | 配置与证据已完善，部分原判断不成立 | 旧`--with-deps`不是Windows必然无效的证据，且用户报告已给出旧CI成功。本轮显式区分Linux/Windows安装命令，配置HTML与JSON reporter，上传实际存在目录；同平台跑本轮纯后端回归。不是宣称整个后端126项在Windows上执行。 |
| G1 | 已修复 | suggest对trim后空串返回422。 |
| G2 | 已修复 | bulk move空白folder拒绝，前端空白也拒绝；显式/才表示根目录。 |
| G3 | 已修复 | 仅未删除文件占名；还原冲突分配新序号，避免旧文件还原产生重名。 |
| G4 | 已修复输入歧义 | 绝对expires_at必须有Z或偏移，naive拒绝；aware归一UTC。相对天数仍是推荐入口，服务端决定到期时间。原UTC存储策略不改变。 |
| G5 | 已补来源与版本，完整历史仍待办 | 合并/拆分version=max(source.version)+1；replaced_from记录第一源，审计source_file_ids记录全部源，响应和详情显示来源。未把一个来源字段冒充完整版本历史、回滚或分支树。 |
| G6 | 已修复页面拉满 | 三接口增加envelope=true返回items/total/limit/offset，旧数组客户端兼容；前端仅拉当前页并服务端搜索，审计不再以第21项猜hasMore。其余兼容数组读取遇任何重复记录立即终止。稳定offset排序不是历史快照，翻页期间数据改变应刷新，本轮不声称实现快照游标。 |
| G7 | 已缩短锁范围 | PDFIUM_LOCK仅保护每次PDFium读取/生成，service.upload写盘/SQL/镜像不在该锁内；测试在持久化入口断言未持锁。单个PDF操作仍需锁，/content原本不经过PDFIUM_LOCK，不能称其必然被该锁阻塞。 |
| G8 | 已修复 | 后端返回effective_sort；前端不可用时清状态并将状态排序恢复newest，禁用状态选项。提示只说明能力不可用及实际处理，不再无条件称“已取消状态筛选”。真实未挂载API测试覆盖。 |
| G9 | 客户端与访问路径已修，后台账务仍待办 | 手动创建/校对/取消/导出/重试传AbortSignal，卸载不继续UI副作用；终态结算失败也有限重试。viewer可结算自己终态任务，不能指定页数或他人资源；当前任务settle端点按Job数据库写锁串行，四并发只结算一次。取消浏览器请求不撤销已提交任务；持久化任务可重入查询。无人访问自动结算、跨月账务、同ID重试是独立C3整体设计，未声称已解决。 |
| G10 | 已修复 | 契约由真实装配app完整生成，59路径/68操作；query/trash/users/audit/bulk响应具模型，Merge最少2项和uniqueItems，offset上限、ShareOut、admin权限扩展完整。CI运行生成一致性检查。`type:integer`配`minimum:1.0`在JSON Schema中并不允许小数，原数字写法不是有效缺陷。 |
| G11 | 已修复时点混淆 | 历史记录加“已推送/旧CI成功”的更新说明，保留原始时点证据；当前记录区分macOS修复环境、复测者win32、旧提交与新修复。受限流影响，不伪造最新PR/CI状态。 |
| G12 | 已修复 | frontend到仓库docs为../../；批量检查新增文档的相对链接。 |
| G13 | 已修复直接依赖 | esbuild@0.21.5显式devDependency并更新lock，测试不依赖传递提升。`npm ci --omit=dev`本就不是运行开发测试的安装方式，不承诺其能运行单测。 |
| T1 | 已修复缺口并纠正描述 | JSON/body/blob/publicFile以及OCR导出均支持signal；常见Pydantic错误中文映射。allFiles原本已有signal，本轮继续保留；取消与解析错误独立分类。 |
| T2 | 已修复 | sessionStorage轮询改为事件、storage与BroadcastChannel通知，localStorage不可用也能退出；401视为已失效，500与连接/超时分别提示。旧注销响应仅更新提示，不会清除重新登录的新会话。 |
| T3 | 已修复 | 前后端规范化统一移除Unicode C类、取basename并修剪stem空格；重命名入口用同一规范化，服务端亦去重。 |
| T4 | 已修复 | 文件变更有真实监听者与BroadcastChannel，另一已打开文件库刷新；真实双页浏览器测试覆盖。 |
| T5 | 已修复计数/时刻并明确限制 | 分享次数SQL原子递增，到期统一<=；成功/拒绝写审计，不记录token/code；加单进程限速（30次/分钟/IP），多worker/多机需网关或共享限速器。审计页面标本地时区、CSV列头标UTC原值，8小时时差不是内容篡改。 |

## 未实现的独立需求

维护者评审/合并与部署、C3整套账务与后台终态结算、完整文件版本历史、阅读器高级功能、禁止下载安全渲染、配额管理写接口/存储上限、日趋势/平均耗时、独立分类树/空目录/标签颜色、回收站与审计保留作业、MySQL生产验收、Paddle模型及200页准确率、生产部署演练。

这些项目在报告中本就作为“待完成”，本轮没有通过假数据、前端隐藏或本地测试把它们销项。

## 验证命令

```bash
cd pdf_system
python -m pytest backend/tests ../pdf_ocr_module/ocr_service/tests -q
python -m backend.scripts.export_contract --check
cd frontend
npm test
npm run build
npm run test:e2e
npm run test:live
```

真实测试与故障注入分开报告；具体数量和复跑结果见 `pdf_system/frontend/docs/VALIDATION.md` 最新章节。
