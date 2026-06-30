# GreatOCR Phase 4 Editable DOCX Reconstruction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 从统一文档模型生成可编辑 `result.docx`，优先保留标题、段落、列表、基础表格、图片、页眉页脚和页码。

**Architecture:** DOCX 生成使用确定性规则，不让 LLM 直接写 Word XML。复杂或低置信表格退化为图片并生成 issue。

**Tech Stack:** python-docx、Pillow、zipfile、pytest。

---

## 可改范围

允许创建或修改：

- `src/greatocr/docx/builder.py`
- `src/greatocr/docx/styles.py`
- `src/greatocr/docx/tables.py`
- `src/greatocr/docx/assets.py`
- `src/greatocr/docx/validate_docx.py`
- `tests/test_docx_builder.py`
- `tests/test_docx_tables.py`
- `tests/test_docx_assets.py`
- `tests/test_docx_openability.py`

不允许实现翻译、高保真文本框式排版或 Word 自动化。

## 验收条件

- 生成标准 `.docx` 文件。
- 标题、段落、列表和基础表格可编辑。
- 图片、签名、印章可插入。
- 低置信表格可降级为图片并记录 issue。
- DOCX 解包结构有效，Microsoft Word 打开无修复提示。

## 测试方式

- 自动解包检查 `[Content_Types].xml`、`word/document.xml`。
- 使用 python-docx 读回段落和表格数量。
- 对 fixture 文档执行快照式 XML 关键片段检查。
- 人工用 Microsoft Word 打开阶段样本。

## 任务

### Task 4.1: 建立 DOCX builder

**Files:**
- Create: `src/greatocr/docx/builder.py`
- Create: `src/greatocr/docx/styles.py`
- Create: `tests/test_docx_builder.py`

- [ ] 写测试：最小 Document 生成存在的 `.docx`。
- [ ] 写测试：标题和段落可被 python-docx 读回。
- [ ] 实现 `build_docx(document: Document, output_path: Path) -> DocxBuildResult`。
- [ ] 实现基础样式：正文、标题 1、标题 2、页眉、页脚。
- [ ] 运行 `python -m pytest tests/test_docx_builder.py -v`。

### Task 4.2: 实现页面和分页基础策略

**Files:**
- Modify: `src/greatocr/docx/builder.py`
- Modify: `tests/test_docx_builder.py`

- [ ] 写测试：多页 Document 在页之间插入分页符。
- [ ] 写测试：页面尺寸和方向写入 section。
- [ ] 实现按 Page 生成 Word 内容和分页。
- [ ] 对分页偏差生成 `pagination_may_drift` issue。
- [ ] 运行 `python -m pytest tests/test_docx_builder.py -v`。

### Task 4.3: 实现表格生成和降级

**Files:**
- Create: `src/greatocr/docx/tables.py`
- Create: `tests/test_docx_tables.py`

- [ ] 写测试：普通表格生成真实 Word table。
- [ ] 写测试：合并单元格写入 Word 合并。
- [ ] 写测试：低置信表格不生成错误可编辑表格，返回降级 issue。
- [ ] 实现 `add_table(document, table_block)`。
- [ ] 实现表格边框、对齐、基础底色。
- [ ] 运行 `python -m pytest tests/test_docx_tables.py -v`。

### Task 4.4: 实现图片、签名和印章

**Files:**
- Create: `src/greatocr/docx/assets.py`
- Create: `tests/test_docx_assets.py`

- [ ] 写测试：图片 asset 插入 DOCX。
- [ ] 写测试：缺失图片生成 issue，不中断整份文档。
- [ ] 写测试：签名和印章按图片保留。
- [ ] 实现 `add_image_asset(document, asset, approximate_position)`。
- [ ] 运行 `python -m pytest tests/test_docx_assets.py -v`。

### Task 4.5: 实现 DOCX 结构有效性检查

**Files:**
- Create: `src/greatocr/docx/validate_docx.py`
- Create: `tests/test_docx_openability.py`

- [ ] 写测试：有效 DOCX 返回 `valid=true`。
- [ ] 写测试：损坏 ZIP 返回明确 validation issue。
- [ ] 实现 `validate_docx_package(path: Path) -> DocxValidationResult`。
- [ ] 运行 `python -m pytest tests/test_docx_openability.py -v`。

### Task 4.6: 接入 pipeline 输出 result.docx

**Files:**
- Modify: `src/greatocr/pipeline.py`
- Modify: `tests/test_pipeline_model_outputs.py`

- [ ] 写测试：pipeline 使用 fake provider 可生成 `result.docx`。
- [ ] 写测试：DOCX 生成 issue 被合并回 Document issues。
- [ ] 实现 DOCX 生成阶段。
- [ ] 运行 `python -m pytest tests/test_pipeline_model_outputs.py tests/test_docx_builder.py -v`。

## Phase 4 完成后交付物

- `result.docx`。
- 可编辑标题、段落、列表和基础表格。
- 图片和签名印章保留。
- DOCX 有效性检查。

