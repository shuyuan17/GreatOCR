# GreatOCR V2.2 Page Selection and Provider Architecture Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让用户只处理指定页面，并建立正式解析器、通用多模态实验适配器、失败切换、页面返工和结果版本机制。

**Architecture:** 页面选择在任何网络调用前完成；子 PDF 只包含获选页面并携带原始页码映射。供应商通过能力声明和统一注册表接入，pipeline 按页保存 provider trace，失败策略只对批准的服务生效。

**Tech Stack:** Python 3.11+、pydantic、pypdf、httpx、pytest、JSON Schema。

---

## 文件结构

- Create: `src/greatocr/selection/page_ranges.py`
- Create: `src/greatocr/selection/subset_pdf.py`
- Create: `src/greatocr/providers/profiles.py`
- Create: `src/greatocr/providers/registry.py`
- Create: `src/greatocr/providers/generic_vision.py`
- Create: `src/greatocr/reasoning/base.py`
- Create: `src/greatocr/reasoning/openai_compatible.py`
- Create: `src/greatocr/providers/fallback.py`
- Create: `src/greatocr/task/versions.py`
- Modify: `src/greatocr/providers/base.py`
- Modify: `src/greatocr/security.py`
- Modify: `src/greatocr/pipeline.py`
- Modify: `src/greatocr/rework.py`
- Modify: `src/greatocr/task/manifest.py`
- Test: `tests/test_page_ranges.py`
- Test: `tests/test_subset_pdf.py`
- Test: `tests/test_provider_registry.py`
- Test: `tests/test_generic_vision_provider.py`
- Test: `tests/test_text_reasoner.py`
- Test: `tests/test_provider_fallback.py`
- Test: `tests/test_result_versions.py`
- Modify: `tests/test_rework.py`

### Task 1: 页码范围解析与原始页码映射

**Files:**
- Create: `src/greatocr/selection/page_ranges.py`
- Create: `tests/test_page_ranges.py`

- [ ] **Step 1: 写失败测试**

```python
def test_parse_mixed_ranges_deduplicates_and_preserves_document_order():
    selection = parse_page_ranges("3, 8-10, 9, 1", page_count=12)
    assert selection.pages == [1, 3, 8, 9, 10]
    assert selection.groups == [[3], [8, 9, 10], [9], [1]]

@pytest.mark.parametrize("value", ["0", "4-2", "13", "3,,4", "x"])
def test_invalid_ranges_are_rejected(value):
    with pytest.raises(PageRangeError):
        parse_page_ranges(value, page_count=12)
```

- [ ] **Step 2: 运行测试确认失败**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_page_ranges.py -v`。

- [ ] **Step 3: 实现明确类型**

```python
class PageSelection(BaseModel):
    expression: str
    pages: list[int]
    groups: list[list[int]]

def parse_page_ranges(expression: str, page_count: int) -> PageSelection:
    groups: list[list[int]] = []
    for raw_token in expression.split(","):
        token = raw_token.strip()
        if not token:
            raise PageRangeError("empty page token")
        if "-" in token:
            parts = token.split("-")
            if len(parts) != 2 or not all(part.isdigit() for part in parts):
                raise PageRangeError(f"invalid page range: {token}")
            start, end = map(int, parts)
            if start > end:
                raise PageRangeError(f"descending page range: {token}")
            group = list(range(start, end + 1))
        elif token.isdigit():
            group = [int(token)]
        else:
            raise PageRangeError(f"invalid page token: {token}")
        if any(page < 1 or page > page_count for page in group):
            raise PageRangeError(f"page outside 1..{page_count}: {token}")
        groups.append(group)
    pages = sorted({page for group in groups for page in group})
    return PageSelection(expression=expression, pages=pages, groups=groups)
```

实现时不得用 `eval`；错误必须包含无效 token 和合法范围 `1..page_count`。

- [ ] **Step 4: 运行测试**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_page_ranges.py -v`  
Expected: PASS。

- [ ] **Step 5: 条件提交**

```powershell
git add src/greatocr/selection/page_ranges.py tests/test_page_ranges.py
git commit -m "feat: parse selected PDF page ranges"
```

### Task 2: 只生成和上传选中页面

**Files:**
- Create: `src/greatocr/selection/subset_pdf.py`
- Create: `tests/test_subset_pdf.py`
- Modify: `src/greatocr/pipeline.py`

- [ ] **Step 1: 写子 PDF 失败测试**

```python
def test_subset_pdf_contains_only_selected_pages(tmp_path):
    source = make_numbered_pdf(tmp_path / "source.pdf", page_count=5)
    result = write_subset_pdf(source, [2, 5], tmp_path / "subset.pdf")
    assert PdfReader(result.path).get_num_pages() == 2
    assert result.task_to_original == {1: 2, 2: 5}

def test_requested_groups_can_produce_separate_outputs():
    selection = parse_page_ranges("3-5, 20-22", page_count=30)
    assert output_groups(selection, split_by_group=True) == [[3, 4, 5], [20, 21, 22]]
    assert output_groups(selection, split_by_group=False) == [[3, 4, 5, 20, 21, 22]]
```

- [ ] **Step 2: 运行并确认失败**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_subset_pdf.py -v`。

- [ ] **Step 3: 实现不修改原 PDF 的 writer**

```python
class SubsetPdfResult(BaseModel):
    path: Path
    task_to_original: dict[int, int]

def write_subset_pdf(source: Path, pages: list[int], output: Path) -> SubsetPdfResult:
    reader, writer = PdfReader(source), PdfWriter()
    for page_number in pages:
        writer.add_page(reader.pages[page_number - 1])
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("wb") as stream:
        writer.write(stream)
    return SubsetPdfResult(path=output, task_to_original={i + 1: p for i, p in enumerate(pages)})
```

Pipeline 必须把 mapping 写入 manifest，并在 mapper 阶段把临时页码恢复为原始页码。
`output_groups` 默认返回一组合并页；启用按区间输出时保留用户输入的区间顺序，但同一区间内去重。Pipeline 为每组建立独立输出版本，并在文件名中包含原始页码范围。

- [ ] **Step 4: 验证未选页面不进入 fake provider 输入**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_subset_pdf.py tests/test_pipeline_parse.py -v`  
Expected: PASS。

- [ ] **Step 5: 条件提交**

```powershell
git add src/greatocr/selection/subset_pdf.py src/greatocr/pipeline.py tests/test_subset_pdf.py tests/test_pipeline_parse.py
git commit -m "feat: process only selected PDF pages"
```

### Task 3: 能力化 provider profile 与注册表

**Files:**
- Modify: `src/greatocr/providers/base.py`
- Create: `src/greatocr/providers/profiles.py`
- Create: `src/greatocr/providers/registry.py`
- Create: `tests/test_provider_registry.py`

- [ ] **Step 1: 写注册与能力筛选测试**

```python
def test_registry_filters_provider_by_required_capabilities():
    registry = ProviderRegistry([text_only_profile(), mineru_profile()])
    matches = registry.match(RequiredCapabilities(layout=True, tables=True))
    assert [profile.profile_id for profile in matches] == ["mineru-default"]
```

- [ ] **Step 2: 定义稳定合同**

```python
class ProviderProfile(BaseModel):
    profile_id: str
    display_name: str
    adapter_type: Literal["mineru", "generic_vision", "fake"]
    endpoint: str
    model_name: str | None = None
    public: bool = True
    verified: bool = False
    capabilities: ProviderCapabilities

class RequiredCapabilities(BaseModel):
    text: bool = True
    layout: bool = False
    tables: bool = False
    images: bool = False
    formulas: bool = False

class ProviderCapabilities(BaseModel):
    text: bool = True
    native_pdf: bool
    scanned_pdf: bool
    coordinates: bool
    layout: bool = False
    tables: bool
    images: bool = False
    formulas: bool
    languages: list[str]
    data_residency: str = "provider-defined"
```

- [ ] **Step 3: 实现注册表，禁止未知 adapter_type**

注册表提供 `get(profile_id)`、`match(requirements)` 和 `create_parser(profile_id, secret_resolver)`；不存在的 profile 返回可读 `UnknownProviderProfile`。

- [ ] **Step 4: 运行 provider 契约测试**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_provider_registry.py tests/test_provider_contract.py tests/test_mineru_adapter.py -v`  
Expected: PASS。

- [ ] **Step 5: 条件提交**

```powershell
git add src/greatocr/providers/base.py src/greatocr/providers/profiles.py src/greatocr/providers/registry.py tests/test_provider_registry.py
git commit -m "feat: add capability-based provider registry"
```

### Task 4: 通用多模态实验适配器

**Files:**
- Create: `src/greatocr/providers/generic_vision.py`
- Create: `tests/test_generic_vision_provider.py`
- Modify: `src/greatocr/providers/registry.py`

- [ ] **Step 1: 写 mock HTTP 测试**

```python
def test_generic_vision_rejects_non_json_model_output(tmp_path, httpx_mock):
    httpx_mock.add_response(json={"choices": [{"message": {"content": "not json"}}]})
    with pytest.raises(ExperimentalProviderOutputError):
        parser().parse_document(sample_pdf(tmp_path), tmp_path / "raw")

def test_generic_vision_writes_schema_valid_result(tmp_path, httpx_mock):
    httpx_mock.add_response(json=chat_response(valid_page_payload()))
    result = parser().parse_document(sample_pdf(tmp_path), tmp_path / "raw")
    assert (result.raw_result_dir / "result.json").exists()
```

- [ ] **Step 2: 定义模型输出 schema**

```python
class VisionBlock(BaseModel):
    type: Literal["title", "paragraph", "list", "table", "image", "header", "footer", "page_number"]
    text: str = ""
    bbox: tuple[float, float, float, float]
    confidence: float = Field(ge=0, le=1)

class VisionPage(BaseModel):
    page_number: int
    blocks: list[VisionBlock]
```

- [ ] **Step 3: 实现适配器边界**

每页渲染为受控分辨率图片，发送固定 system prompt 和 JSON Schema；只解析常见 chat-completions envelope。任何缺页、非法 bbox 或非 JSON 响应都失败，不猜测修复。原响应保存到 provider-raw，异常信息不得含密钥。

- [ ] **Step 4: 运行无网络测试**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_generic_vision_provider.py tests/test_no_secret_leakage.py -v`  
Expected: PASS。

- [ ] **Step 5: 条件提交**

```powershell
git add src/greatocr/providers/generic_vision.py src/greatocr/providers/registry.py tests/test_generic_vision_provider.py
git commit -m "feat: add experimental generic vision adapter"
```

### Task 5: 可选文本校正接口，默认关闭

**Files:**
- Create: `src/greatocr/reasoning/base.py`
- Create: `src/greatocr/reasoning/openai_compatible.py`
- Create: `tests/test_text_reasoner.py`
- Modify: `src/greatocr/pipeline.py`

- [ ] **Step 1: 写默认跳过和关键字段保护测试**

```python
def test_pipeline_does_not_call_reasoner_when_disabled(tmp_path):
    reasoner = CountingReasoner()
    run_reasoning_stage(document(), reasoner, enabled=False)
    assert reasoner.calls == 0

def test_reasoner_cannot_replace_unverified_critical_value():
    doc = document_with_critical_span("CNY 52,077,455.23")
    proposal = correction_proposal(current="CNY 52,077,455.23", replacement="CNY 52,077,455.28")
    updated = apply_corrections(doc, [proposal])
    assert first_span(updated).current_text == "CNY 52,077,455.23"
    assert "critical_field_correction_rejected" in issue_types(updated)
```

- [ ] **Step 2: 定义 reasoner 合同**

```python
class CorrectionProposal(BaseModel):
    span_id: str
    original_text: str
    replacement_text: str
    reason: str
    confidence: float = Field(ge=0, le=1)

class TextReasoner(ABC):
    @abstractmethod
    def propose(self, document: Document) -> list[CorrectionProposal]:
        raise NotImplementedError
```

- [ ] **Step 3: 实现 OpenAI-compatible 文本接口和保守应用器**

只发送 span ID、必要上下文和低置信文本，不发送整份页面图片。响应必须通过 `CorrectionProposal` 校验；`original_text` 与当前 span 不一致时拒绝；关键字段默认拒绝模型改值；所有采纳或拒绝都写 modification/issue。

- [ ] **Step 4: 接入 pipeline 检查点**

`reasoning_enabled=False` 时标记 reasoning stage 为 skipped；失败时记录 issue 并继续 DOCX；成功时写回 `document.json`。不得因 reasoner 失败重新解析 PDF。

- [ ] **Step 5: 运行测试和条件提交**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_text_reasoner.py tests/test_critical_fields.py tests/test_pipeline_resume.py -v`  
Expected: PASS。

```powershell
git add src/greatocr/reasoning src/greatocr/pipeline.py tests/test_text_reasoner.py
git commit -m "feat: add optional conservative text reasoner"
```

### Task 6: 敏感文件与失败切换策略

**Files:**
- Create: `src/greatocr/providers/fallback.py`
- Modify: `src/greatocr/security.py`
- Modify: `src/greatocr/task/manifest.py`
- Create: `tests/test_provider_fallback.py`
- Modify: `tests/test_security.py`

- [ ] **Step 1: 写策略测试**

```python
def test_sensitive_auto_fallback_uses_only_preapproved_profiles():
    policy = FallbackPolicy(mode="auto", approved_profile_ids=["private-a"])
    assert choose_fallback(policy, [public_b(), private_a()]).profile_id == "private-a"

def test_ask_mode_never_sends_without_user_choice():
    with pytest.raises(FallbackChoiceRequired):
        choose_fallback(FallbackPolicy(mode="ask"), [mineru_profile()])
```

- [ ] **Step 2: 实现三种模式**

```python
class FallbackPolicy(BaseModel):
    mode: Literal["stop", "ask", "auto"] = "ask"
    approved_profile_ids: list[str] = Field(default_factory=list)
```

`auto` 仅在 profile 已批准且能力满足时返回；`ask` 只产生候选列表，不调用 provider；敏感任务的 manifest 记录任务级确认时间和已批准 profile IDs。

- [ ] **Step 3: 确保只重试失败页**

为 pipeline 增加 `failed_original_pages`，fallback 输入只能由该集合生成子 PDF；新增 provider 调用计数断言。

- [ ] **Step 4: 运行安全回归**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_provider_fallback.py tests/test_security.py tests/test_pipeline_resume.py -v`  
Expected: PASS。

- [ ] **Step 5: 条件提交**

```powershell
git add src/greatocr/providers/fallback.py src/greatocr/security.py src/greatocr/task/manifest.py tests/test_provider_fallback.py tests/test_security.py
git commit -m "feat: add approved provider fallback policies"
```

### Task 7: 页面返工、重新拼合和结果版本

**Files:**
- Create: `src/greatocr/task/versions.py`
- Create: `tests/test_result_versions.py`
- Modify: `src/greatocr/rework.py`
- Modify: `tests/test_rework.py`

- [ ] **Step 1: 写版本和页面替换测试**

```python
def test_rework_replaces_failed_page_and_keeps_other_ids(tmp_path):
    before = make_partial_task(tmp_path)
    after = rework_pages(before.task_dir, [3], successful_parser())
    assert after.pages[2].status == "succeeded"
    assert after.pages[0].blocks[0].block_id == before.document.pages[0].blocks[0].block_id

def test_new_result_version_preserves_previous_file(tmp_path):
    v1 = publish_result_version(tmp_path, source_docx(tmp_path, "one"))
    v2 = publish_result_version(tmp_path, source_docx(tmp_path, "two"))
    assert v1.name == "result-v1.docx"
    assert v2.name == "result-v2.docx"
    assert (tmp_path / "result.docx").read_bytes() == v2.read_bytes()
```

- [ ] **Step 2: 实现版本发布器**

```python
def publish_result_version(task_dir: Path, generated: Path) -> Path:
    existing = sorted(task_dir.glob("result-v*.docx"))
    versioned = task_dir / f"result-v{len(existing) + 1}.docx"
    shutil.copy2(generated, versioned)
    shutil.copy2(versioned, task_dir / "result.docx")
    return versioned
```

- [ ] **Step 3: 重构 rework 输出**

返工只替换指定原始页；重写 `document.json` 和质量报告；先生成临时 DOCX，验证后调用 version publisher。失败时不覆盖现有 `result.docx`。

- [ ] **Step 4: 运行返工回归**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_rework.py tests/test_result_versions.py tests/test_pipeline_resume.py -v`  
Expected: PASS。

- [ ] **Step 5: 阶段全量验证和条件提交**

Run: `./.venv/Scripts/python.exe -m pytest -v`  
Expected: PASS。

```powershell
git add src/greatocr/rework.py src/greatocr/task/versions.py tests/test_rework.py tests/test_result_versions.py
git commit -m "feat: recompose versioned documents after page rework"
```
