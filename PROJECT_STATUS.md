# PROJECT STATUS

最后更新：2026-07-03

## 当前项目目标是什么

GreatOCR 当前的总体目标是把一个本地 PDF 重建引擎逐步做成可在 Windows 10/11 使用的文档恢复工具：

- 输入单个 PDF
- 完成预检、选页、解析、结构化映射、Word 重建、质量报告
- 对敏感文件和外部上传做显式安全控制
- 最终补齐本地图形界面和便携发布版本

按当前计划，项目分为 4 个阶段：

1. V2.1：重建质量核心
2. V2.2：选页与多 provider 架构
3. V2.3：本地 FastAPI + React 图形界面
4. V2.4：便携打包与发布验收

其中：

- `main` 已完成并合入 V2.2
- V2.3 正在独立工作树 `D:\codeprojects\codex-workspace\GreatOCR\.worktrees\v2-3-local-web-app` 中继续开发，尚未合入主线

## 已完成的功能

### 主线 `main` 已完成

- PDF 预检：页数、加密状态、页面类型识别（原生文本、扫描、混合）
- 安全策略：普通/敏感模式、是否允许外部上传、结果保留策略
- MinerU provider 适配器
- fake provider 离线验收链路
- 统一文档模型：页面、块、坐标、问题项、稳定 ID
- 坐标与版面修复：方向、旋转、双栏阅读顺序
- Word 重建：段落、表格、图片、签字盖章图片、页眉页脚、页面尺寸
- Markdown 中间稿导出
- 质量报告：JSON + DOCX
- 关键字段保护与可选文本校正
- 进度、检查点、断点恢复
- 失败页返工、表格返工
- 选页表达式解析与子 PDF 生成
- 原页码映射恢复
- 多 provider 能力注册表
- 通用多模态实验 provider 适配器
- fallback/审批策略
- 结果版本管理（`result-v1.docx`、`result-v2.docx` 等）
- CLI 入口：`doctor`、`convert`、`rework`

### V2.3 M2 新增

- **文件上传端点** `POST /api/tasks/upload-file` — 接收文件上传，自动预检获取总页数，创建任务
- **启动脚本** `scripts/serve.py` — 一键初始化数据库、seed fake-default provider、后台 Worker 自动处理任务
- **前端新建任务页面** — 文件选择、Provider 选择、「开始 OCR」按钮、状态轮询、结果展示
- **前端任务中心页面** — 任务列表、状态标签、自动刷新、质量评分与输出目录显示
- **前端设置页面** — Provider 列表展示、API Key 配置状态、配置命令指引
- **依赖补充** — `python-multipart` 用于文件上传

### 真实文件测试验证（2026-07-03）

- **测试 Provider**: MinerU（真实 OCR）
- **测试文件**: `testsamples/中英夹杂的.pdf`（2 页扫描件，中英双语董事会决议）
- **测试结果**:
  - ✅ 上传 → 任务创建 → OCR 处理 → 结果生成 全流程通过
  - ✅ 质量评级：**high**（质量报告）
  - ✅ 中英双语内容均被正确识别
  - ⚠️ 存在单词粘连、数字格式混用问题
  - ⚠️ MinerU 识别的页码块类型未正确映射
  - ❌ 印章/签字区域未提取，仅输出文字文本
  - ❌ 前端暂不支持指定页码范围
- **详细报告**: [docs/reports/real-file-ocr-test.md](./docs/reports/real-file-ocr-test.md)

### 已完成的验收结论

- 主线 V2.2 已有验收报告
- V2.3 M2 后端 API 已验证：health / upload / start / get / list / providers / auth 共 7 个场景全部通过
- fake provider（离线测试）✅ MinerU（真实 OCR）✅ 双流程均跑通
- 现有 31 个后端测试、2 个前端测试全部通过

## 未完成的功能

### V2.3 待完成

| 任务 | 内容 | 优先级 |
|------|------|--------|
| M3.1 | PDF 指定页码上传 | 高 |
| M3.2 | OCR 识别质量参数优化（单词粘连、数字格式） | 中 |
| M3.3 | 版式还原优化（未知块类型、分页漂移） | 中 |
| M3.4 | 印章/签字识别能力评估 | 低 |
| M3.5 | 结果导出/展示优化（预览、下载、问题高亮） | 高 |
| — | 任务详情页（缩略图预览、结果 DOCX 查看） | 中 |
| — | 设置页 API Key 输入 UI | 中 |
| — | UI 美化 | 低 |
| — | 前后端一体化启动 | 低 |
| — | 完整端到端人工验收报告 | 低 |

### V2.4 未开始

- PyInstaller 或等价方式的便携打包
- 干净环境验证
- 免预装 Python/Node 的桌面交付

## 后端有哪些 API

说明：以下 API 目前存在于 V2.3 工作树中，主线 `main` 还没有这些 HTTP 接口。

基础信息：

- 前缀：`/api`
- 认证方式：请求头 `X-GreatOCR-Token`
- 仅允许本机会话，且限制浏览器 `Origin`

### 基础接口

| 路径 | 方法 | 作用 |
| --- | --- | --- |
| `/api/health` | `GET` | 健康检查，返回服务是否可用 |

### Provider 接口

| 路径 | 方法 | 作用 |
| --- | --- | --- |
| `/api/providers` | `GET` | 列出 provider 配置及密钥是否已配置 |
| `/api/providers` | `POST` | 新增或更新 provider 配置；密钥通过请求头 `X-GreatOCR-Provider-Key` 传入 |
| `/api/providers/{profile_id}` | `DELETE` | 删除 provider 配置与凭据；若正在被运行中任务使用则拒绝 |
| `/api/providers/{profile_id}/test-connection` | `POST` | 测试 provider 连通性 |
| `/api/providers/{profile_id}/test-capabilities` | `POST` | 返回该 provider 的能力描述 |

### 任务接口

| 路径 | 方法 | 作用 |
| --- | --- | --- |
| `/api/tasks` | `POST` | 创建任务（需提供服务器端文件路径） |
| `/api/tasks/upload-file` | `POST` | **V2.3 M2 新增** — 上传文件并创建任务（一体式端点） |
| `/api/tasks` | `GET` | 列出任务 |
| `/api/tasks/{task_id}` | `GET` | 查看任务详情 |
| `/api/tasks/{task_id}/preflight` | `POST` | 对任务源 PDF 执行预检 |
| `/api/tasks/{task_id}/thumbnails` | `GET` | 渲染指定页窗口的缩略图 |
| `/api/tasks/{task_id}/start` | `POST` | 启动任务；敏感文件走公开 provider 时要求二次确认 |
| `/api/tasks/{task_id}/pause` | `POST` | 暂停任务 |
| `/api/tasks/{task_id}/cancel` | `POST` | 取消任务 |
| `/api/tasks/{task_id}/retry-failed-pages` | `POST` | 针对失败页发起重试 |
| `/api/tasks/{task_id}/versions` | `GET` | 列出结果版本文件 |
| `/api/tasks/{task_id}/open-output` | `POST` | 打开任务输出目录 |

## 数据库目前有哪些表

说明：以下 SQLite 表同样属于 V2.3 工作树，主线 `main` 尚未引入数据库。

### `schema_version`

- 作用：记录数据库 schema 版本
- 当前版本：`1`

### `tasks`

- 作用：保存任务元数据与队列状态
- 当前字段：`task_id`, `display_name`, `source_path`, `sensitive`, `selected_pages`, `provider_profile_id`, `approved_fallback_ids`, `status`, `output_dir`, `quality_rating`, `requested_action`, `created_at`

### `provider_profiles`

- 作用：保存 provider 配置，不保存 API key
- 当前字段：`profile_id`, `display_name`, `adapter_type`, `endpoint`, `public`, `capabilities`, `approved_fallback_ids`

补充说明：

- API key 不写入 SQLite，通过 Windows 凭据管理器（keyring）管理
- 敏感任务默认不把真实 `source_path` 持久化进数据库

## 前端完成了哪些页面

| 页面 | 路由 | 状态 |
| --- | --- | --- |
| 首页 | `/` | ✅ 欢迎信息 + 快速开始按钮 |
| 新建任务 | `/new` | ✅ 文件选择 + Provider 选择 + 上传 + 启动 + 轮询 + 结果 |
| 任务中心 | `/tasks` | ✅ 任务列表 + 状态标签 + 自动刷新 |
| 设置 | `/settings` | ✅ Provider 列表 + API Key 状态 + 配置指引 |

## 如何启动项目

### 一键后端启动（推荐）

```powershell
.\.venv\Scripts\python.exe scripts\serve.py
```

首次启动自动创建 `data/` 目录和 `fake-default` provider。

### 前端启动（另一个终端）

```powershell
cd .\frontend\
C:\Users\user\.workbuddy\binaries\node\versions\22.22.2\node.exe .\node_modules\vite\bin\vite.js
```

浏览器访问 `http://localhost:5173/`。

## 当前有哪些已知问题

### 识别质量问题

- 英语段落存在单词粘连（`theCompany` 应为 `the Company`）
- 数字格式前后不一致（`52,077,455.23` 与 `52.077.455.23` 混用）
- MinerU 识别的 `page_number` 块类型未映射到模型，产生 `unknown_provider_block` 警告

### 版本中问题

- 印章/签字区域仅输出文字，无图像提取
- 前端暂不支持指定页码范围，默认全部页面
- 缺少结果预览/下载功能
- 设置页的 API Key 输入 UI 未实现（需通过 curl 或 Postman 配置）

### 安全与流程边界

- 真实 MinerU 上传必须逐次得到用户明确授权
- 项目根目录仍存在 `MinerU API key.txt`，虽然已被 `.gitignore` 排除，但后续开发仍需继续遵守"不读取、不打印、不提交"的规则

## 现状结论

V2.3 M2 已完成——第一条真实 OCR 流程已可运行（fake provider 离线测试 + MinerU 真实 OCR 双流程均已通过真实文件验证）。质量评级 **high**，但存在单词粘连、数字格式、未知块类型等识别问题，以及印章提取、页码选择等功能缺口。

后续开发建议优先补齐 **M3.1 页码选择** 和 **M3.5 结果展示优化**，再逐步优化 OCR 质量和版式还原。
