# GreatOCR

GreatOCR 是一个本地 PDF 文档重建工具项目，目标是把 PDF 预检、OCR/解析、结构化映射、Word 重建、质量报告和后续本地图形界面逐步做成一个可在 Windows 10/11 使用的交付版本。

## 当前状态

- 主线 `main` 已完成 V2.2，当前可稳定使用的能力以 CLI 和重建引擎为主
- V2.3 本地 Web 界面正在独立工作树中推进：
  - 工作树目录：`D:\codeprojects\codex-workspace\GreatOCR\.worktrees\v2-3-local-web-app`
  - 当前阶段：FastAPI 后端已可启动，React App Shell 已完成并通过基础联通验证
- V2.4 便携打包与发布验收尚未开始

更详细状态请看：

- [PROJECT_STATUS.md](/D:/codeprojects/codex-workspace/GreatOCR/PROJECT_STATUS.md)
- [docs/TASK_BOARD.md](/D:/codeprojects/codex-workspace/GreatOCR/docs/TASK_BOARD.md)

## 仓库结构

- `src/`：核心引擎、CLI、后端应用代码
- `tests/`：自动化测试
- `docs/acceptance/`：阶段性验收报告
- `docs/reports/`：运行、前端、验证等执行报告
- `docs/superpowers/`：历史设计与任务分解文档
- `.worktrees/v2-3-local-web-app/`：V2.3 本地 Web 应用独立工作树

## 主线如何启动

先创建虚拟环境并安装依赖：

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

返工入口：

```powershell
.\.venv\Scripts\python.exe -m greatocr.cli rework --task-dir <任务目录> --pages 3,8
.\.venv\Scripts\python.exe -m greatocr.cli rework --task-dir <任务目录> --tables table-1
```

## V2.3 Web 相关说明

V2.3 不在主线直接开发，而是在独立工作树中推进。当前结论是：

- 后端可启动
- 前端可启动
- 前端可访问 `/api/health`
- App Shell 页面可正常显示

相关报告见：

- [docs/reports/RUN_REPORT.md](/D:/codeprojects/codex-workspace/GreatOCR/docs/reports/RUN_REPORT.md)
- [docs/reports/FRONTEND_REPORT.md](/D:/codeprojects/codex-workspace/GreatOCR/docs/reports/FRONTEND_REPORT.md)
- [docs/reports/VALIDATION_REPORT.md](/D:/codeprojects/codex-workspace/GreatOCR/docs/reports/VALIDATION_REPORT.md)

## 协作与文档

开始任何任务前，建议先阅读：

1. [README.md](/D:/codeprojects/codex-workspace/GreatOCR/README.md)
2. [PROJECT_STATUS.md](/D:/codeprojects/codex-workspace/GreatOCR/PROJECT_STATUS.md)
3. [docs/AGENT_GUIDE.md](/D:/codeprojects/codex-workspace/GreatOCR/docs/AGENT_GUIDE.md)
4. [docs/TASK_BOARD.md](/D:/codeprojects/codex-workspace/GreatOCR/docs/TASK_BOARD.md)
5. `docs/reports/` 下相关报告

## 注意事项

- 不要读取、打印或提交根目录中的 `MinerU API key.txt`
- 不要直接在 `main` 上开发新功能
- 优先保证“可以运行、可以测试、可以提交”，再考虑美化和重构
