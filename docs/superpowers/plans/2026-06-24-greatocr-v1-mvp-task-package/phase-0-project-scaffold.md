# GreatOCR Phase 0 Project Scaffold Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建立可测试、可扩展、可被后续 phase 逐步填充的 Python 工程骨架。

**Architecture:** Phase 0 只建立项目结构、依赖、测试配置、CLI 空壳和固定输出目录约定，不接入 OCR 或 DOCX 生成。后续功能都挂到 `src/greatocr` 下，测试统一放在 `tests` 下。

**Tech Stack:** Python 3.11+、pytest、pydantic、typer 或 argparse、ruff 可选。

---

## 可改范围

允许创建或修改：

- `pyproject.toml`
- `src/greatocr/__init__.py`
- `src/greatocr/cli.py`
- `src/greatocr/config.py`
- `src/greatocr/paths.py`
- `tests/test_cli.py`
- `tests/test_paths.py`
- `tests/fixtures/README.md`
- `.gitignore`

不允许实现 MinerU、OCR、DOCX 重建、质量报告或真实文件上传。

## 验收条件

- `python -m greatocr.cli --help` 能显示 CLI 帮助。
- `python -m greatocr.cli doctor` 能输出运行环境检查结果。
- `pytest` 全部通过。
- 工程目录能支持后续 phase 直接添加模块。

## 测试方式

- 单元测试：CLI help、doctor 命令、任务目录命名。
- Smoke test：在当前工作区运行 `python -m greatocr.cli doctor`。

## 任务

### Task 0.1: 创建 Python 包结构

**Files:**
- Create: `pyproject.toml`
- Create: `src/greatocr/__init__.py`
- Create: `tests/fixtures/README.md`
- Modify: `.gitignore`

- [ ] 创建 `pyproject.toml`，声明包名 `greatocr`、Python 版本和测试依赖。
- [ ] 创建 `src/greatocr/__init__.py`，导出版本号 `0.1.0`.
- [ ] 创建 `tests/fixtures/README.md`，说明真实样本必须脱敏，不提交 API Key 或敏感原文。
- [ ] 更新 `.gitignore`，忽略 `.venv/`、`__pycache__/`、`.pytest_cache/`、`outputs/`、`*.key`、`.env`。
- [ ] 运行 `python -m pytest`，预期收集 0 个或少量基础测试且不报导入错误。

### Task 0.2: 创建路径与任务目录工具

**Files:**
- Create: `src/greatocr/paths.py`
- Create: `tests/test_paths.py`

- [ ] 编写测试：给定输入文件名 `sample.pdf`，任务目录名包含安全文件名前缀、时间戳和短指纹。
- [ ] 实现 `safe_stem(name: str) -> str`，去除路径分隔符和不适合目录名的字符。
- [ ] 实现 `make_task_dir(base_dir: Path, source_pdf: Path, created_at: datetime) -> Path`。
- [ ] 运行 `python -m pytest tests/test_paths.py -v`，预期全部通过。

### Task 0.3: 创建 CLI 空壳

**Files:**
- Create: `src/greatocr/cli.py`
- Create: `src/greatocr/config.py`
- Create: `tests/test_cli.py`

- [ ] 编写测试：`doctor` 命令返回 0，输出 Python 版本和 GreatOCR 版本。
- [ ] 实现 `doctor` 命令。
- [ ] 添加 `convert` 命令参数但只做参数校验，不处理 PDF。
- [ ] 运行 `python -m pytest tests/test_cli.py -v`，预期全部通过。
- [ ] 运行 `python -m greatocr.cli doctor`，预期输出运行环境摘要。

## Phase 0 完成后交付物

- 可运行的 Python 包骨架。
- 基础 CLI。
- 可持续扩展的测试框架。

