# Backend Map

本文件按后端分层组织，适合在明确要改 server 代码时快速定位。

## 1. 应用装配与运行时

- FastAPI 生命周期、路由挂载、后台 reminder loop：`server/app/main.py:25`、`43`、`58`。
- 全局配置：`server/app/core/config.py:19`。
- 数据库 engine / session / migration bootstrap：`server/app/core/database.py:20`、`28`、`36`、`45`、`58`。
- Docker 默认环境变量：`docker-compose.yml:16-55`，重点看 `LLM_*`、`MAIL_*`、`EMBEDDING_DIMENSIONS`。

## 2. 鉴权与安全

- Bearer 解析与当前用户：`server/app/core/auth.py:22`。
- AI 安全 user_id 读取：`server/app/core/auth.py:54`。
- 管理员校验：`server/app/core/auth.py:82`。
- 密码哈希：`server/app/core/security.py:31`。
- JWT 生成/解析：`server/app/core/security.py:62`、`86`。

## 3. Router 层

- `auth`: `server/app/routers/auth.py:14`、`26`、`37`、`48`。
- `admin`: `server/app/routers/admin.py:14`、`23`。
- `schedules`: `server/app/routers/schedules.py:14`、`27`、`37`、`59`。
- `sync`: `server/app/routers/sync.py:16`、`26`、`36`。
- `parse`: `server/app/routers/parse.py:29`、`61`、`109`、`137`、`169`。
- `rag`: `server/app/routers/rag.py:22`、`41`、`55`、`74`。
- `share`: `server/app/routers/share.py:14`、`26`。
- `health`: `server/app/routers/health.py:8`。

## 4. Service 层

### 通用业务

- 认证：`server/app/services/auth_service.py:16`、`32`、`41`、`66`。
- 管理员：`server/app/services/admin_service.py:12`、`18`。
- 云端日程 CRUD：`server/app/services/schedule_service.py:16`、`34`、`56`、`81`。
- 分享：`server/app/services/share_service.py:28`、`61`。
- 同步：`server/app/services/sync_service.py:22`、`100`、`108`。

### AI 相关

- LangChain runtime 封装：`server/app/services/ai_runtime.py:88`。
- AI token 配额、Shanghai 日窗口与 usage ledger：`server/app/services/quota_service.py:38`、`103`、`119`、`129`。
- 旧的 OpenAI-compatible provider：`server/app/services/llm_provider.py:16`。
- Parse 主类入口：`server/app/services/parse_service.py:823`。
- Parse 状态与兼容动作派生：`server/app/services/parse_service.py:532`、`536`、`576`、`580`。
- Parse fallback 提取：`server/app/services/parse_service.py:643`。
- Parse runtime/fallback 合并与时间保护：`server/app/services/parse_service.py:722`、`753`、`843`。
- Parse 会话上下文与响应组装：`server/app/services/parse_service.py:976`、`1020`。
- Parse 路由层 quota 接入：`server/app/routers/parse.py:35`、`67`、`115`、`144`。
- RAG 主类入口：`server/app/services/rag_service.py:132`。
- RAG 结构化源文本：`server/app/services/rag_service.py:194`。
- RAG 向量 SQL：`server/app/services/rag_service.py:377`。
- RAG 检索后按 schedule 聚合：`server/app/services/rag_service.py:497`。
- RAG 路由层 quota 接入：`server/app/routers/rag.py:32`、`59`、`82`、`114`。

### Reminder 相关

- reminder 是否启用后台 loop：`server/app/services/email_reminder_service.py:31`。
- 日程级 reminder 重算：`server/app/services/email_reminder_service.py:57`。
- 扫描并发送：`server/app/services/email_reminder_service.py:113`。
- 背景循环：`server/app/services/email_reminder_service.py:175`。
- Brevo 发送实现：`server/app/services/mail_service.py:49`。

## 5. Model 层

- 用户：`server/app/models/user.py:12`。
- 日程：`server/app/models/schedule.py:22`。
- 分享 UUID：`server/app/models/share_link.py:11`。
- 向量 chunk：`server/app/models/vector_chunk.py:10`。
- AI usage ledger：`server/app/models/ai_usage_event.py:11`。
- 知识库状态：`server/app/models/knowledge_base_state.py:11`。
- 对话历史：`server/app/models/chat_history.py:12`。
- 邮件提醒：`server/app/models/email_reminder.py:11`。
- 枚举：`server/app/models/enums.py:6`。

## 6. Schema 层

- 用户与 auth：`server/app/schemas/auth.py:10`、`17`、`18`、`20`、`25`、`30`、`37`、`56`。
- 日程：`server/app/schemas/schedule.py:12`、`36`、`60`。
- 同步：`server/app/schemas/sync.py:12`、`38`、`42`、`56`。
- Parse：`server/app/schemas/parse.py:17`、`25`、`84`、`90`、`105`。
- RAG：`server/app/schemas/rag.py:9`、`13`、`23`、`34`、`39`、`51`。
- 分享：`server/app/schemas/share.py:10`、`22`。
- Admin：`server/app/schemas/admin.py:10`、`21`。

## 7. Migration 与脚本

- Alembic 环境：`server/alembic/env.py`。
- 迁移版本：`server/alembic/versions/0001_baseline.py` 到 `server/alembic/versions/0007_ai_usage_ledger.py`，其中配额相关为 `server/alembic/versions/0006_demo_quota_tiers.py:1` 与 `server/alembic/versions/0007_ai_usage_ledger.py:1`。
- 启动前自动迁移脚本：`server/app/scripts/bootstrap_migrations.py`。
- 性能探针：`server/app/scripts/perf_probe.py`。

## 8. 后端阅读建议

- 想改接口行为：先读对应 router，再跳 service，同步打开同名 schema。
- 想改配额 / 层级 / token 记账：先读 `quota_service.py`，再读 `auth.py`、`parse.py`、`rag.py`，最后回看 `ai_usage_event.py` 与配额相关 migration。
- 想改 Parse：优先读 `server/app/schemas/parse.py:17`、`84`、`90`，再读 `server/app/services/parse_service.py:532`、`922`、`976`、`1020`。
- 想改 RAG：优先读 `server/app/services/rag_service.py:194`、`377`、`497`、`580`、`793`、`831`。
- 想改 reminder：优先读 `server/app/services/email_reminder_service.py:57`、`113`，然后看 `server/app/services/mail_service.py:49`。
- 想确认数据库字段：读 model，再回看对应 migration。
