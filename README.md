# GreatOCR

GreatOCR 是一个本地 PDF 文档重建工具项目，目标是把 PDF 预检、OCR/解析、结构化映射、Word 重建、质量报告和后续本地图形界面逐步做成一个可在 Windows 10/11 使用的交付版本。

## 当前状态

- 主线 `main` 已完成 V2.2，当前可稳定使用的能力以 CLI 和重建引擎为主
- V2.3 本地 Web 界面正在独立工作树中推进：
  - 工作树目录：`D:\codeprojects\codex-workspace\GreatOCR\.worktrees\v2-3-local-web-app`
  - 当前阶段：**V2.3 M2 已完成** — 上传文件 → OCR → 查看结果的完整流程已可运行
  - 支持 fake provider（离线测试）和 MinerU（需配置 API Key）
- V2.4 便携打包与发布验收尚未开始

更详细状态请看：

- [PROJECT_STATUS.md](PROJECT_STATUS.md)
- [docs/TASK_BOARD.md](/D:/codeprojects/codex-workspace/GreatOCR/.worktrees/v2-3-local-web-app/docs/TASK_BOARD.md)

## 仓库结构

- `src/`：核心引擎、CLI、后端应用代码
- `frontend/`：React + Vite 前端应用
- `scripts/`：启动脚本等工具
- `tests/`：自动化测试
- `data/`：运行时数据（SQLite、上传文件、缩略图缓存）— 首次启动自动创建
- `docs/`：文档、任务看板
- `releases/`：发布相关材料
- `.worktrees/v2-3-local-web-app/`：V2.3 本地 Web 应用独立工作树

## 如何启动（V2.3 本地 Web 应用）

### 前置条件

确保已安装 Python 虚拟环境依赖：

```powershell
.\.venv\Scripts\python.exe -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -e ".[dev]"
```

### 一键启动（推荐）

```powershell
.\.venv\Scripts\python.exe scripts\serve.py
```

首次启动会自动：
1. 创建 `data/` 目录（含 SQLite 数据库、上传目录、缩略图缓存）
2. 创建 `fake-default` provider（离线测试用，无需 API Key）
3. 在 `http://127.0.0.1:8399` 启动 FastAPI 后端

### 启动前端（另一个终端）

```powershell
cd .\frontend\
npx pnpm install
npx pnpm dev
```

前端默认在 `http://127.0.0.1:5173` 启动，Vite 自动将 `/api/*` 请求代理到后端。

### 访问应用

打开浏览器访问 `http://127.0.0.1:5173`。

### 配置 MinerU API Key（可选）

如需使用真实 MinerU OCR，请在后端启动后执行：

```powershell
curl -X POST http://127.0.0.1:8399/api/providers `
  -H "X-GreatOCR-Token: greatocr-dev-token-2026" `
  -H "X-GreatOCR-Provider-Key: 你的MinerU_API_Key" `
  -H "Content-Type: application/json" `
  -d '{"profile_id":"mineru-default","display_name":"MinerU","adapter_type":"mineru","endpoint":"https://mineru.net","public":true,"capabilities":{"tables":true,"images":true}}'
```

## 主线如何启动

```powershell
# 常用检查命令
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m greatocr.cli doctor
.\.venv\Scripts\python.exe -m greatocr.cli convert <你的PDF路径> --dry-run
```

## 协作与文档

开始任何任务前，建议先阅读：

1. [README.md](README.md)
2. [PROJECT_STATUS.md](PROJECT_STATUS.md)
3. [docs/AGENT_GUIDE.md](/D:/codeprojects/codex-workspace/GreatOCR/.worktrees/v2-3-local-web-app/docs/AGENT_GUIDE.md)
4. [docs/TASK_BOARD.md](/D:/codeprojects/codex-workspace/GreatOCR/.worktrees/v2-3-local-web-app/docs/TASK_BOARD.md)

## 注意事项

- 不要读取、打印或提交根目录中的 `MinerU API key.txt`
- 不要直接在 `main` 上开发新功能
- 优先保证"可以运行、可以测试、可以提交"，再考虑美化和重构
