# GreatOCR Phase 3 Unified Document Model Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将供应商解析结果转换为统一文档模型，生成 `document.json` 和 `content.md`，并实现关键字段保护的基础能力。

**Architecture:** 统一文档模型是 DOCX 生成、质量报告、返工和后续翻译的权威来源。Markdown 只用于阅读和排错，不作为 Word 重建的权威数据。

**Tech Stack:** Python 3.11+、pydantic、pytest、jsonschema 可选。

---

## 可改范围

允许创建或修改：

- `src/greatocr/model/document.py`
- `src/greatocr/model/ids.py`
- `src/greatocr/model/mapper.py`
- `src/greatocr/model/markdown_export.py`
- `src/greatocr/model/critical_fields.py`
- `tests/test_document_model.py`
- `tests/test_mapper_fake.py`
- `tests/test_markdown_export.py`
- `tests/test_critical_fields.py`

不允许在本阶段生成 DOCX 或调用真实 MinerU。

## 验收条件

- `document.json` 包含 Document、Page、Block、TextSpan、Table、Asset、Issue 核心实体。
- 页、区块、表格和文本 span 有稳定 ID。
- Markdown 能反映阅读顺序。
- 关键字段能被标记，且默认不被自动改写。

## 测试方式

- 模型序列化/反序列化测试。
- fake provider 映射测试。
- Markdown 快照测试。
- 关键字段识别测试。

## 任务

### Task 3.1: 定义统一文档模型

**Files:**
- Create: `src/greatocr/model/document.py`
- Create: `tests/test_document_model.py`

- [ ] 写测试：最小 Document 可序列化为 JSON 并读回。
- [ ] 写测试：Block 类型只允许标题、段落、列表、表格、图片、页眉、页脚、页码。
- [ ] 写测试：Issue 必须包含页码、类型、严重程度和说明。
- [ ] 实现 Document、Page、Block、TextSpan、Table、TableCell、Asset、Issue。
- [ ] 运行 `python -m pytest tests/test_document_model.py -v`。

### Task 3.2: 实现稳定 ID 规则

**Files:**
- Create: `src/greatocr/model/ids.py`
- Modify: `tests/test_document_model.py`

- [ ] 写测试：相同页码、区块类型、阅读顺序生成相同 ID。
- [ ] 写测试：局部重解析未变页面时 ID 不变化。
- [ ] 实现 `make_page_id`、`make_block_id`、`make_table_id`、`make_span_id`。
- [ ] 运行 `python -m pytest tests/test_document_model.py -v`。

### Task 3.3: 从 fake provider 映射到统一模型

**Files:**
- Create: `src/greatocr/model/mapper.py`
- Create: `tests/test_mapper_fake.py`

- [ ] 写测试：fake provider 的标题、段落、表格、图片都映射到对应 Block。
- [ ] 写测试：坐标、置信度、来源 provider 元数据被保留。
- [ ] 写测试：无法识别的 provider block 生成 warning issue。
- [ ] 实现 `map_provider_result(raw_result, preflight) -> Document`。
- [ ] 运行 `python -m pytest tests/test_mapper_fake.py -v`。

### Task 3.4: 生成 Markdown 中间稿

**Files:**
- Create: `src/greatocr/model/markdown_export.py`
- Create: `tests/test_markdown_export.py`

- [ ] 写测试：标题导出为 Markdown 标题。
- [ ] 写测试：段落按阅读顺序导出。
- [ ] 写测试：表格导出为 Markdown 表格；合并单元格用可读注释说明。
- [ ] 实现 `export_markdown(document: Document) -> str`。
- [ ] 运行 `python -m pytest tests/test_markdown_export.py -v`。

### Task 3.5: 实现关键字段保护标记

**Files:**
- Create: `src/greatocr/model/critical_fields.py`
- Create: `tests/test_critical_fields.py`

- [ ] 写测试：金额、日期、税号、账号、合同编号被标记为关键字段。
- [ ] 写测试：关键字段不会被普通文本校正规则覆盖。
- [ ] 写测试：低置信关键字段生成 `critical_field_low_confidence` issue。
- [ ] 实现 `detect_critical_fields(document: Document) -> Document`。
- [ ] 运行 `python -m pytest tests/test_critical_fields.py -v`。

### Task 3.6: 接入 pipeline 输出

**Files:**
- Modify: `src/greatocr/pipeline.py`
- Create: `tests/test_pipeline_model_outputs.py`

- [ ] 写测试：pipeline 生成 `intermediates/document.json`。
- [ ] 写测试：pipeline 生成 `intermediates/content.md`。
- [ ] 实现模型映射和中间稿写入。
- [ ] 运行 `python -m pytest tests/test_pipeline_model_outputs.py -v`。

## Phase 3 完成后交付物

- `document.json`。
- `content.md`。
- 关键字段保护基础。
- provider 输出到统一模型的映射层。

