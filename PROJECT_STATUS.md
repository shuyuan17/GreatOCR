# PROJECT STATUS

最后更新：2026-07-02

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

### 已完成的验收结论

- 主线 V2.2 已有验收报告：[v2-2-page-selection-providers-report.md](/D:/codeprojects/codex-workspace/GreatOCR/docs/acceptance/v2-2-page-selection-providers-report.md)
- 真实 MinerU 上传已对一份用户明确授权 PDF 完成
- 加密 PDF 会被正确识别并阻止
- fake provider 离线验收已通过
- V2.3 后端巡检报告已整理至 [docs/reports/RUN_REPORT.md](/D:/codeprojects/codex-workspace/GreatOCR/docs/reports/RUN_REPORT.md)
- V2.3 前端应用壳报告已整理至 [docs/reports/FRONTEND_REPORT.md](/D:/codeprojects/codex-workspace/GreatOCR/docs/reports/FRONTEND_REPORT.md)
- V2.3 App Shell 基础验证报告已整理至 [docs/reports/VALIDATION_REPORT.md](/D:/codeprojects/codex-workspace/GreatOCR/docs/reports/VALIDATION_REPORT.md)

## 未完成的功能

### V2.3 未完成

- 图形界面尚未合入主线
- 本地 Web 应用尚未形成完整交付版本
- App Shell 已完成并通过基础启动与联通验证，但业务页面仍未完成
- FastAPI 与前端静态资源的一体化发布尚未完成
- 完整端到端人工验收报告尚未生成

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
| `/api/tasks` | `POST` | 创建任务 |
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
- 当前字段：
  - `task_id`
  - `display_name`
  - `source_path`
  - `sensitive`
  - `selected_pages`
  - `provider_profile_id`
  - `approved_fallback_ids`
  - `status`
  - `output_dir`
  - `quality_rating`
  - `requested_action`
  - `created_at`

### `provider_profiles`

- 作用：保存 provider 配置，不保存 API key
- 当前字段：
  - `profile_id`
  - `display_name`
  - `adapter_type`
  - `endpoint`
  - `public`
  - `capabilities`
  - `approved_fallback_ids`

补充说明：

- API key 不写入 SQLite
- 凭据设计放在 Windows 当前用户凭据存储中
- 敏感任务默认不把真实 `source_path` 持久化进数据库

## 前端完成了哪些页面

主线 `main` 当前没有前端目录。

V2.3 工作树中的前端状态如下：

- 已完成：
  - `frontend/package.json`
  - `vite`/`vitest`/`TypeScript` 基础配置
  - 前端测试基架
  - `App.tsx`
  - `api.ts`
  - `main.tsx`
  - 一个可运行的 App Shell，包含导航与健康检查状态显示
  - 一个导航层级的基础页面结构，当前包含：
    - 任务中心
    - 新建任务
    - 设置

- 尚未完成：
  - `TaskCenter.tsx`
  - `NewTaskWizard.tsx`
  - `TaskDetail.tsx`
  - `Settings.tsx`

结论：前端已从“纯脚手架阶段”进入“可运行 App Shell 阶段”。当前页面已可启动、可显示、可访问 `/api/health`，但业务页面仍以占位实现为主，尚未进入完整可交付状态。

## 如何启动项目

### 当前主线 `main`

先准备本地 Python 虚拟环境并安装依赖：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -e ".[dev]"
```

常用检查命令：

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m greatocr.cli doctor
```

本地预检一个 PDF：

```powershell
.\.venv\Scripts\python.exe -m greatocr.cli convert <你的PDF路径> --dry-run
```

页/表返工入口：

```powershell
.\.venv\Scripts\python.exe -m greatocr.cli rework --task-dir <任务目录> --pages 3,8
.\.venv\Scripts\python.exe -m greatocr.cli rework --task-dir <任务目录> --tables table-1
```

### V2.3 工作树

V2.3 当前已有明确的开发态启动与验证记录，可参考：

- [docs/reports/RUN_REPORT.md](/D:/codeprojects/codex-workspace/GreatOCR/docs/reports/RUN_REPORT.md)
- [docs/reports/FRONTEND_REPORT.md](/D:/codeprojects/codex-workspace/GreatOCR/docs/reports/FRONTEND_REPORT.md)
- [docs/reports/VALIDATION_REPORT.md](/D:/codeprojects/codex-workspace/GreatOCR/docs/reports/VALIDATION_REPORT.md)

当前判断：

- 后端可启动
- 前端可启动
- 前端可访问 `/api/health`
- App Shell 页面可正常显示

但它仍然是开发态成果，不等于完整交付版本；现阶段更适合继续开发与测试，而不是直接给最终用户使用。

## 当前有哪些已知问题

### 主线层面

- `main` 只有 CLI 和引擎，没有图形界面
- 缺少统一的项目说明文档，启动方式主要分散在计划和测试中
- `convert` 命令仍偏“预检/占位”，不是完整端到端 GUI 工作流

### V2.3 层面

- Web API 尚未合入主线
- 前端 App Shell 已实现并通过基础验证，但核心业务页面仍未完成
- 前后端集成、静态资源托管和最终启动方式尚未收口
- 主线与工作树状态需要在文档中明确区分

### 安全与流程边界

- 真实 MinerU 上传必须逐次得到用户明确授权
- 项目根目录仍存在 `MinerU API key.txt`，虽然已被 `.gitignore` 排除，但后续开发仍需继续遵守“不读取、不打印、不提交”的规则

## 建议下一步开发顺序

1. 先完成 V2.3 Task 5：把前端应用壳、`App.tsx`、`api.ts`、`main.tsx` 补齐，让导航与 token 请求链路真正可运行。
2. 再完成 V2.3 Task 6：实现任务中心、新建任务向导、任务详情、设置页面。
3. 完成 V2.3 Task 7：把前端构建产物接入 FastAPI，跑通 fake provider 端到端验收，并补完整的 `v2-3-local-app-report.md`。
4. V2.3 全量验证通过后，再决定是否合并回 `main`。
5. 最后进入 V2.4：做便携打包、干净环境验证和发布说明。

## 现状结论

现在的 GreatOCR 已经是一个功能完整度较高的本地 OCR 重建引擎，主线价值主要在“CLI + 安全控制 + Word 重建 + 质量报告 + 选页与返工能力”。项目当前真正的开发重心已经从“引擎能力”转向“本地图形界面交付”和“最终发布形态”。

补充结论：

- 以仓库根目录视角看，主线仍以 CLI/引擎为主
- 以 V2.3 工作树视角看，App Shell 已完成并通过基础验证
- 下一阶段重点应放在业务页面落地与前后端完整集成，而不是重复搭脚手架
