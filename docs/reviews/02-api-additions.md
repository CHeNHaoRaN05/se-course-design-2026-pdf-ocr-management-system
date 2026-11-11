# 02 线审查修复：增量 API 契约（本地待评审）

基线：2026-11-11 fetch 的 origin/main 8cf647f、PR #9 head 1c9971d。
本次按用户要求修复测试审查问题。既有 C1–C5 函数签名与模型结构保持兼容；新增接口由对应维护者 review 后再合并，不自动发布或合并 PR。

- GET /api/v1/files/query：q/folder/tag/media_type/date_from/date_to/status/sort/limit/offset。响应 {items,total,status_available}。日期 UTC，sort=newest/name/size/pages/status，稳定 id 次级排序。OCR 不可用时返回 status_available=false 并忽略状态过滤，不返回假空集。
- GET /api/v1/files/trash：仅软删除文件，数组响应，包含真实 deleted_at；静态路由先于 /{file_id}。
- POST /api/v1/files/bulk：{file_ids(1..100,唯一),action:move|tag|delete,folder?,tags?,append_tags?}。先校验全部归属/参数，每项一个事务，返回 {items:[{id,name,ok,message?}],succeeded,failed}。部分失败明确报告，不宣称全批原子。
- POST /api/v1/files/merge：{file_ids(2..100,唯一),name}，按 ID 顺序生成新 PDF，服务端校验源文件内容和总页数，响应 FileOut。
- POST /api/v1/files/{id}/split：{name,groups?:正整数页码二维数组,every?:正整数}，二者择一，不可越界或重叠；响应 FileOut[]。所有新文件一个数据库事务，异常回滚记录并清理新文件；原件不变。
- GET /api/v1/auth/users：require_admin，limit/offset，UserOut[]。
- GET /api/v1/audit：require_admin，actor_id/action/date_from/date_to/limit/offset；白名单字段，不返回 detail 正文。
- POST /api/v1/share：新增 expires_in_days=1|7|30，服务端 now() 计算（缺省7天）；兼容 expires_at 输入但限制未来30天以内，二者不能并传。提取码仅可见 ASCII 字母数字 1..32 字符；ShareOut 新增 expired，由服务端判断。
- PATCH /api/v1/auth/users/{id}/role：拒绝当前管理员自降级；管理员权限保持在服务端校验。
- GET /api/v1/search：增加 media_type=application/pdf|image/png|image/jpeg（可省略）；历史前端兼容旧格式。
- 所有新增 offset 上限1,000,000；原有文件、搜索 offset 也加上限，避免数据库整数溢出。

不在本次补齐：阅读器高级功能、OCR 引擎实现、生产 MySQL/模型验收、空目录模型、存储配额管理、定时保留策略、安全只读页面渲染。详见逐项结论。
