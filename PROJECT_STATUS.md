# PROJECT STATUS

最后更新：2026-07-04

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

### V2.3 M3.5 新增

- **任务中心结果展开区** — OCR 完成后可在任务中心查看任务状态、文件名、页码范围、创建时间与输出目录
- **结果文件下载** — 支持下载 `result.docx`，并在存在时下载 `quality-report.docx`
- **当前任务默认展开** — 新建任务完成后跳转到任务中心，当前任务结果默认展开，其他任务保持收起
- **缺失文件友好提示** — 当结果文件或质量报告不存在时，前端显示友好提示而不是技术错误
- **结果接口补齐** — 新增任务结果摘要接口与标准结果文件下载接口

### V2.3 M3.1 新增

- **前端页码范围输入** — 新建任务页支持输入 `1`、`1-3`、`1,3,5`、`1-3,5,7-9`
- **前端简单校验与提示** — 非法格式会在上传前提示，避免发起错误请求
- **上传参数透传** — 前端把页码范围传给后端 `pages` 参数
- **后端范围解析** — `/api/tasks/upload-file` 支持解析单页与范围表达式；留空时仍默认处理全部页面

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
  - ✅ 前端已支持指定页码范围上传
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
| M3.1 | PDF 指定页码上传 | ✅ 已完成 |
| M3.2 | OCR 识别质量参数优化（单词粘连、数字格式） | 中 |
| M3.3 | 版式还原优化（未知块类型、分页漂移） | 中 |
| M3.4 | 任务中心完善（删除任务、复制路径、打开文件夹、完成时间记录） | ✅ 已完成 |
| M3.5 | 任务中心列表化（表格展示、分页、多选、批量删除） | ✅ 已完成 |
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
| `/api/tasks/{task_id}` | `DELETE` | 删除单个任务记录（仅数据库，不删文件） |
| `/api/tasks/batch-delete` | `POST` | 批量删除任务记录（仅数据库，不删文件） |

## 数据库目前有哪些表

说明：以下 SQLite 表同样属于 V2.3 工作树，主线 `main` 尚未引入数据库。

### `schema_version`

- 作用：记录数据库 schema 版本
- 当前版本：`2`

### `tasks`

- 作用：保存任务元数据与队列状态
- 当前字段：`task_id`, `display_name`, `source_path`, `sensitive`, `selected_pages`, `provider_profile_id`, `approved_fallback_ids`, `status`, `output_dir`, `quality_rating`, `requested_action`, `created_at`, `completed_at`

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
- 已支持结果下载，但仍缺少 DOCX 在线预览与问题项高亮
- 设置页的 API Key 输入 UI 未实现（需通过 curl 或 Postman 配置）

### 安全与流程边界

- 真实 MinerU 上传必须逐次得到用户明确授权
- 项目根目录仍存在 `MinerU API key.txt`，虽然已被 `.gitignore` 排除，但后续开发仍需继续遵守"不读取、不打印、不提交"的规则

## 现状结论

V2.3 M2 已完成——第一条真实 OCR 流程已可运行（fake provider 离线测试 + MinerU 真实 OCR 双流程均已通过真实文件验证）。质量评级 **high**，但存在单词粘连、数字格式、未知块类型等识别问题，以及印章提取、页码选择等功能缺口。

后续开发建议从 **M3.2 OCR 识别质量优化** 和 **M3.3 版式还原优化** 继续推进；M3.5 的基础结果查看与下载流程已可用。
## 2026-07-04 补充更新

- 已完成 V2.3 M3.5 本地输出目录改造的第一版闭环。
- 新建任务页增加"输出路径"输入框，默认从后端读取默认输出目录。
- 当前默认输出目录为工作树下 `data/exports`，用户也可以手动填写自定义目录。
- 后端会校验输出目录是否存在、是否为目录、是否可写；校验失败时返回友好错误。
- OCR 结果文件改为直接生成到本地输出目录下的任务子目录，不再依赖错误的远端下载思路。
- 任务中心列表已改为最新任务优先展示。
- 从新建任务完成后跳转进入任务中心时，当前任务默认展开，其它任务保持收起。

### 本次新增接口与行为

- `GET /api/tasks/default-output-dir`
- `POST /api/tasks/upload-file` 支持 `output_dir`
- `GET /api/tasks` 按最新任务倒序返回

## 2026-07-04 补充更新（M3.4 任务中心完善）

- **已完成 V2.3 M3.4 任务中心完善** — 让用户可以在任务中心管理已运行 OCR 任务。
- **任务记录新增 `completed_at` 字段** — 任务完成时记录完成时间，前端列表可查看。
- **任务完成时间记录** — `SerialWorker.finish()` 改为调用 `complete_task()`，同时更新状态和完成时间。
- **删除任务功能** — 新增 `DELETE /api/tasks/{task_id}` 接口，前端任务中心每张任务卡片增加"删除任务"按钮，带确认弹窗。
- **删除只清除数据库记录** — 不删除输出文件和原始文件，确认弹窗中有明确提示。
- **复制输出路径** — 前端增加"复制输出路径"按钮，调用 `navigator.clipboard.writeText()`，点击后反馈"已复制"。
- **打开输出文件夹** — 前端增加"打开输出文件夹"按钮，调用已有的 `POST /api/tasks/{task_id}/open-output` 接口。
- **数据库 schema 升级到 v2** — 新增 `completed_at` 列，提供从 v1 到 v2 的自动迁移。
- **所有现有 205 个测试全部通过**，前端 TypeScript 编译通过。

### 本次新增接口

- `DELETE /api/tasks/{task_id}` — 删除任务记录（仅数据库，不删文件）

### 当前限制

- 当前默认输出目录仍是开发阶段目录 `data/exports`，尚未切到未来安装包落点。
- 前端现有部分历史文案存在编码混杂问题，但不影响本次输出目录、结果展示和下载流程。
- 结果文件目前仍以本地文件下载为主，未提供在线预览。
- 任务详情页未做缩略图预览和 DOCX 在线查看。
- 删除任务仅移除数据库记录，不回收磁盘空间（输出文件保留在磁盘上）。

## 2026-07-04 补充更新（M3.5 任务中心列表化）

- **已完成 V2.3 M3.5 任务中心列表化** — 将任务中心从卡片式布局改为表格/列表形式，更加直观易管理。
- **表格布局** — 每行展示：选择框、文件名、页码范围、状态、创建时间、完成时间、输出目录、操作。
- **多选/全选** — 表头全选复选框（支持半选态），每行独立复选框。仅终止状态（已完成/失败/已取消/部分完成）的任务可选择。
- **批量删除** — 顶部"删除选中"按钮，选中后弹出确认弹窗，确认后批量删除任务记录（仅数据库，不删文件）。
- **分页功能** — 每页 10 条，支持上一页/下一页，显示当前页码和总条数。
- **操作区精简** — 每行操作区以图标按钮展示：📁（打开文件夹）、📋（复制路径）、🗑（删除）。下载链接降级为小字文本"结果"/"报告"，不再使用大按钮。
- **结果加载优化** — 结果文件信息改为页面加载时统一为所有终止状态任务懒加载，不再依赖展开操作。
- **批量删除接口** — 新增 `POST /api/tasks/batch-delete` 接口，接收 `task_ids` 数组，逐个删除。
- **所有 205 个测试继续通过**，前端 TypeScript 编译通过。

### 本次新增接口

- `POST /api/tasks/batch-delete` — 批量删除任务记录（仅数据库，不删文件）

### 当前限制（同前）

- 当前默认输出目录仍是开发阶段目录 `data/exports`，尚未切到未来安装包落点。
- 前端现有部分历史文案存在编码混杂问题，但不影响本次功能使用。
- 结果文件目前仍以本地文件下载为主，未提供在线预览。
- 任务详情页未做缩略图预览和 DOCX 在线查看。
- 删除任务仅移除数据库记录，不回收磁盘空间（输出文件保留在磁盘上）。
