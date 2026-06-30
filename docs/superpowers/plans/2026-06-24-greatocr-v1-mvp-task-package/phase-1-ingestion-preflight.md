# GreatOCR Phase 1 Ingestion and Preflight Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现单个 PDF 的输入校验、基础预检、页面分类和安全确认模型。

**Architecture:** 输入层只负责读取本地 PDF 元数据和生成预检结果，不调用外部解析服务。页面类型先用可解释启发式判断，后续 provider 可覆盖或补充。

**Tech Stack:** Python 3.11+、pydantic、pypdf 或 pymupdf、pytest。

---

## 可改范围

允许创建或修改：

- `src/greatocr/ingest/preflight.py`
- `src/greatocr/ingest/page_classifier.py`
- `src/greatocr/security.py`
- `src/greatocr/config.py`
- `src/greatocr/cli.py`
- `tests/test_preflight.py`
- `tests/test_security.py`
- `tests/fixtures/pdfs/`

不允许真实上传文件或调用 MinerU。

## 验收条件

- 能识别 PDF 是否存在、扩展名、文件头、是否加密、页数。
- 能输出每页基础信息：页码、宽高、旋转、初步页面类型。
- 能生成用户确认所需的数据流向摘要。
- 敏感文件默认禁用公共 API。

## 测试方式

- 使用程序生成的小型 PDF 夹具测试正常、缺失、非 PDF、加密 PDF。
- 单元测试页面分类：文本页、空扫描模拟页、混合页。
- CLI smoke：`convert --dry-run` 输出预检摘要，不生成 DOCX。

## 任务

### Task 1.1: 定义预检数据结构

**Files:**
- Create: `src/greatocr/ingest/preflight.py`
- Create: `tests/test_preflight.py`

- [ ] 写测试：正常 PDF 返回 `page_count`、`file_sha256`、`encrypted=false`。
- [ ] 写测试：不存在文件返回明确异常 `InputFileNotFound`。
- [ ] 写测试：非 PDF 文件返回 `InvalidPdfError`。
- [ ] 实现 `PreflightResult`、`PagePreflight`、`run_preflight(pdf_path: Path) -> PreflightResult`。
- [ ] 运行 `python -m pytest tests/test_preflight.py -v`。

### Task 1.2: 实现页面分类

**Files:**
- Create: `src/greatocr/ingest/page_classifier.py`
- Modify: `src/greatocr/ingest/preflight.py`
- Modify: `tests/test_preflight.py`

- [ ] 写测试：包含可提取文字的页面分类为 `native_text`。
- [ ] 写测试：无文本但有图像或内容流的页面分类为 `scanned`。
- [ ] 写测试：既有文本又有图片的页面分类为 `mixed`。
- [ ] 实现 `classify_page(page) -> Literal["native_text", "scanned", "mixed"]`。
- [ ] 将页面分类结果写入 `PagePreflight.page_type`。
- [ ] 运行 `python -m pytest tests/test_preflight.py -v`。

### Task 1.3: 实现安全配置与数据流向摘要

**Files:**
- Create: `src/greatocr/security.py`
- Modify: `src/greatocr/config.py`
- Create: `tests/test_security.py`

- [ ] 写测试：普通模式允许使用上次批准的 provider。
- [ ] 写测试：敏感模式默认禁止 public provider。
- [ ] 写测试：安全摘要不包含 API Key。
- [ ] 实现 `SecurityMode`、`RetentionPolicy`、`DataFlowSummary`。
- [ ] 实现 `build_data_flow_summary(config, preflight) -> DataFlowSummary`。
- [ ] 运行 `python -m pytest tests/test_security.py -v`。

### Task 1.4: 接入 CLI dry-run

**Files:**
- Modify: `src/greatocr/cli.py`
- Modify: `tests/test_cli.py`

- [ ] 写测试：`convert sample.pdf --dry-run` 打印页数、页面类型统计、供应商和留存策略。
- [ ] 实现 `--dry-run` 只运行预检和安全摘要。
- [ ] 运行 `python -m pytest tests/test_cli.py tests/test_preflight.py tests/test_security.py -v`。

## Phase 1 完成后交付物

- PDF 预检能力。
- 页面类型初判。
- 普通/敏感模式安全摘要。
- CLI dry-run。

