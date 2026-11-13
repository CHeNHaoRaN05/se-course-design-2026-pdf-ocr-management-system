# 2026-11-13 复测修复契约（本地增量）

基线：main 8cf647f、远端02分支/PR head 613be22。前次提交已推送；本轮尚未推送。

- bulk：归属检查与文件可操作状态分离。他人/不存在ID仍全批404不写入；本人已软删ID作为逐项失败，不阻止有效ID。全部成功200，混合207，全部操作失败409（同一items/succeeded/failed结构）。move空白folder拒绝，根目录须显式传/。
- 文件名：前后端统一移除Unicode C类字符、目录分隔与边缘空白、保留扩展名。命名覆盖上传/重命名/还原；仅活动文件占名，还原冲突自动加序号。SQLite使用真实数据库写锁（不是被忽略的FOR UPDATE）锁住名字分配直到提交。
- 旧files的q/folder最长255、tag最长64；新query同上；suggest空白q拒绝；绝对expires_at必须带Z/偏移，建议使用相对天数。
- trash/users/audit增加envelope=true模式返回{items,total,limit,offset}，旧数组模式保留；前端使用分页对象与服务端q过滤，每页只取所需数据。offset分页不是历史快照，数据变化时刷新。
- merge/split产生新文件，version=max(source.version)+1；replaced_from记录第一源ID（merge多源同时写审计source_file_ids）；不是替换原件，也不冒充完整版本历史。PDF锁仅保护PDFium操作，写盘/SQL/镜像不占PDF锁。
- 请求取消贯穿fetch与body读取及blob；连接异常/超时/取消/解析错误区分。仅替换文件元数据PATCH允许最多3次瞬时故障重试，非幂等POST不自动重试。
- OCR手动请求加入取消；自动结算失败有限重试。客户端取消不能撤销已经提交的后端写入，持久化任务可从文件重入找回。无人访问时自动结算、同ID重试和账务归属是独立C3改造，本轮不伪称完成。
- OpenAPI从真实装配app导出并校验，响应模型、参数上限、权限扩展同步。浏览器测试分真实API项目与明确故障注入项目，不能用mock结果代替真实集成。
