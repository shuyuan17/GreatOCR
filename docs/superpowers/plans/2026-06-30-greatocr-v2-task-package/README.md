# GreatOCR V2 实施任务包

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement each phase. Use `superpowers:test-driven-development` before feature code and `superpowers:verification-before-completion` before declaring a phase complete.

**Goal:** 将已确认的 V0.3 规格拆成四个可独立验收的软件增量，最终交付 Windows 10/11 GreatOCR 便携版。

**Architecture:** 保留 V1 的 Python 文档引擎，通过统一文档模型 V2 修复方向、版面、文字和资源问题；再增加页面选择、多模型适配、本机 FastAPI + React 图形界面，最后完成便携打包与发布验收。

**Tech Stack:** Python 3.11+、pydantic、pypdf、PyMuPDF、Pillow、python-docx、httpx、FastAPI、SQLite、React、TypeScript、Vite、pytest、PyInstaller。

---

## 权威输入

- 产品规格：`docs/superpowers/specs/2026-06-23-greatocr-document-reconstruction-design.md`
- V1 回退基线：`releases/v1/`
- V1 交接：`docs/session-handoff-2026-06-25-v1.md`

不得修改 `releases/v1/`。不得读取、打印、复制或提交 `MinerU API key.txt`。真实上传任何测试 PDF 前必须再次取得用户明确确认。

## 本地依赖规则

所有 Python 包安装在项目内 `.venv`，不修改系统 Python：

```powershell
python -m venv .venv
./.venv/Scripts/python.exe -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -e ".[dev]"
```

前端依赖只安装到 `frontend/node_modules/`。执行阶段若清华镜像不可用，应停止并报告，不得未经用户同意改用境外镜像。

## 阶段文件

1. `phase-1-reconstruction-core.md`：方向、坐标、文字、图片、页眉页脚和 Word 重建核心。
2. `phase-2-page-selection-providers.md`：选页、子 PDF、模型能力、实验适配器、失败切换、返工和版本。
3. `phase-3-local-web-app.md`：FastAPI、React、SQLite、Windows 凭据、队列和敏感确认。
4. `phase-4-portable-release.md`：便携打包、干净环境、安全、真实样本和发布验收。

严格按 Phase 1 → Phase 4 执行。每个 phase 完成后先验收，再进入下一阶段。

## Git 规则

当前工作区不是可用 Git 仓库。执行者每个任务结束时先运行：

```powershell
git rev-parse --is-inside-work-tree
```

若返回 `true`，按计划提交；若返回失败，不得擅自 `git init`，改为在阶段验收记录中写明已完成的文件和测试结果，并继续等待用户决定是否建立仓库。

## 总体验收

- 竖版/旋转 PDF 的 Word 方向正确。
- 选中页面全部输出，未选页面不上传。
- 图片和印章使用相对资源路径，不因迁移目录丢失。
- 英文粘连和断行相对 V1 明显改善。
- 失败页可单独重试并重新生成完整版本。
- 敏感文件的供应商和备选服务均经逐任务确认。
- API Key 不进入 SQLite、任务目录、日志或报告。
- Windows 10/11 便携版无需预装 Python、Node.js或管理员权限。
