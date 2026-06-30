# GreatOCR V2.3 Local Web Application Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建立只在本机运行的 FastAPI + React 图形界面，覆盖任务创建、选页、模型设置、敏感确认、串行队列、历史和结果访问。

**Architecture:** FastAPI 负责文件、任务、凭据、队列和 pipeline 编排；React 只通过带临时令牌的本机 API 交互。SQLite 保存非敏感元数据，API Key 通过 Windows 当前用户凭据存储读取。

**Tech Stack:** FastAPI、uvicorn、pydantic、SQLite、keyring、React、TypeScript、Vite、pytest、Vitest、Playwright（开发验收）。

---

## 文件结构

- Modify: `pyproject.toml`
- Create: `src/greatocr/app/main.py`
- Create: `src/greatocr/app/auth.py`
- Create: `src/greatocr/app/db.py`
- Create: `src/greatocr/app/schemas.py`
- Create: `src/greatocr/app/routes/tasks.py`
- Create: `src/greatocr/app/routes/providers.py`
- Create: `src/greatocr/app/services/credentials.py`
- Create: `src/greatocr/app/services/task_service.py`
- Create: `src/greatocr/app/services/worker.py`
- Create: `src/greatocr/app/services/thumbnails.py`
- Create: `frontend/package.json`
- Create: `frontend/src/api.ts`
- Create: `frontend/src/App.tsx`
- Create: `frontend/src/pages/TaskCenter.tsx`
- Create: `frontend/src/pages/NewTaskWizard.tsx`
- Create: `frontend/src/pages/TaskDetail.tsx`
- Create: `frontend/src/pages/Settings.tsx`
- Test: `tests/app/test_auth.py`
- Test: `tests/app/test_db.py`
- Test: `tests/app/test_credentials.py`
- Test: `tests/app/test_task_api.py`
- Test: `tests/app/test_worker.py`
- Test: `tests/app/test_thumbnails.py`
- Test: `frontend/src/*.test.tsx`

### Task 1: FastAPI 壳、临时令牌和回环限制

**Files:**
- Modify: `pyproject.toml`
- Create: `src/greatocr/app/main.py`
- Create: `src/greatocr/app/auth.py`
- Create: `tests/app/test_auth.py`

- [ ] **Step 1: 增加本机应用依赖**

```toml
dependencies = [
  "httpx>=0.28", "pydantic>=2.8", "python-docx>=1.1", "pypdf>=5.0",
  "PyMuPDF>=1.24", "Pillow>=10.4", "fastapi>=0.115",
  "uvicorn>=0.34", "keyring>=25.6"
]
```

使用国内镜像安装到 `.venv`。

- [ ] **Step 2: 写认证失败测试**

```python
def test_api_rejects_missing_or_wrong_session_token(client):
    assert client.get("/api/health").status_code == 401
    assert client.get("/api/health", headers={"X-GreatOCR-Token": "wrong"}).status_code == 401

def test_api_accepts_current_session_token(client, session_token):
    response = client.get("/api/health", headers={"X-GreatOCR-Token": session_token})
    assert response.json() == {"status": "ok"}
```

- [ ] **Step 3: 实现 app factory**

```python
def create_app(session_token: str, allowed_origin: str) -> FastAPI:
    app = FastAPI(docs_url=None, redoc_url=None)
    app.state.session_token = session_token
    app.state.allowed_origin = allowed_origin
    app.include_router(api_router, prefix="/api", dependencies=[Depends(require_local_session)])
    return app
```

`require_local_session` 同时检查 header token 和 Origin；启动器只能绑定 `127.0.0.1`，不能接受 `0.0.0.0` 配置。

- [ ] **Step 4: 运行测试**

Run: `./.venv/Scripts/python.exe -m pytest tests/app/test_auth.py -v`  
Expected: PASS。

- [ ] **Step 5: 条件提交**

```powershell
git add pyproject.toml src/greatocr/app/main.py src/greatocr/app/auth.py tests/app/test_auth.py
git commit -m "feat: add authenticated local FastAPI shell"
```

### Task 2: SQLite 任务历史与敏感字段最小化

**Files:**
- Create: `src/greatocr/app/db.py`
- Create: `src/greatocr/app/schemas.py`
- Create: `tests/app/test_db.py`

- [ ] **Step 1: 写数据库测试**

```python
def test_sensitive_task_uses_anonymous_display_name(db):
    task = db.create_task(NewTask(source_path="C:/secret/client.pdf", sensitive=True, pages=[2]))
    row = db.get_task(task.task_id)
    assert row.display_name.startswith("敏感任务 ")
    assert "client.pdf" not in db.raw_database_text()

def test_database_never_stores_api_key(db):
    db.save_provider(provider_with_secret("top-secret"))
    assert "top-secret" not in db.raw_database_text()
```

- [ ] **Step 2: 定义任务 DTO**

```python
class TaskRecord(BaseModel):
    task_id: str
    display_name: str
    source_path: str | None
    sensitive: bool
    selected_pages: list[int]
    provider_profile_id: str
    status: Literal["pending", "running", "paused", "succeeded", "partial", "failed", "cancelled"]
    output_dir: str
    quality_rating: str | None = None
```

- [ ] **Step 3: 实现显式 schema migration**

SQLite 启动时创建 `schema_version`、`tasks` 和 `provider_profiles`。页码和批准的 fallback IDs 使用 JSON 文本；API Key 字段不得存在。敏感任务默认 `source_path=NULL`，实际路径只在任务运行上下文或受控任务 manifest 中使用。

- [ ] **Step 4: 运行测试和结构检查**

Run: `./.venv/Scripts/python.exe -m pytest tests/app/test_db.py tests/test_no_secret_leakage.py -v`。

- [ ] **Step 5: 条件提交**

```powershell
git add src/greatocr/app/db.py src/greatocr/app/schemas.py tests/app/test_db.py
git commit -m "feat: store local task history without secrets"
```

### Task 3: Windows 当前用户凭据服务

**Files:**
- Create: `src/greatocr/app/services/credentials.py`
- Create: `tests/app/test_credentials.py`
- Create: `src/greatocr/app/routes/providers.py`

- [ ] **Step 1: 写 fake keyring 测试**

```python
def test_credential_service_masks_and_deletes_secret(fake_keyring):
    service = CredentialService(fake_keyring, service_name="GreatOCR")
    service.set("mineru-default", "abcdef123456")
    assert service.status("mineru-default").masked == "********3456"
    service.delete("mineru-default")
    assert service.status("mineru-default").configured is False
```

- [ ] **Step 2: 实现只返回状态的接口**

```python
class CredentialStatus(BaseModel):
    configured: bool
    masked: str | None = None

class CredentialNotConfigured(RuntimeError):
    pass

class CredentialService:
    def __init__(self, backend, service_name: str = "GreatOCR"):
        self.backend = backend
        self.service_name = service_name

    def set(self, profile_id: str, secret: str) -> None:
        if not secret.strip():
            raise ValueError("API key cannot be empty")
        self.backend.set_password(self.service_name, profile_id, secret)

    def resolve(self, profile_id: str) -> SecretStr:
        value = self.backend.get_password(self.service_name, profile_id)
        if value is None:
            raise CredentialNotConfigured(profile_id)
        return SecretStr(value)

    def status(self, profile_id: str) -> CredentialStatus:
        value = self.backend.get_password(self.service_name, profile_id)
        return CredentialStatus(
            configured=value is not None,
            masked=("********" + value[-4:]) if value else None,
        )

    def delete(self, profile_id: str) -> None:
        if self.backend.get_password(self.service_name, profile_id) is not None:
            self.backend.delete_password(self.service_name, profile_id)
```

GET provider API 只能返回 `CredentialStatus`；任何 pydantic DTO 不包含 secret 字段。连接测试在后端解析 secret，异常通过固定错误码返回。

- [ ] **Step 3: 添加 provider CRUD 和能力测试路由**

路由：`GET/POST/DELETE /api/providers`、`POST /api/providers/{id}/test-connection`、`POST /api/providers/{id}/test-capabilities`。删除 profile 前检查是否被 running task 使用。

- [ ] **Step 4: 运行凭据和路由测试**

Run: `./.venv/Scripts/python.exe -m pytest tests/app/test_credentials.py tests/app/test_task_api.py -v`。

- [ ] **Step 5: 条件提交**

```powershell
git add src/greatocr/app/services/credentials.py src/greatocr/app/routes/providers.py tests/app/test_credentials.py
git commit -m "feat: store provider keys in Windows user credentials"
```

### Task 4: 任务 API、敏感确认和串行 worker

**Files:**
- Create: `src/greatocr/app/services/task_service.py`
- Create: `src/greatocr/app/services/worker.py`
- Create: `src/greatocr/app/services/thumbnails.py`
- Create: `src/greatocr/app/routes/tasks.py`
- Create: `tests/app/test_task_api.py`
- Create: `tests/app/test_worker.py`
- Create: `tests/app/test_thumbnails.py`

- [ ] **Step 1: 写敏感任务确认测试**

```python
def test_sensitive_public_task_cannot_start_without_exact_confirmation(api):
    task = api.create_task(sensitive=True, provider="mineru-default")
    response = api.start(task.task_id, confirmation=None)
    assert response.status_code == 409
    assert response.json()["code"] == "SENSITIVE_CONFIRMATION_REQUIRED"
```

- [ ] **Step 2: 写单 worker 测试**

```python
def test_worker_runs_one_task_and_leaves_second_pending(worker, two_tasks):
    worker.tick()
    assert statuses(two_tasks) == ["running", "pending"]

def test_thumbnail_service_renders_only_requested_window(tmp_path):
    service = ThumbnailService(max_cached_pages=20)
    result = service.render(pdf_with_pages(tmp_path, 100), pages=range(41, 51))
    assert [item.page_number for item in result] == list(range(41, 51))
    assert all(item.path.exists() for item in result)
```

- [ ] **Step 3: 实现 API 状态机**

路由：创建、预检、缩略图、启动、暂停请求、取消、重试失败页、获取详情、列出版本、打开输出目录。`start` 校验选页、provider 能力、凭据、输出目录和敏感确认快照后才入队。缩略图服务按页窗惰性渲染，默认最多缓存 20 页；超长 PDF 不预生成全部页面。

Worker 每次只 claim 一个 pending task；阶段边界读取 pause/cancel flag；每个阶段后同步 manifest 和 SQLite。进程重启时把遗留 running 状态恢复为 paused，并提供继续按钮。

- [ ] **Step 4: 运行 API/worker 回归**

Run: `./.venv/Scripts/python.exe -m pytest tests/app/test_task_api.py tests/app/test_worker.py tests/app/test_thumbnails.py tests/test_pipeline_resume.py -v`。

- [ ] **Step 5: 条件提交**

```powershell
git add src/greatocr/app/services/task_service.py src/greatocr/app/services/worker.py src/greatocr/app/routes/tasks.py tests/app/test_task_api.py tests/app/test_worker.py
git commit -m "feat: add local task API and serial worker"
```

### Task 5: React 基础壳和 API 客户端

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/tsconfig.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/src/api.ts`
- Create: `frontend/src/App.tsx`
- Create: `frontend/src/App.test.tsx`

- [ ] **Step 1: 创建前端工程并在项目目录安装依赖**

`package.json` 固定 React、TypeScript、Vite、Vitest、Testing Library 版本；生成 lockfile。依赖只写入 `frontend/node_modules`。

- [ ] **Step 2: 写导航和 token header 测试**

```tsx
it("renders the four primary pages", () => {
  render(<App />)
  expect(screen.getByText("任务中心")).toBeInTheDocument()
  expect(screen.getByText("新建任务")).toBeInTheDocument()
  expect(screen.getByText("设置")).toBeInTheDocument()
})
```

```ts
export async function apiFetch(path: string, init: RequestInit = {}) {
  const headers = new Headers(init.headers)
  headers.set("X-GreatOCR-Token", window.__GREAT_OCR_TOKEN__)
  const requestInit = Object.assign({}, init, {headers})
  return fetch(`/api${path}`, requestInit)
}
```

- [ ] **Step 3: 实现路由和错误边界**

App 只包含四个顶层页面；所有错误显示后端返回的用户消息和错误码，不显示 traceback、密钥或完整 provider 响应。

- [ ] **Step 4: 运行前端测试**

Run: `cd frontend; npm test -- --run`  
Expected: PASS。

- [ ] **Step 5: 条件提交**

```powershell
git add frontend
git commit -m "feat: scaffold GreatOCR local web UI"
```

### Task 6: 新建任务向导、任务中心、详情和设置

**Files:**
- Create: `frontend/src/pages/TaskCenter.tsx`
- Create: `frontend/src/pages/NewTaskWizard.tsx`
- Create: `frontend/src/pages/TaskDetail.tsx`
- Create: `frontend/src/pages/Settings.tsx`
- Create: `frontend/src/pages/pages.test.tsx`

- [ ] **Step 1: 写用户流程测试**

```tsx
it("requires a second confirmation for a sensitive public-provider task", async () => {
  render(<NewTaskWizard api={fakeApi} />)
  await selectPdf("sample.pdf")
  await enterPageRange("3, 8-10")
  await markSensitive()
  await selectProvider("MinerU")
  expect(screen.getByRole("button", {name: "开始处理"})).toBeDisabled()
  await confirmSensitiveDataFlow()
  expect(screen.getByRole("button", {name: "开始处理"})).toBeEnabled()
})
```

- [ ] **Step 2: 实现向导四步状态**

向导步骤必须与规格一致：文件/页面、安全/操作、解析方案、输出/确认。缩略图选择和页码表达式共享一个 `selectedPages` 状态；超长文档提供“不生成全部缩略图”。

- [ ] **Step 3: 实现其他页面**

任务中心显示队列分组；详情显示阶段和版本；设置显示 provider 能力、风险标签和密钥状态。翻译、总结、Excel 按钮必须 disabled 并显示“即将支持”，不得调用后端。

- [ ] **Step 4: 运行前端和后端端到端 fake 测试**

Run: `cd frontend; npm test -- --run`  
Run: `./.venv/Scripts/python.exe -m pytest tests/app tests/test_end_to_end_fake_provider.py -v`  
Expected: PASS。

- [ ] **Step 5: 条件提交**

```powershell
git add frontend/src/pages tests/app
git commit -m "feat: add GreatOCR task workflow pages"
```

### Task 7: Phase 3 集成验收

**Files:**
- Create: `docs/acceptance/v2-3-local-app-report.md`

- [ ] **Step 1: 构建前端并由 FastAPI 提供静态资源**

Run: `cd frontend; npm run build`。将 `frontend/dist` 作为构建输入；开发模式可由 Vite proxy 指向 FastAPI。

- [ ] **Step 2: 运行全量离线测试**

Run: `./.venv/Scripts/python.exe -m pytest -v`  
Run: `cd frontend; npm test -- --run`  
Expected: 全部 PASS。

- [ ] **Step 3: 人工 fake-provider 演练**

验证普通任务、敏感二次确认、页码范围、排队、暂停恢复、失败页重试、版本列表、密钥掩码和扩展入口禁用状态。

- [ ] **Step 4: 写验收报告和条件提交**

```powershell
git add docs/acceptance/v2-3-local-app-report.md
git commit -m "docs: record local web application acceptance"
```
