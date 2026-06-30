# GreatOCR Phase 5 Quality Report and Validation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现完整性验证、关键字段差异检查和面向用户的 `quality-report.docx`。

**Architecture:** 质量报告由结构化 `quality-report.json` 生成 Word 报告。报告面向普通业务用户，明确页码、片段、问题类型、说明和建议。

**Tech Stack:** python-docx、pydantic、pytest。

---

## 可改范围

允许创建或修改：

- `src/greatocr/validation/checks.py`
- `src/greatocr/validation/quality.py`
- `src/greatocr/reports/quality_docx.py`
- `src/greatocr/reports/quality_json.py`
- `tests/test_validation_checks.py`
- `tests/test_quality_report_json.py`
- `tests/test_quality_report_docx.py`
- `tests/test_pipeline_quality_report.py`

不允许生成带框选截图的 PDF 或额外页面截图报告。

## 验收条件

- 输出 `quality-report.docx`。
- 可选输出 `intermediates/quality-report.json`。
- 每个 issue 至少包含页码、原文片段、问题类型、说明、建议。
- 报告包含总体质量评级、页数、处理时间、供应商、页面类型统计、表格降级、字体替换、自动校正摘要。

## 测试方式

- 结构化报告 JSON schema 测试。
- Word 报告读回文本测试。
- pipeline 端到端测试：fake provider → DOCX → quality report。

## 任务

### Task 5.1: 实现完整性验证

**Files:**
- Create: `src/greatocr/validation/checks.py`
- Create: `tests/test_validation_checks.py`

- [ ] 写测试：输入 3 页，输出模型少 1 页时生成 `missing_page` issue。
- [ ] 写测试：关键字段原值和当前值不一致且无修改记录时生成 high severity issue。
- [ ] 写测试：图片 asset 缺失时生成 issue。
- [ ] 实现 `run_integrity_checks(document, preflight) -> list[Issue]`。
- [ ] 运行 `python -m pytest tests/test_validation_checks.py -v`。

### Task 5.2: 实现质量评级

**Files:**
- Create: `src/greatocr/validation/quality.py`
- Create: `tests/test_quality_report_json.py`

- [ ] 写测试：无 high severity issue 时可评级为高。
- [ ] 写测试：存在关键字段 issue 时总体评级不掩盖问题。
- [ ] 写测试：多处表格降级时评级下降为中或低。
- [ ] 实现 `compute_quality_summary(document, issues) -> QualitySummary`。
- [ ] 运行 `python -m pytest tests/test_quality_report_json.py -v`。

### Task 5.3: 输出 quality-report.json

**Files:**
- Create: `src/greatocr/reports/quality_json.py`
- Modify: `tests/test_quality_report_json.py`

- [ ] 写测试：JSON 包含文件名、页数、处理时间、provider、页面统计。
- [ ] 写测试：issue 字段完整。
- [ ] 实现 `write_quality_json(summary, issues, output_path)`。
- [ ] 运行 `python -m pytest tests/test_quality_report_json.py -v`。

### Task 5.4: 输出 quality-report.docx

**Files:**
- Create: `src/greatocr/reports/quality_docx.py`
- Create: `tests/test_quality_report_docx.py`

- [ ] 写测试：Word 报告标题包含 `GreatOCR 质量报告`。
- [ ] 写测试：报告中能读到页码、片段、问题类型、建议。
- [ ] 写测试：无 issue 时报告仍包含“未发现关键风险”。
- [ ] 实现 `write_quality_docx(report, output_path)`。
- [ ] 运行 `python -m pytest tests/test_quality_report_docx.py -v`。

### Task 5.5: 接入 pipeline

**Files:**
- Modify: `src/greatocr/pipeline.py`
- Create: `tests/test_pipeline_quality_report.py`

- [ ] 写测试：pipeline 生成 `quality-report.docx`。
- [ ] 写测试：普通模式保留 `intermediates/quality-report.json`。
- [ ] 写测试：敏感模式默认不保留中间 JSON。
- [ ] 实现验证和报告阶段。
- [ ] 运行 `python -m pytest tests/test_pipeline_quality_report.py -v`。

## Phase 5 完成后交付物

- `quality-report.docx`。
- `quality-report.json`。
- 完整性和质量评级逻辑。

