# P7-S1 Frontend Absorption Audit

## Goal

- 审查 `unit22-agent-c/frontend` 代码，形成“可直接吸收 / 需改造后吸收 / 禁止吸收”清单
- 以 `unit22-agent-a` + `docs/api_contract.md` 为唯一可信契约基线
- 本文档不信任 agent-c 的 docs，只基于可读代码判断

## Audit Scope

- candidate root: `C:/Users/nor/Documents/project/study/unit22-agent-c/frontend/src`
- baseline root: `C:/Users/nor/Documents/project/study/unit22-agent-a/frontend/src`
- contract refs:
  - `docs/api_contract.md`
  - `server/app/schemas/*.py`
  - `server/app/routers/*.py`

## Findings Summary

- agent-c 的前端视觉与交互细节明显强于主线 scaffold，可作为 UI 候选素材
- agent-c 的 API 契约与当前后端存在系统性漂移，不能直接并入主线
- agent-c 中仍硬编码 `X-User-Id` 且值类型错误（字符串），与本轮 JWT 目标冲突
- 多个页面使用后端不存在的字段与接口方法，需要先做契约回收

## Classification

## A. 可直接吸收（低风险）

- `src/App.vue`
  - 可吸收内容：路由过渡动画（`fade`）、底部导航中文标签、视图切换结构
  - 约束：保持现有路由路径不变（`/ /schedules /parse /rag /share`）

- `src/views/HomeView.vue`
  - 可吸收内容：健康检查状态徽章、交互反馈样式、基础排版
  - 约束：保留现有 `fetchHealth` 契约，不引入额外字段依赖

- `src/style.css`（部分）
  - 可吸收内容：`glass-panel`、`status-badge`、列表/卡片过渡、Vant 样式微调
  - 约束：仅做“样式层吸收”，不携带任何业务字段假设

## B. 需改造后吸收（中风险）

- `src/views/ScheduleView.vue`
  - 可复用：卡片式列表、弹窗表单、编辑/删除交互流程
  - 必改点：
    - 字段从 `description/is_all_day/priority/status/tags` 回收到 `location/remark/source`
    - 更新方法从 `PUT` 回收到后端契约 `PATCH`
    - 去掉后端不存在的 `GET /schedules/{id}` 依赖

- `src/views/ParseView.vue`
  - 可复用：输入区 + 结果预览 + 保存确认交互框架
  - 必改点：
    - `human_review_required` 更正为 `requires_human_review`
    - `draft.description` 更正为 `draft.remark`（并补 `draft.location` 显示）
    - 保存 payload 回收到 `ScheduleCreate` 契约字段

- `src/views/RagView.vue`
  - 可复用：聊天气泡、流式打字机、滚动交互
  - 必改点：
    - 请求体从 `{ question }` 更正为 `{ query, top_k }`
    - SSE 解析按后端事件 `meta/token/done` 对齐
    - 删除临时 `X-User-Id` 注入逻辑

- `src/views/ShareView.vue`
  - 可复用：分享卡片 UI、复制链接交互
  - 必改点：
    - 创建响应字段从 `share_url/uuid` 对齐为 `share_uuid/share_path/schedule`
    - 展示字段从 `description/status` 回收到 `remark/location/source`
    - 只读页严格走脱敏 DTO

## C. 禁止吸收（高风险）

- `src/api/client.ts`
  - 问题：
    - 硬编码 `X-User-Id`
    - 值为 `"test_user_1"`，后端当前依赖要求正整数，运行时将触发 401
  - 结论：禁止迁入主线

- `src/api/schedule.ts`
  - 问题：
    - DTO 大量字段不在后端契约中（`description/is_all_day/priority/status/tags`）
    - 更新接口使用 `PUT`，与后端 `PATCH` 不一致
  - 结论：禁止直接迁入，需重写

- `src/api/parse.ts`
  - 问题：返回字段使用 `human_review_required`，与后端不一致
  - 结论：禁止直接迁入，需重写

- `src/api/rag.ts`
  - 问题：
    - 请求字段 `question` 与后端 `query` 不一致
    - 继续使用 `X-User-Id` 头
  - 结论：禁止直接迁入，需重写

- `src/api/share.ts`
  - 问题：响应字段使用 `share_url/uuid`，与后端 `share_uuid/share_path` 不一致
  - 结论：禁止直接迁入，需重写

## Contract Drift Matrix

- schedule:
  - agent-c: `description/status/tags/priority/is_all_day`
  - backend: `location/remark/source/is_deleted`
- parse:
  - agent-c: `human_review_required`
  - backend: `requires_human_review`, `can_persist_directly`
- rag:
  - agent-c request: `question`
  - backend request: `query`, `top_k`
- share:
  - agent-c create response: `share_url`, `uuid`
  - backend create response: `share_uuid`, `share_path`, `schedule`
- auth transport:
  - agent-c: hardcoded `X-User-Id`
  - round target: `Authorization: Bearer <jwt>`

## P7-S2 Execution Input

- 先在主线重建 contract-first API 层：
  - `frontend/src/api/auth.ts`
  - `frontend/src/api/schedules.ts`
  - `frontend/src/api/parse.ts`
  - `frontend/src/api/rag.ts`
  - `frontend/src/api/share.ts`
- 再选择性迁移 agent-c 的 UI 结构与动画层
- 迁移原则：样式可迁、契约不可漂移、鉴权不可回退

## Done Check (for P7-S1)

- 已完成候选审查与分类
- 已形成主线可执行吸收清单
- 已明确下一步 `P7-S2` 的输入边界与禁入项
