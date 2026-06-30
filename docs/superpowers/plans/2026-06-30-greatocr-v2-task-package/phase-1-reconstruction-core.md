# GreatOCR V2.1 Reconstruction Core Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复 V1 的页面方向、英文粘连、版面顺序、图片路径/尺寸和页眉页脚问题，建立可回归的统一文档模型 V2。

**Architecture:** 保留 provider → unified model → DOCX 的主链路，在 provider 边界标准化页面方向、坐标和资源；Word builder 只消费标准化模型。所有修复先用合成夹具建立失败测试，再做最小实现。

**Tech Stack:** Python 3.11+、pydantic、pypdf、PyMuPDF、Pillow、python-docx、pytest。

---

## 文件结构

- Modify: `pyproject.toml` — 增加图像/PDF 裁剪依赖。
- Modify: `src/greatocr/model/document.py` — V2 页面、资源、追踪和状态字段。
- Create: `src/greatocr/model/geometry.py` — 方向和归一化坐标。
- Create: `src/greatocr/model/text_cleanup.py` — 英文空格、断行和段落合并规则。
- Create: `src/greatocr/model/layout.py` — 基于坐标的阅读顺序和区域分类。
- Modify: `src/greatocr/providers/mineru_zip.py` — 保留资源相对路径和更丰富结构。
- Modify: `src/greatocr/model/mapper.py` — 标准化页面、坐标、文本和资源。
- Modify: `src/greatocr/docx/builder.py` — 分节、方向、页眉页脚和布局消费。
- Modify: `src/greatocr/docx/assets.py` — 相对路径解析和比例尺寸。
- Modify: `src/greatocr/validation/checks.py` — 方向、资源、粘连和页覆盖检查。
- Test: `tests/test_page_geometry.py`
- Test: `tests/test_text_cleanup.py`
- Test: `tests/test_layout_order.py`
- Modify: `tests/test_document_model.py`
- Modify: `tests/test_mineru_zip_mapper.py`
- Modify: `tests/test_docx_builder.py`
- Modify: `tests/test_docx_assets.py`
- Modify: `tests/test_validation_checks.py`

### Task 1: 建立 V2 模型兼容层

**Files:**
- Modify: `src/greatocr/model/document.py`
- Modify: `tests/test_document_model.py`

- [ ] **Step 1: 写失败测试，要求旧 JSON 仍可读取且 V2 字段有确定默认值**

```python
def test_v1_page_loads_with_v2_defaults():
    page = Page(
        page_id="page-0001", page_number=1, width=842, height=595,
        rotation=270, page_type="scanned", blocks=[]
    )
    assert page.original_page_number == 1
    assert page.task_page_number == 1
    assert page.status == "succeeded"
    assert page.effective_width == 595
    assert page.effective_height == 842
```

- [ ] **Step 2: 运行测试确认失败**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_document_model.py::test_v1_page_loads_with_v2_defaults -v`  
Expected: FAIL，缺少 V2 字段。

- [ ] **Step 3: 最小实现 V2 类型**

```python
PageStatus = Literal["pending", "succeeded", "partial", "failed"]

class ProviderTrace(BaseModel):
    provider_name: str
    model_name: str | None = None
    attempt: int = 1
    elapsed_ms: int | None = None

class Page(BaseModel):
    page_id: str
    page_number: int
    original_page_number: int | None = None
    task_page_number: int | None = None
    width: float
    height: float
    effective_width: float | None = None
    effective_height: float | None = None
    rotation: int
    page_type: PageType
    status: PageStatus = "succeeded"
    provider_traces: list[ProviderTrace] = Field(default_factory=list)
    blocks: list[Block] = Field(default_factory=list)
    issues: list[Issue] = Field(default_factory=list)

    @model_validator(mode="after")
    def fill_v2_defaults(self):
        self.original_page_number = self.original_page_number or self.page_number
        self.task_page_number = self.task_page_number or self.page_number
        rotated = self.rotation % 180 != 0
        self.effective_width = self.effective_width or (self.height if rotated else self.width)
        self.effective_height = self.effective_height or (self.width if rotated else self.height)
        return self
```

- [ ] **Step 4: 运行模型回归**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_document_model.py tests/test_mapper_fake.py -v`  
Expected: PASS。

- [ ] **Step 5: Git 检查与提交**

Run: `git rev-parse --is-inside-work-tree`。若为 true：

```powershell
git add src/greatocr/model/document.py tests/test_document_model.py
git commit -m "feat: add backward-compatible v2 document fields"
```

若不是仓库，禁止初始化，记录测试结果后继续。

### Task 2: 标准化页面方向和坐标

**Files:**
- Create: `src/greatocr/model/geometry.py`
- Create: `tests/test_page_geometry.py`
- Modify: `src/greatocr/model/mapper.py`

- [ ] **Step 1: 写方向与坐标失败测试**

```python
def test_rotation_270_swaps_effective_page_size():
    assert effective_page_size(842, 595, 270) == (595, 842)

def test_bbox_is_normalized_to_zero_one():
    assert normalize_bbox([84.2, 59.5, 421, 297.5], 842, 595) == pytest.approx(
        [0.1, 0.1, 0.5, 0.5]
    )
```

- [ ] **Step 2: 运行测试确认失败**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_page_geometry.py -v`  
Expected: FAIL，模块不存在。

- [ ] **Step 3: 实现纯函数并在 mapper 中调用**

```python
def effective_page_size(width: float, height: float, rotation: int) -> tuple[float, float]:
    return (height, width) if rotation % 180 else (width, height)

def normalize_bbox(bbox: list[float] | None, width: float, height: float):
    if bbox is None:
        return None
    x0, y0, x1, y1 = bbox
    return [x0 / width, y0 / height, x1 / width, y1 / height]
```

Mapper 必须给 `Page.effective_width/effective_height` 赋值，并把 provider bbox 转为归一化 bbox；原始 bbox 写入新增的 `source_bbox` 字段。

- [ ] **Step 4: 运行几何与 mapper 测试**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_page_geometry.py tests/test_mapper_fake.py tests/test_mineru_zip_mapper.py -v`  
Expected: PASS。

- [ ] **Step 5: 条件提交**

```powershell
git add src/greatocr/model/geometry.py src/greatocr/model/mapper.py tests/test_page_geometry.py
git commit -m "fix: normalize page orientation and coordinates"
```

仅在有效 Git 仓库中执行。

### Task 3: 修复 Word 分节、方向和页眉页脚

**Files:**
- Modify: `src/greatocr/docx/builder.py`
- Modify: `tests/test_docx_builder.py`

- [ ] **Step 1: 写失败测试**

```python
def test_rotated_source_generates_portrait_section(tmp_path):
    page = make_page(width=842, height=595, rotation=270)
    output = tmp_path / "portrait.docx"
    build_docx(make_document([page]), output)
    section = WordDocument(output).sections[0]
    assert section.page_height > section.page_width

def test_header_and_footer_use_word_parts(tmp_path):
    output = tmp_path / "header-footer.docx"
    build_docx(make_document_with_header_footer(), output)
    reopened = WordDocument(output)
    assert "Header text" in reopened.sections[0].header.paragraphs[0].text
    assert "Footer text" in reopened.sections[0].footer.paragraphs[0].text
```

- [ ] **Step 2: 运行测试确认 V1 行为失败**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_docx_builder.py -v`  
Expected: 新增测试 FAIL。

- [ ] **Step 3: 用每页 section 消费有效宽高**

```python
def configure_section(section, page):
    section.page_width = Pt(page.effective_width)
    section.page_height = Pt(page.effective_height)
    section.orientation = (
        WD_ORIENT.LANDSCAPE
        if page.effective_width > page.effective_height
        else WD_ORIENT.PORTRAIT
    )
```

第一页配置现有 section；后续页面使用 `word.add_section(WD_SECTION.NEW_PAGE)`。页眉页脚 block 写入 section.header/footer，并在内容不同的 section 断开 `is_linked_to_previous`。

- [ ] **Step 4: 运行 DOCX 回归**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_docx_builder.py tests/test_docx_openability.py -v`  
Expected: PASS。

- [ ] **Step 5: 条件提交**

```powershell
git add src/greatocr/docx/builder.py tests/test_docx_builder.py
git commit -m "fix: preserve page orientation and header footer sections"
```

### Task 4: 修复资源路径、定位和尺寸

**Files:**
- Modify: `pyproject.toml`
- Modify: `src/greatocr/model/document.py`
- Modify: `src/greatocr/providers/mineru_zip.py`
- Modify: `src/greatocr/docx/assets.py`
- Modify: `tests/test_mineru_zip_mapper.py`
- Modify: `tests/test_docx_assets.py`

- [ ] **Step 1: 增加依赖并安装到项目 `.venv`**

```toml
dependencies = [
  "httpx>=0.28", "pydantic>=2.8", "python-docx>=1.1", "pypdf>=5.0",
  "PyMuPDF>=1.24", "Pillow>=10.4"
]
```

Run: `./.venv/Scripts/python.exe -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -e ".[dev]"`。

- [ ] **Step 2: 写失败测试，移动任务目录后图片仍可插入**

```python
def test_relative_asset_survives_task_directory_move(tmp_path):
    task = create_task_with_relative_image(tmp_path / "task-a")
    moved = tmp_path / "task-b"
    task.rename(moved)
    result = build_docx(load_document(moved), moved / "result.docx", task_dir=moved)
    assert not [issue for issue in result.issues if issue.issue_type == "asset_missing"]
```

- [ ] **Step 3: 实现相对资源契约**

`Asset.path` 保存 `intermediates/assets/images/<hash>.<ext>`；新增 `content_fingerprint`。`add_image_asset` 接收 `task_dir`，使用 `(task_dir / asset.path).resolve()`，并验证结果仍位于 task_dir 内。

图片宽度计算：

```python
page_fraction = max(0.05, min(1.0, asset.bbox[2] - asset.bbox[0]))
width_inches = min(usable_width_inches, usable_width_inches * page_fraction)
word.add_picture(str(asset_path), width=Inches(width_inches))
```

- [ ] **Step 4: 运行资源回归**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_mineru_zip_mapper.py tests/test_docx_assets.py -v`  
Expected: PASS，测试 JSON 不包含工作区绝对路径。

- [ ] **Step 5: 条件提交**

```powershell
git add pyproject.toml src/greatocr/model/document.py src/greatocr/providers/mineru_zip.py src/greatocr/docx/assets.py tests/test_mineru_zip_mapper.py tests/test_docx_assets.py
git commit -m "fix: make document assets portable and proportionate"
```

### Task 5: 英文空格、断行和阅读顺序

**Files:**
- Create: `src/greatocr/model/text_cleanup.py`
- Create: `src/greatocr/model/layout.py`
- Create: `tests/test_text_cleanup.py`
- Create: `tests/test_layout_order.py`
- Modify: `src/greatocr/model/mapper.py`

- [ ] **Step 1: 写保守规则测试**

```python
@pytest.mark.parametrize((left, right, expected), [
    ("Board", "resolution", "Board resolution"),
    ("inter-", "national", "international"),
    ("人民币", "52,077", "人民币52,077"),
    ("CNY", "52,077", "CNY 52,077"),
])
def test_join_line_fragments(left, right, expected):
    assert join_line_fragments(left, right) == expected

def test_two_column_blocks_read_left_column_before_right():
    ordered = order_blocks(two_column_blocks())
    assert [b.block_id for b in ordered] == ["left-1", "left-2", "right-1"]
```

- [ ] **Step 2: 确认测试失败**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_text_cleanup.py tests/test_layout_order.py -v`。

- [ ] **Step 3: 实现不改写事实值的纯规则**

```python
def join_line_fragments(left: str, right: str) -> str:
    if left.endswith("-") and left[-2:-1].isascii() and right[:1].islower():
        return left[:-1] + right
    if left[-1:].isascii() and right[:1].isascii() and left[-1:].isalnum() and right[:1].isalnum():
        return left + " " + right
    if left in {"CNY", "USD", "RMB"}:
        return left + " " + right
    return left + right
```

`order_blocks` 先按垂直重叠识别栏，再按栏 x 坐标、栏内 y 坐标排序。任何无法判定的布局保留 provider reading_order 并生成低严重度 issue。

- [ ] **Step 4: 运行 mapper 和 Markdown 回归**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_text_cleanup.py tests/test_layout_order.py tests/test_mapper_fake.py tests/test_markdown_export.py -v`  
Expected: PASS。

- [ ] **Step 5: 条件提交**

```powershell
git add src/greatocr/model/text_cleanup.py src/greatocr/model/layout.py src/greatocr/model/mapper.py tests/test_text_cleanup.py tests/test_layout_order.py
git commit -m "feat: add conservative text and layout normalization"
```

### Task 6: 扩展质量检查并完成阶段验收

**Files:**
- Modify: `src/greatocr/validation/checks.py`
- Modify: `tests/test_validation_checks.py`
- Create: `docs/acceptance/v2-1-reconstruction-report.md`

- [ ] **Step 1: 写方向、资源和粘连 issue 测试**

```python
def test_integrity_checks_report_orientation_asset_and_word_join_risks(tmp_path):
    issues = run_integrity_checks(document_with_known_v1_defects(tmp_path), preflight_rotated())
    assert {i.issue_type for i in issues} >= {
        "orientation_mismatch", "asset_missing", "possible_english_word_join"
    }
```

- [ ] **Step 2: 实现检查并运行全量测试**

Run: `./.venv/Scripts/python.exe -m pytest -v`  
Expected: 全部 PASS；若旧测试与 V2 合同冲突，只更新断言，不删除覆盖。

- [ ] **Step 3: 运行 fake provider 验收**

Run: `./.venv/Scripts/python.exe scripts/run_acceptance.py --provider fake`  
Expected: 生成 `result.docx`、`quality-report.docx` 和 V2 `document.json`。

- [ ] **Step 4: 写阶段报告**

报告必须记录：测试命令、通过数量、方向样本、资源迁移测试、仍未解决的真实 MinerU 质量问题，以及“未执行真实上传”的说明。

- [ ] **Step 5: 条件提交**

```powershell
git add src/greatocr/validation/checks.py tests/test_validation_checks.py docs/acceptance/v2-1-reconstruction-report.md
git commit -m "test: validate v2 reconstruction quality gates"
```
