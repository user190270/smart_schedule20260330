# Tests And Docs Map

本文件回答两个问题：

- 这个仓库已经有哪些验证入口。
- 现有 `docs/` 里哪些文档值得读，哪些可以暂时跳过。

## 1. 测试索引

- 烟雾测试：`server/tests/test_smoke.py:12`。
- Auth：`server/tests/test_auth_api.py:16`、`40`、`51`。
- Admin：`server/tests/test_admin_api.py:35`、`54`、`58`、`66`。
- 日程 CRUD：`server/tests/test_schedule_crud.py:19`、`61`、`86`、`90`、`101`、`115`。
- Sync：`server/tests/test_sync_api.py:52`、`107`、`136`、`162`、`187`。
- Parse 合同：`server/tests/test_parse_contract.py:35`、`59`、`129`、`142`、`214`、`335`。
- RAG 工作流：`server/tests/test_rag_workflow.py:79`、`111`、`169`、`185`、`265`、`287`、`333`、`369`、`447`。
- Share：`server/tests/test_share_api.py:39`、`53`、`57`。
- Email reminders：`server/tests/test_email_reminders.py:64`、`77`、`89`、`118`、`151`、`161`。
- LangChain 路径：`server/tests/test_ai_langchain_integration.py:97`、`149`、`161`、`217`、`226`、`261`、`329`。

## 2. 测试阅读建议

- 先想知道“产品承诺是什么”：读功能对应 test 名称即可，测试名已经很说明意图。
- 改 Parse 时：优先看 `test_parse_contract.py` 和 `test_ai_langchain_integration.py`。
- 改 RAG 时：优先看 `test_rag_workflow.py` 和 `test_ai_langchain_integration.py`。
- 改 reminder 时：优先看 `test_email_reminders.py`。
- 改同步时：优先看 `test_sync_api.py` 与前端 `local-schedules` 冲突逻辑。

## 3. 现有 docs/ 阅读优先级

- `docs/current_state.md`
  - 当前开发轮次、已交付状态、验证结果、剩余限制。
- `docs/working_contract.md`
  - 团队协作边界与执行约束。
- `docs/task_board.md`
  - 任务拆分与步骤状态。
- `docs/api_contract.md`
  - 接口边界参考，只有在需要确认增量 contract 时再读。
- `docs/decision_log.md`
  - 历史决策与取舍，只有在需要解释“为什么这样做”时再读。

## 4. 其他现有 docs 的用途

- `docs/docker_workflow.md`
  - Docker 开发与容器命令。
- `docs/mobile_lan_setup.md`
  - 移动端局域网调试。
- `docs/client_capacitor_plan.md`
  - Capacitor 相关规划背景。
- `docs/p11_acceptance_checklist.md`
  - 某轮验收视角。
- `docs/p7_s1_frontend_absorption_audit.md`
  - 前端吸收分析，偏历史过程。
- `docs/ai_workflow_patterns.md`
  - AI 工作流经验沉淀，不是业务实现入口。

## 5. 运行与验证命令

- 后端依赖与入口定义：`server/pyproject.toml`。
- 前端脚本：`frontend/package.json`。
- 本地全栈容器：`docker-compose.yml`。
- 当前状态文档记录的最近验证：
  - `docker compose exec api pytest /app/tests -q`
  - `docker compose exec frontend npm run build`
  - `python skills/coding-agent-loop-en/scripts/docs_consistency_check.py --docs-root docs`

## 6. 阅读时建议忽略的生成物

- `server/smart_schedule.db`
- `server/.pytest_cache/`
- `server/.venv/`
- `frontend/node_modules/`
- `frontend/android/build/`
- `tmp/`

## 7. 如果要快速建立置信度

- 先读 `README.md`。
- 再读功能对应测试文件的测试名。
- 最后只打开相关实现起点，不要整包导入大文件。

