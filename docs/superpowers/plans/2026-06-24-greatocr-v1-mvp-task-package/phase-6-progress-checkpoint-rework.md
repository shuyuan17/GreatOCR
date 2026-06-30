# GreatOCR Phase 6 Progress, Checkpoint, and Limited Rework Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现阶段进度、动态预计剩余时间、任务检查点，以及 V1 限定的按页或表格局部返工。

**Architecture:** pipeline 每完成一个阶段写入 `task-manifest.json`。返工只重新解析指定页或表格对应范围，更新统一 JSON 后重新生成整份 DOCX 和质量报告。

**Tech Stack:** Python 3.11+、pydantic、pytest、time.monotonic。

---

## 可改范围

允许创建或修改：

- `src/greatocr/task/manifest.py`
- `src/greatocr/task/progress.py`
- `src/greatocr/task/checkpoints.py`
- `src/greatocr/rework.py`
- `src/greatocr/pipeline.py`
- `src/greatocr/cli.py`
- `tests/test_progress.py`
- `tests/test_checkpoints.py`
- `tests/test_rework.py`
- `tests/test_pipeline_resume.py`

不允许实现段落级任意编辑或 DOCX 内部原位替换。

## 验收条件

- 处理过程能显示阶段、当前页、百分比、已用时间、预计剩余时间。
- 每个主要阶段后更新 `intermediates/task-manifest.json`。
- 任务中断后可从最近完成阶段恢复。
- 按页返工不重新调用未受影响页面的 provider。
- 按表格返工更新对应 table block 并重新生成整份 DOCX。

## 测试方式

- 进度估算单元测试。
- 检查点状态机测试。
- fake provider 调用计数测试返工范围。
- pipeline resume 测试。

## 任务

### Task 6.1: 实现 task manifest

**Files:**
- Create: `src/greatocr/task/manifest.py`
- Create: `tests/test_checkpoints.py`

- [ ] 写测试：manifest 记录 source fingerprint、config、stages、outputs。
- [ ] 写测试：阶段状态只能是 pending、running、succeeded、failed、skipped。
- [ ] 写测试：manifest 不保存 API Key。
- [ ] 实现 `TaskManifest`、`StageRecord`、`load_manifest`、`save_manifest`。
- [ ] 运行 `python -m pytest tests/test_checkpoints.py -v`。

### Task 6.2: 实现进度和预计剩余时间

**Files:**
- Create: `src/greatocr/task/progress.py`
- Create: `tests/test_progress.py`

- [ ] 写测试：阶段权重可计算总体百分比。
- [ ] 写测试：已处理页数增长时预计剩余时间下降。
- [ ] 写测试：provider 不提供细粒度进度时使用阶段权重估算。
- [ ] 实现 `ProgressTracker`、`ProgressSnapshot`、`format_progress_bar`。
- [ ] 运行 `python -m pytest tests/test_progress.py -v`。

### Task 6.3: 接入 pipeline 检查点和 resume

**Files:**
- Create: `src/greatocr/task/checkpoints.py`
- Modify: `src/greatocr/pipeline.py`
- Create: `tests/test_pipeline_resume.py`

- [ ] 写测试：parse 阶段成功后 manifest 标记 succeeded。
- [ ] 写测试：DOCX 阶段失败后重跑可从 document.json 继续。
- [ ] 写测试：resume 时不重复执行已成功阶段。
- [ ] 实现 `run_pipeline(..., resume=True)`。
- [ ] 运行 `python -m pytest tests/test_pipeline_resume.py -v`。

### Task 6.4: 实现按页局部返工

**Files:**
- Create: `src/greatocr/rework.py`
- Create: `tests/test_rework.py`

- [ ] 写测试：请求 page 5 返工时 fake provider 只收到 page 5。
- [ ] 写测试：未受影响页面的 block ID 保持不变。
- [ ] 写测试：返工后重新生成 `document.json`、`result.docx`、`quality-report.docx`。
- [ ] 实现 `rework_pages(task_dir, pages, parser)`。
- [ ] 运行 `python -m pytest tests/test_rework.py -v`。

### Task 6.5: 实现按表格局部返工

**Files:**
- Modify: `src/greatocr/rework.py`
- Modify: `tests/test_rework.py`

- [ ] 写测试：请求 table ID 返工时解析对应页。
- [ ] 写测试：只替换目标 table block，保留同页其他稳定 block。
- [ ] 写测试：找不到 table ID 时给出明确错误。
- [ ] 实现 `rework_tables(task_dir, table_ids, parser)`。
- [ ] 运行 `python -m pytest tests/test_rework.py -v`。

### Task 6.6: 接入 CLI

**Files:**
- Modify: `src/greatocr/cli.py`
- Modify: `tests/test_cli.py`

- [ ] 写测试：`convert sample.pdf --show-progress` 输出文本进度。
- [ ] 写测试：`rework --task-dir ... --pages 5` 调用页返工。
- [ ] 写测试：`rework --task-dir ... --tables tbl_p005_001` 调用表格返工。
- [ ] 实现 CLI 参数。
- [ ] 运行 `python -m pytest tests/test_cli.py tests/test_rework.py -v`。

## Phase 6 完成后交付物

- 进度条和预计剩余时间。
- `task-manifest.json`。
- 断点恢复。
- 页/表格局部返工。

