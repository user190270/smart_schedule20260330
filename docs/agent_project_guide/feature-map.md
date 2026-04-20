# Feature Map

本文件按“功能链路”组织，适合回答“某段实现到底在哪”。

## 1. 认证与用户资料

- 后端入口：`server/app/routers/auth.py:14`、`26`、`37`、`48`。
- 后端实现：注册 `server/app/services/auth_service.py:16`，登录 `:32`，个人资料更新 `:66`。
- 鉴权依赖：`server/app/core/auth.py:22`、`54`、`82`。
- JWT 与密码：`server/app/core/security.py:31`、`62`、`86`。
- 前端状态：`frontend/src/stores/auth.ts:24`。
- 前端 API：`frontend/src/api/auth.ts:32`、`38`、`44`、`49`。
- 首页登录 UI：`frontend/src/views/HomeView.vue:218`、`238`、`258`、`269`。
- 邮箱保存 UI：`frontend/src/views/ScheduleView.vue:512`、`532`。
- 测试：`server/tests/test_auth_api.py:16`，邮箱配置测试 `server/tests/test_email_reminders.py:64`。

## 2. 本地日程仓与本地提醒

- 本地记录结构：`frontend/src/repositories/local-schedules.ts:30`。
- 新建本地记录：`frontend/src/repositories/local-schedules.ts:251`。
- 本地仓 store：`frontend/src/stores/local-schedules.ts:300`。
- 创建/更新：`frontend/src/stores/local-schedules.ts:393`、`421`。
- 删除菜单与冲突解法：`frontend/src/stores/local-schedules.ts:713`、`780`。
- 本地提醒同步：`frontend/src/services/notification.ts:138`，取消 `:187`。
- 日程页面 UI：创建 `frontend/src/views/ScheduleView.vue:455`，编辑 `:470`，保存 `:537`，删除 `:589`，冲突解决 `:623`。
- 后端云端 CRUD：路由 `server/app/routers/schedules.py:14`、`27`、`37`、`59`，服务 `server/app/services/schedule_service.py:16`、`56`、`81`。
- 测试：`server/tests/test_schedule_crud.py:19`、`61`、`90`、`101`、`115`。

## 3. Push / Pull / 同步冲突

- 首页操作入口：Push `frontend/src/views/HomeView.vue:289`，Pull `:311`，Rebuild `:331`。
- 云端状态 store：`frontend/src/stores/cloud-sync.ts:69`。
- Push/Pull/Rebuild 动作：`frontend/src/stores/cloud-sync.ts:157`、`202`、`232`。
- Push 计划与结果回写：`frontend/src/stores/local-schedules.ts:610`、`637`。
- Pull 合并与冲突标记：`frontend/src/stores/local-schedules.ts:476`、`780`。
- 后端路由：`server/app/routers/sync.py:16`、`26`、`36`。
- 后端服务：Push `server/app/services/sync_service.py:22`，Pull `:100`，状态 `:108`。
- 关键测试：`server/tests/test_sync_api.py:52`、`107`、`136`、`162`、`187`。

## 4. AI 解析与草稿确认

- 前端 API：`frontend/src/api/parse.ts:61`、`68`、`78`。
- 前端会话 store：`frontend/src/stores/parse-session.ts:49`。
- 前端页面入口：发消息 `frontend/src/views/ParseView.vue:504`，确认保存 `:537`。
- 草稿回写与补丁同步：`frontend/src/views/ParseView.vue:349`、`370`、`407`、`426`。
- 后端路由：普通解析 `server/app/routers/parse.py:22`，SSE `:37`，会话创建 `:67`，继续对话 `:78`，草稿补丁 `:92`。
- Fallback 解析计划：`server/app/services/parse_service.py:569`。
- LangChain 合并逻辑：`server/app/services/parse_service.py:651`、`681`、`765`。
- 会话上下文打包：`server/app/services/parse_service.py:912`。
- 单轮消息处理：`server/app/services/parse_service.py:995`。
- 会话入口：创建 `server/app/services/parse_service.py:1021`，继续 `:1039`，补丁 `:1051`。
- 合同测试：`server/tests/test_parse_contract.py:22`、`83`、`119`、`136`、`166`、`202`、`233`、`261`、`290`、`318`。
- LangChain 路径测试：`server/tests/test_ai_langchain_integration.py:97`、`161`、`226`。

## 5. RAG 知识库重建、检索、流式问答

- 前端 API：检索 `frontend/src/api/rag.ts:61`，SSE 消费 `:69`。
- 前端页面：重建 `frontend/src/views/RagView.vue:244`，仅检索 `:262`，流式回答 `:310`。
- 后端路由：重建单条 `server/app/routers/rag.py:22`，全量重建 `:41`，检索 `:55`，流式回答 `:74`。
- 源文本构造：`server/app/services/rag_service.py:194`。
- 向量检索 SQL：`server/app/services/rag_service.py:377`。
- 候选答案聚合：`server/app/services/rag_service.py:497`。
- 单条/全量重建：`server/app/services/rag_service.py:580`、`666`。
- 检索：`server/app/services/rag_service.py:733`。
- 文本回答与流式回答：`server/app/services/rag_service.py:754`、`793`。
- 流式准备与会话历史：`server/app/services/rag_service.py:831`。
- 成功后持久化历史：`server/app/services/rag_service.py:566`。
- 关键测试：`server/tests/test_rag_workflow.py:79`、`111`、`169`、`185`、`265`、`287`、`333`、`369`、`447`。
- LangChain 路径测试：`server/tests/test_ai_langchain_integration.py:260`、`329`。

## 6. 公开分享

- 前端生成分享：`frontend/src/views/ShareView.vue:149`。
- 前端公开预览：`frontend/src/views/PublicShareView.vue:53`。
- 公共链接拼接：`frontend/src/services/public-share.ts:18`、`22`。
- 后端路由：创建 `server/app/routers/share.py:14`，公开读取 `:26`。
- 后端服务：`server/app/services/share_service.py:28`、`61`。
- 测试：`server/tests/test_share_api.py:39`、`53`、`57`。

## 7. 管理员后台

- 前端页面：加载用户 `frontend/src/views/AdminView.vue:136`，切换启用状态 `:181`，重置配额 `:214`。
- 前端 API：`frontend/src/api/admin.ts:17`、`22`。
- 后端路由：`server/app/routers/admin.py:14`、`23`。
- 后端服务：`server/app/services/admin_service.py:12`、`18`。
- 测试：`server/tests/test_admin_api.py:35`、`54`、`58`、`66`。

## 8. 云端邮件提醒

- 前端邮箱配置：`frontend/src/views/ScheduleView.vue:31`、`512`。
- 前端日程内提醒开关：`frontend/src/views/ScheduleView.vue:191`、`485`、`503`。
- 本地仓对 reminder 字段的归一化：`frontend/src/stores/local-schedules.ts:82`、`421`。
- 后端用户邮箱更新触发 reminder 同步：`server/app/services/auth_service.py:66`。
- 后端日程写入触发 reminder 同步：`server/app/services/schedule_service.py:16`、`56`、`81`。
- reminder 调度：`server/app/services/email_reminder_service.py:57`、`100`、`107`、`113`、`175`。
- 邮件发送：`server/app/services/mail_service.py:49`。
- 数据模型：`server/app/models/email_reminder.py:11`。
- 测试：`server/tests/test_email_reminders.py:64`、`77`、`89`、`118`、`151`、`161`。

## 9. 演示层级、配额管理与 token 记账

- 首页头像入口：`frontend/src/views/HomeView.vue:28`、`282`、`286`。
- 配额页路由与页面：`frontend/src/router/index.ts:52`、`54`，`frontend/src/views/QuotaView.vue:1`、`24`、`29`、`160`、`181`。
- 前端用户资料与演示升级 API：`frontend/src/api/auth.ts:4`、`11`、`60`，store 在 `frontend/src/stores/auth.ts:74`、`86`。
- 超额错误提示：`frontend/src/services/api-errors.ts:20`、`28`。
- 后端 demo upgrade 路由：`server/app/routers/auth.py:67`。
- 用户资料中的 quota 字段与升级请求：`server/app/schemas/auth.py:10`、`17`、`18`、`56`。
- 后端资料同步与层级提升：`server/app/services/auth_service.py:60`、`110`。
- 配额核心语义、Shanghai 日窗口与 usage ledger 写入：`server/app/services/quota_service.py:38`、`103`、`119`、`129`。
- Parse / RAG 入口记账：`server/app/routers/parse.py:35`、`67`、`113`、`142`，`server/app/routers/rag.py:32`、`59`、`82`、`114`。
- 账本模型与迁移：`server/app/models/ai_usage_event.py:11`，`server/alembic/versions/0006_demo_quota_tiers.py:1`，`server/alembic/versions/0007_ai_usage_ledger.py:1`。
- 关键测试：`server/tests/test_ai_quota_demo.py:107`、`226`、`257`、`293`、`300`。
