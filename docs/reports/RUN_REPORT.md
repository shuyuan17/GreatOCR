# RUN_REPORT — V2.3 Local Web App 后端巡检

- **工作树**: `D:\codeprojects\codex-workspace\GreatOCR\.worktrees\v2-3-local-web-app`
- **分支**: `codex/v2-3-local-web-app`
- **巡检时间**: 2026-07-01 20:44 (GMT+8)
- **巡检范围**: FastAPI 后端启动、`/api/health` 可访问性、`/api/tasks` 与 `/api/providers` 测试覆盖
- **限制**: 不修改业务代码，仅新增本报告文件

---

## 1. FastAPI 后端启动检查

### 1.1 依赖完整性

工作树内自带独立 venv (`.venv/`)，核心依赖均可正常导入：

| 依赖 | 版本 | 状态 |
|------|------|------|
| fastapi | 0.115.14 | OK |
| uvicorn | 0.49.0 | OK |
| pydantic | 2.13.4 | OK |
| httpx | — | OK |
| keyring | — | OK |
| pypdf | — | OK |
| PyMuPDF (fitz) | — | OK |
| Pillow (PIL) | — | OK |
| python-docx (docx) | — | OK |

### 1.2 应用工厂

后端入口为 `src/greatocr/app/main.py` 中的 `create_app()` 工厂函数。该函数接收 `session_token`、`allowed_origin` 以及可选的 `database`、`credential_service`、`provider_connection_tester`、`task_service` 依赖注入参数，返回配置好的 `FastAPI` 实例。

> 注意：当前 CLI (`src/greatocr/cli.py`) 仅提供 `doctor`、`convert`、`rework` 三个子命令，尚无 `serve` / `web` 子命令。这是 Phase 4（可移植发布）的计划内容，不影响后端本身的可用性。本次巡检通过内联 Python 脚本调用 `create_app()` + `uvicorn.run()` 完成启动验证。

### 1.3 实际启动验证

使用内联脚本在 `127.0.0.1:8399` 启动 uvicorn 服务：

```python
app = create_app(session_token='health-check-token', allowed_origin='http://127.0.0.1:4173')
uvicorn.run(app, host='127.0.0.1', port=8399)
```

**结果：服务启动成功，无报错，进程正常运行。**

安全约束验证（`validate_bind_host`）：
- 仅允许回环地址绑定（`127.0.0.1`、`localhost`、`::1`）
- 拒绝非回环地址（`0.0.0.0`、`::`、`192.168.1.5`）并抛出 `ValueError`

---

## 2. /api/health 可访问性检查

### 2.1 端点定义

- **路由**: `GET /api/health`（`main.py:17-19`）
- **鉴权**: 全局依赖 `require_local_session`，需通过 `X-GreatOCR-Token` 请求头传递会话令牌
- **来源校验**: 校验 `Origin` 请求头，仅允许 `create_app()` 中配置的 `allowed_origin`
- **响应**: `{"status": "ok"}`

### 2.2 实际 HTTP 验证

| 场景 | 请求 | 期望 | 实际 | 结果 |
|------|------|------|------|------|
| 无令牌 | `GET /api/health` | 401 | `401 {"detail":{"code":"INVALID_SESSION_TOKEN"}}` | PASS |
| 错误令牌 | `GET /api/health` + `X-GreatOCR-Token: wrong` | 401 | `401 {"detail":{"code":"INVALID_SESSION_TOKEN"}}` | PASS |
| 正确令牌 | `GET /api/health` + `X-GreatOCR-Token: health-check-token` | 200 | `200 {"status":"ok"}` | PASS |
| 跨域来源 | 正确令牌 + `Origin: https://attacker.example` | 403 | `403 {"detail":{"code":"ORIGIN_NOT_ALLOWED"}}` | PASS |

### 2.3 测试覆盖

`tests/app/test_auth.py` 共 9 个测试用例覆盖 health 端点及启动安全：

| 测试函数 | 覆盖内容 |
|----------|----------|
| `test_api_rejects_missing_or_wrong_session_token` | 无令牌 401、错误令牌 401 |
| `test_api_accepts_current_session_token` | 正确令牌 200 + `{"status":"ok"}` |
| `test_api_rejects_foreign_browser_origin` | 跨域来源 403 |
| `test_launcher_rejects_non_loopback_bind_hosts` (×3 参数化) | 拒绝非回环绑定地址 |
| `test_launcher_accepts_loopback_bind_hosts` (×3 参数化) | 允许回环绑定地址 |

---

## 3. /api/tasks 测试覆盖检查

### 3.1 端点清单

路由文件：`src/greatocr/app/routes/tasks.py`，前缀 `/api/tasks`

| 方法 | 路径 | 处理函数 | 功能 |
|------|------|----------|------|
| POST | `/api/tasks` | `create_task` | 创建任务 |
| GET | `/api/tasks` | `list_tasks` | 列出任务 |
| GET | `/api/tasks/{task_id}` | `get_task` | 获取任务详情 |
| POST | `/api/tasks/{task_id}/preflight` | `preflight_task` | PDF 预检 |
| GET | `/api/tasks/{task_id}/thumbnails` | `task_thumbnails` | 页面缩略图 |
| POST | `/api/tasks/{task_id}/start` | `start_task` | 启动任务（含敏感确认） |
| POST | `/api/tasks/{task_id}/pause` | `pause_task` | 暂停任务 |
| POST | `/api/tasks/{task_id}/cancel` | `cancel_task` | 取消任务 |
| POST | `/api/tasks/{task_id}/retry-failed-pages` | `retry_failed_pages` | 重试失败页 |
| GET | `/api/tasks/{task_id}/versions` | `task_versions` | 列出结果版本 |
| POST | `/api/tasks/{task_id}/open-output` | `open_task_output` | 打开输出目录 |

### 3.2 测试覆盖矩阵

测试文件：`tests/app/test_task_api.py`（4 个测试函数）

| 端点 | 覆盖测试 | 覆盖状态 |
|------|----------|----------|
| POST `/api/tasks` | `create_task` 辅助函数（4 个测试均使用） | 已覆盖 |
| GET `/api/tasks` | `test_task_list_and_detail_do_not_expose_sensitive_source_path` | 已覆盖 |
| GET `/api/tasks/{task_id}` | `test_task_list_and_detail_do_not_expose_sensitive_source_path` | 已覆盖 |
| POST `/{task_id}/preflight` | `test_task_preflight_and_thumbnail_window` | 已覆盖 |
| GET `/{task_id}/thumbnails` | `test_task_preflight_and_thumbnail_window`（含分页参数） | 已覆盖 |
| POST `/{task_id}/start` | `test_sensitive_public_task_cannot_start_without_exact_confirmation`、`test_task_controls_versions_and_open_output` | 已覆盖 |
| POST `/{task_id}/pause` | `test_task_controls_versions_and_open_output` | 已覆盖 |
| POST `/{task_id}/cancel` | `test_task_controls_versions_and_open_output` | 已覆盖 |
| POST `/{task_id}/retry-failed-pages` | `test_task_controls_versions_and_open_output` | 已覆盖 |
| GET `/{task_id}/versions` | `test_task_controls_versions_and_open_output` | 已覆盖 |
| POST `/{task_id}/open-output` | `test_task_controls_versions_and_open_output` | 已覆盖 |

**结论：11/11 端点全部有测试覆盖。**

测试场景亮点：
- 敏感文件启动需精确确认（文件名匹配），否则返回 409
- 敏感任务列表/详情不暴露源路径（`source_path` 返回 `null`）
- 缩略图分页窗口验证（`start` + `count`）
- 暂停 → checkpoint → 重试 → 版本列表 → 打开输出 → 取消 完整生命周期
- approval.json 中不含 API 密钥

---

## 4. /api/providers 测试覆盖检查

### 4.1 端点清单

路由文件：`src/greatocr/app/routes/providers.py`，前缀 `/api/providers`

| 方法 | 路径 | 处理函数 | 功能 |
|------|------|----------|------|
| GET | `/api/providers` | `list_providers` | 列出供应商 |
| POST | `/api/providers` | `save_provider` | 保存供应商（含密钥头） |
| DELETE | `/api/providers/{profile_id}` | `delete_provider` | 删除供应商 |
| POST | `/api/providers/{profile_id}/test-connection` | `test_connection` | 测试连接 |
| POST | `/api/providers/{profile_id}/test-capabilities` | `test_capabilities` | 测试能力 |

### 4.2 测试覆盖矩阵

测试文件：`tests/app/test_credentials.py`（5 个 API 测试 + 2 个凭据服务单元测试）

| 端点 | 覆盖测试 | 覆盖状态 |
|------|----------|----------|
| GET `/api/providers` | `test_provider_api_returns_masked_status_and_never_secret`、`test_provider_capability_test_and_delete` | 已覆盖 |
| POST `/api/providers` | 5 个 API 测试均使用（含 `X-GreatOCR-Provider-Key` 头注入密钥） | 已覆盖 |
| DELETE `/{profile_id}` | `test_provider_capability_test_and_delete`、`test_provider_delete_is_blocked_while_running_task_uses_it` | 已覆盖 |
| POST `/{profile_id}/test-connection` | `test_provider_connection_uses_resolved_secret_without_returning_it`、`test_provider_connection_failure_returns_fixed_error_code` | 已覆盖 |
| POST `/{profile_id}/test-capabilities` | `test_provider_capability_test_and_delete` | 已覆盖 |

**结论：5/5 端点全部有测试覆盖。**

测试场景亮点：
- 密钥掩码展示（`********1234`），永不返回明文
- 连接测试使用解析后的密钥但不回传
- 连接失败返回固定错误码 `PROVIDER_CONNECTION_FAILED`，不泄漏内部异常信息
- 删除被运行中任务引用的供应商返回 409 `PROVIDER_IN_USE`
- 删除后同时清理 keyring 中的密钥
- 数据库中不存储 API 密钥明文

### 4.3 实际端点验证（无服务注入场景）

启动时未注入 `database` / `credential_service`，端点返回 503：

| 端点 | 实际响应 |
|------|----------|
| `GET /api/tasks` | `503 {"detail":{"code":"TASK_SERVICE_UNAVAILABLE"}}` |
| `GET /api/providers` | `503 {"detail":{"code":"PROVIDER_SERVICE_UNAVAILABLE"}}` |

符合预期的优雅降级设计。

---

## 5. 全量测试运行结果

```
196 passed in 8.29s
```

其中 `tests/app/` 目录（后端 Web 应用层）31 个测试全部通过：

```
tests/app/test_auth.py ......................... 9 passed
tests/app/test_credentials.py ................... 7 passed
tests/app/test_db.py ........................... 4 passed
tests/app/test_task_api.py ..................... 4 passed
tests/app/test_thumbnails.py ................... 3 passed
tests/app/test_worker.py ....................... 4 passed
                              31 passed in 0.90s
```

---

## 6. 总结

| 检查项 | 结果 |
|--------|------|
| FastAPI 后端能否启动 | **通过** — `create_app()` 工厂正常，uvicorn 可在回环地址启动服务 |
| `/api/health` 是否可访问 | **通过** — 正确令牌返回 200 `{"status":"ok"}`；无/错令牌返回 401；跨域来源返回 403 |
| `/api/tasks` 测试覆盖 | **通过** — 11 个端点全部覆盖（4 个测试函数） |
| `/api/providers` 测试覆盖 | **通过** — 5 个端点全部覆盖（5 个 API 测试 + 2 个单元测试） |
| 全量测试套件 | **通过** — 196 passed, 0 failed |

**未发现阻塞性问题。后端 Web 应用层功能完整、测试覆盖充分、安全防护（会话令牌、来源校验、回环绑定、密钥掩码）均已实现且有测试守护。**
