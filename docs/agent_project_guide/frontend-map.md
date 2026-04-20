# Frontend Map

本文件按前端状态与页面分层组织，适合在明确要改 `frontend/src` 时快速定位。

## 1. App Shell 与路由

- 应用入口：`frontend/src/main.ts:1`。
- 外层壳与 tab 切换：`frontend/src/App.vue:1`、`11`、`53`、`135`、`142`。
- 路由表：`frontend/src/router/index.ts:14`。
- 路由守卫：`frontend/src/router/index.ts:66`。

## 2. 状态管理

- `app`：当前 tab 与 API base URL，`frontend/src/stores/app.ts:4`。
- `auth`：登录态、hydrate、profile 更新，`frontend/src/stores/auth.ts:24`。
- `local-schedules`：最重要的前端业务状态，`frontend/src/stores/local-schedules.ts:300`。
- `cloud-sync`：云端健康、Push/Pull/Rebuild 与设备侧反馈，`frontend/src/stores/cloud-sync.ts:69`。
- `parse-session`：解析会话临时状态，`frontend/src/stores/parse-session.ts:49`。

## 3. 本地仓与适配层

- 本地记录 schema 与迁移兼容：`frontend/src/repositories/local-schedules.ts:30`、`162`。
- 本地记录读写：`frontend/src/repositories/local-schedules.ts:216`、`220`、`225`。
- IndexedDB / Capacitor Preferences 统一适配：`frontend/src/services/local-store.ts:17`、`109`、`142`、`148`、`173`。
- 运行环境与 API base URL：`frontend/src/services/runtime-config.ts:19`、`27`。

## 4. 页面索引

### 首页 `HomeView.vue`

- 账户与系统状态面板：`frontend/src/views/HomeView.vue:1`。
- 头像进入配额管理：`frontend/src/views/HomeView.vue:28`、`282`、`286`。
- Push：`frontend/src/views/HomeView.vue:289`。
- Pull：`frontend/src/views/HomeView.vue:311`。
- Rebuild：`frontend/src/views/HomeView.vue:331`。

### 日程页 `ScheduleView.vue`

- 页面主体与筛选：`frontend/src/views/ScheduleView.vue:1`。
- 邮件提醒配置 UI：`frontend/src/views/ScheduleView.vue:31`。
- 新建/编辑弹层：`frontend/src/views/ScheduleView.vue:130`。
- 新建入口：`frontend/src/views/ScheduleView.vue:455`。
- 编辑入口：`frontend/src/views/ScheduleView.vue:470`。
- 保存：`frontend/src/views/ScheduleView.vue:537`。
- 删除确认：`frontend/src/views/ScheduleView.vue:589`。
- 冲突解决：`frontend/src/views/ScheduleView.vue:623`。

### 解析页 `ParseView.vue`

- 会话区与草稿确认卡：`frontend/src/views/ParseView.vue:1`。
- 草稿与会话状态映射：`frontend/src/views/ParseView.vue:349`、`370`。
- 草稿补丁防抖：`frontend/src/views/ParseView.vue:407`、`426`、`446`。
- 发起/继续解析：`frontend/src/views/ParseView.vue:504`。
- 确认保存到本地仓：`frontend/src/views/ParseView.vue:537`。

### 知识库页 `RagView.vue`

- 状态面板与诊断提示：`frontend/src/views/RagView.vue:1`、`171`。
- 重建：`frontend/src/views/RagView.vue:244`。
- 仅检索：`frontend/src/views/RagView.vue:262`。
- 流式问答：`frontend/src/views/RagView.vue:310`。

### 分享页 `ShareView.vue` / `PublicShareView.vue`

- 生成分享：`frontend/src/views/ShareView.vue:149`。
- 复制/预览：`frontend/src/views/ShareView.vue:168`、`176`、`184`、`191`。
- 公开预览拉取：`frontend/src/views/PublicShareView.vue:53`。

### 配额页 `QuotaView.vue`

- 页面主体与返回入口：`frontend/src/views/QuotaView.vue:2`、`207`。
- 当前层级 / 今日已用 / 每日上限卡片：`frontend/src/views/QuotaView.vue:17`、`24`、`29`。
- 使用进度条：`frontend/src/views/QuotaView.vue:34`。
- 演示升级：`frontend/src/views/QuotaView.vue:57`、`186`。

### 管理员页 `AdminView.vue`

- 读用户列表：`frontend/src/views/AdminView.vue:136`。
- 启用/禁用：`frontend/src/views/AdminView.vue:181`。
- 重置配额：`frontend/src/views/AdminView.vue:214`。

## 5. API 层

- Axios 与原生 HTTP 适配：`frontend/src/api/client.ts:91`、`165`、`174`、`183`。
- Auth：`frontend/src/api/auth.ts:32`、`38`、`44`、`49`。
- Schedules：`frontend/src/api/schedules.ts:47`、`54`、`59`、`64`。
- Sync：`frontend/src/api/sync.ts:48`、`53`、`58`。
- Parse：`frontend/src/api/parse.ts:61`、`68`、`78`。
- RAG：`frontend/src/api/rag.ts:47`、`54`、`61`、`69`。
- Share：`frontend/src/api/share.ts:20`、`25`。
- Admin：`frontend/src/api/admin.ts:17`、`22`。
- Auth 中的 quota / demo upgrade：`frontend/src/api/auth.ts:11`、`12`、`13`、`60`。
- quota 超额提示文案：`frontend/src/services/api-errors.ts:20`、`28`。

## 6. 与移动端直接相关的文件

- Capacitor 配置：`frontend/capacitor.config.ts`。
- Android 壳入口：`frontend/android/app/src/main/java/com/smartschedule/app/MainActivity.java`。
- Android 网络安全配置：`frontend/android/app/src/main/res/xml/network_security_config.xml`。
- 构建脚本：`frontend/package.json` 中 `android:*` 脚本。

## 7. 前端阅读建议

- 想改“本地状态怎么演进”：读 `local-schedules` store，再看 `ScheduleView.vue`。
- 想改“Push/Pull/Rebuild 按钮怎么串起来”：读 `HomeView.vue` 与 `cloud-sync` store。
- 想改配额页或层级入口：读 `QuotaView.vue`，再看 `auth.ts` / `auth` store，必要时再看后端 `quota_service.py`。
- 想改 Parse 页面：读 `ParseView.vue`，再看 `parse-session.ts`，最后再看后端 `parse_service.py`。
- 想改 RAG 页面：读 `RagView.vue`，再看 `api/rag.ts` 的 SSE 消费。
- 想改本地存储或移动适配：读 `local-store.ts`、`notification.ts`、`runtime-config.ts`。
