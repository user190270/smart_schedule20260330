# AI Agent Project Guide

## 目的

这组文档面向后续 AI agent 的低上下文导读。

- 只先读本文件即可获得项目全局视野。
- 需要深入某条链路时，再按本文件给出的二级索引按需导入。
- 目标不是复述代码，而是减少“先去哪里找”的上下文浪费。

## 项目一句话

这是一个 `local-first` 的智能日程系统：前端先把日程保存在本地仓，用户显式执行 `Push / Pull / Rebuild Knowledge Base` 与云端交互；AI 解析只负责生成和维护草稿，用户确认后才真正入库；RAG、公开分享、管理员后台、可选云端邮件提醒都建立在这条主链路之上。

## 技术选型

- 前端：`Vue 3 + TypeScript + Vant + Pinia + Vue Router`，入口见 `frontend/src/main.ts:1`。
- 本地存储：Web 端优先 `IndexedDB`，原生端走 `Capacitor Preferences`，适配层见 `frontend/src/services/local-store.ts:1`。
- 移动能力：`Capacitor Android`，本地通知逻辑在 `frontend/src/services/notification.ts:80`。
- 后端：`FastAPI + SQLAlchemy + Alembic`，应用入口见 `server/app/main.py:25`。
- 云端数据：`PostgreSQL + pgvector`，向量表模型见 `server/app/models/vector_chunk.py:10`。
- AI 编排：`LangChainAiRuntime`，实现见 `server/app/services/ai_runtime.py:28`。
- 邮件提醒：可选 `Brevo`，发送见 `server/app/services/mail_service.py:49`，调度见 `server/app/services/email_reminder_service.py:113`。

## 实现思路

- 本地仓是主工作面：创建、编辑、删除都先作用于 `frontend/src/stores/local-schedules.ts:393`。
- 云端同步是显式动作：Push/Pull 状态和知识库重建统一由 `frontend/src/stores/cloud-sync.ts:157`、`202`、`232` 调度。
- AI 解析不是直接写库：解析会话维护草稿，并显式返回 `state / trace`；确认后才调用本地仓保存，前端在 `frontend/src/views/ParseView.vue:260`、`284`、`551`、`584`，后端在 `server/app/services/parse_service.py:922`、`976`、`1020`、`1148`、`1199`。
- 云端 AI 配额按 `user_id` 做每日 token 软上限：重置窗口与记账在 `server/app/services/quota_service.py:38`、`103`、`119`、`129`，Parse / RAG 接入点在 `server/app/routers/parse.py:35`、`67`、`113`、`142` 与 `server/app/routers/rag.py:32`、`59`、`82`、`114`。
- 知识库只看云端允许索引的日程：重建逻辑在 `server/app/services/rag_service.py:580`、`666`，检索严格带 `user_id` 过滤，见 `server/app/services/rag_service.py:377`。
- 分享走公共只读 DTO：创建与读取在 `server/app/services/share_service.py:28`、`61`。
- 邮件提醒是 sidecar，不替代本地通知：本地通知在前端，云端邮件提醒在后端后台扫描。

## 功能枚举

- 账号注册、登录、个人资料读取与通知邮箱保存。
- 本地日程 CRUD、时间重叠提醒、存储策略选择、本地提醒调度。
- 显式 Push / Pull，同步冲突标记与解决。
- AI 日程解析、多轮澄清、草稿补丁与确认保存。
- RAG 知识库重建、检索、流式问答、多轮追问。
- 演示层级、头像进入的配额管理页、每日 token 配额与 usage ledger。
- UUID 分享与公开只读预览。
- 管理员用户列表、启用/禁用、每日 token 配额重置。
- 可选云端邮件提醒与后台发送。

## 核心边界

- `local-first` 不是口号，而是状态结构：前端本地记录包含 `presence / sync_intent / storage_strategy / conflict_snapshot`，定义见 `frontend/src/repositories/local-schedules.ts:30`。
- Parse 路径强制 `human-in-the-loop`：`ai_parsed` 日程必须显式确认后才能落库，校验见 `server/app/services/schedule_service.py:16` 与测试 `server/tests/test_schedule_crud.py:90`。
- AI 配额语义是“每日 token”而不是“每日调用次数”：按 `Asia/Shanghai` 自然日重置，`ai_usage_events` 保留每次云端调用账本，见 `server/app/services/quota_service.py:103`、`129` 与 `server/app/models/ai_usage_event.py:11`。
- 同步策略是单条记录级 LWW：核心逻辑在 `server/app/services/sync_service.py:22`。
- RAG 做多租户隔离时依赖 SQL 层过滤，不只依赖上层逻辑，见 `server/app/services/rag_service.py:393`。
- 邮件提醒只对云端日程有意义，且发送不在请求线程内完成，见 `server/app/services/email_reminder_service.py:57`、`113`、`175`。

## 高信号目录树

```text
docs/
  agent_project_guide/
    README.md
    feature-map.md
    backend-map.md
    frontend-map.md
    tests-and-docs-map.md

server/
  app/
    main.py
    core/
    models/
    routers/
    schemas/
    services/
  alembic/
  tests/

frontend/
  src/
    api/
    repositories/
    router/
    services/
    stores/
    views/
  android/
```

## 按需导入策略

- 先看“某个功能从哪里进、会走到哪几层”：读 `feature-map.md`。
- 需要后端分层全景：读 `backend-map.md`。
- 需要前端状态、页面和本地仓关系：读 `frontend-map.md`。
- 需要配额 / 层级 / AI token 记账链路：先读 `feature-map.md`，再按需跳 `frontend-map.md` 的 `QuotaView.vue` 与 `backend-map.md` 的 `quota_service.py` / `parse.py` / `rag.py`。
- 需要验证入口、已有项目文档、运行命令：读 `tests-and-docs-map.md`。

## 推荐阅读起点

- 应用装配：`server/app/main.py:25`，`frontend/src/App.vue:1`，`frontend/src/router/index.ts:14`。
- 本地主状态：`frontend/src/stores/local-schedules.ts:300`。
- 云端状态：`frontend/src/stores/cloud-sync.ts:69`。
- Parse 核心：`server/app/services/parse_service.py:823`。
- RAG 核心：`server/app/services/rag_service.py:132`。

## 非核心目录

默认不要把以下目录整包导入上下文，除非任务明确相关：

- `server/.venv/`
- `server/.pytest_cache/`
- `frontend/node_modules/`
- `frontend/android/build/`
- `tmp/`
- `.git-upload-*`
- `.worktree-*/`
- `media/`
- `prompts/`
