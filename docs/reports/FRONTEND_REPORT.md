# FRONTEND_REPORT — V2.3 Task 5 前端应用壳

- **工作树**: `D:\codeprojects\codex-workspace\GreatOCR\.worktrees\v2-3-local-web-app`
- **完成时间**: 2026-07-01 21:10 (GMT+8)
- **涉及文件**: 3 个新建, 1 个修改, 2 个新增配置文件

---

## 1. 修改了哪些文件

### 新建文件

| 文件 | 说明 |
|------|------|
| `frontend/src/api.ts` | API 客户端，导出 `apiFetch()`。自动在请求头注入 `X-GreatOCR-Token` 并添加 `/api` 前缀，且不修改调用者的 headers 对象。类型声明 `window.__GREAT_OCR_TOKEN__` 也在此处定义。 |
| `frontend/src/App.tsx` | 主应用壳组件，导出 `App`。包含：顶部导航栏（首页/任务中心/新建任务/设置）、后端健康检查状态徽章（`/api/health`）、React Router 路由和占位页面。 |
| `frontend/src/main.tsx` | 应用入口。读取 `VITE_GREAT_OCR_TOKEN` 环境变量作为 session token（取自 `.env.development`），若未设置则自动生成随机 hex token 并在控制台打印。用 `BrowserRouter` 包裹 `<App />` 后挂载到 DOM。 |
| `frontend/src/vite-env.d.ts` | Vite 类型声明，包含 `ImportMetaEnv`（`VITE_GREAT_OCR_TOKEN`）和 `Window.__GREAT_OCR_TOKEN__` 的类型。 |
| `frontend/.env.development` | 开发环境变量，预设 `VITE_GREAT_OCR_TOKEN=greatocr-dev-token-2026`。 |

### 修改文件

| 文件 | 修改内容 |
|------|----------|
| `frontend/vite.config.ts` | 添加 `server.proxy` 配置 `/api → http://127.0.0.1:8399`，使开发时前端请求经过 Vite 代理转发到后端，避免 CORS 问题。同时设置 `server.port: 5173`。 |

### 未被修改的文件（保持原样）

- `frontend/package.json` — 原有依赖（React 18、react-router-dom 6、vite 6、vitest）完全满足需求，未改动
- `frontend/tsconfig.json` / `tsconfig.app.json` / `tsconfig.node.json` — 已有配置正确
- `frontend/index.html` — 模板中引用的 `/src/main.tsx` 现已存在，无需修改
- `frontend/src/api.test.ts` — 测试用例原样保留，全部通过
- `frontend/src/App.test.tsx` — 测试用例原样保留，全部通过
- 后端代码 — 未修改任何 Python 文件

---

## 2. 如何启动前端

### 前置条件

确保后端先在 `127.0.0.1:8399` 启动：

```powershell
# 在 V2.3 工作树根目录
.\.venv\Scripts\python.exe -c "
from greatocr.app.main import create_app
import uvicorn
app = create_app(
    session_token='greatocr-dev-token-2026',
    allowed_origin='http://127.0.0.1:5173'
)
uvicorn.run(app, host='127.0.0.1', port=8399)
"
```

> **注意**: `session_token` 必须与 `.env.development` 中的 `VITE_GREAT_OCR_TOKEN` 值一致。

### 启动前端开发服务器

```powershell
cd .\frontend\
node_modules\.bin\vite.CMD
```

或者使用 pnpm（需先全局安装 pnpm）：

```powershell
cd .\frontend\
pnpm dev
```

前端默认在 `http://127.0.0.1:5173` 启动。

---

## 3. 如何验证 /api/health

### 方式一：通过浏览器

1. 启动后端（见上文）
2. 启动前端
3. 打开 `http://127.0.0.1:5173`
4. 页面顶部导航栏右侧会显示后端连接状态：

| 状态 | 显示 | 含义 |
|------|------|------|
| 加载中 | 🔄 正在连接后端… | 正在发送 health check 请求 |
| 已连接 | ✅ 后端已连接 | `/api/health` 返回 `{"status":"ok"}` |
| 错误 | ❌ 无法连接后端 / 后端错误 (status) | 后端未启动或 token 不匹配 |

### 方式二：通过测试

```powershell
cd .\frontend\
node_modules\.bin\vitest.CMD run
```

现有 2 个测试文件共 2 个测试用例全部通过：

```
 ✓ src/api.test.ts (1 test) — 验证 apiFetch 自动注入 token
 ✓ src/App.test.tsx (1 test) — 验证导航文本渲染
```

### 方式三：通过 curl（后端运行中）

```powershell
# 健康检查（需正确 token）
curl -s -H "X-GreatOCR-Token: greatocr-dev-token-2026" http://127.0.0.1:5173/api/health
# 预期: {"status":"ok"}

# 错误 token
curl -s -H "X-GreatOCR-Token: wrong-token" http://127.0.0.1:5173/api/health
# 预期: {"detail":{"code":"INVALID_SESSION_TOKEN"}}
```

---

## 4. 还有哪些未完成

### Task 5 范围内的已知注意事项

- **开发启动流程尚不完整**：目前缺少后端的 CLI `serve` 子命令，用户需要手动编写内联 Python 脚本来启动 FastAPI。这属于 V2.3 Task 7（前后端集成）或 V2.4（便携打包）的计划范围。
- **前端测试覆盖有限**：仅有 2 个测试（api token 注入、导航渲染）。健康检查组件的 UI 测试（不同状态下的渲染）尚未覆盖。

### V2.3 Task 6 待实现（不在本次范围内）

- **任务中心页面** (`TaskCenter.tsx`) — 显示任务列表和管理任务
- **新建任务向导** (`NewTaskWizard.tsx`) — 完整的多步骤新建任务流程
- **任务详情页面** (`TaskDetail.tsx`) — 查看单个任务的进度和结果
- **设置页面** (`Settings.tsx`) — Provider 配置、安全设置等
- 上述页面的导航链接已在 `App.tsx` 中预留，目前显示占位文字

### V2.3 Task 7 待实现（不在本次范围内）

- 前端构建产物（`vite build`）接入 FastAPI 静态文件托管
- 前后端端到端集成验收
- 生成 `v2-3-local-app-report.md`

### V2.4 待实现（不在本次范围内）

- PyInstaller 便携打包
- 干净环境验证
- 免预装 Python/Node 的桌面交付

---

## 5. 架构示意图

```
浏览器 (http://127.0.0.1:5173)
    │
    ├── index.html
    │   └── /src/main.tsx
    │       ├── BrowserRouter
    │       │   └── <App />
    │       │       ├── Header: 导航 + <HealthBadge>
    │       │       │   └── HealthBadge ──→ apiFetch("/health")
    │       │       └── Routes: 首页 / 任务中心 / 新建任务 / 设置
    │       └── window.__GREAT_OCR_TOKEN__ (从环境变量读取)
    │
    └── Vite Proxy (/api/* → http://127.0.0.1:8399/*)
            │
            ▼
    FastAPI Backend (127.0.0.1:8399)
        └── GET /api/health → {"status":"ok"}
        └── GET /api/tasks → ...
        └── POST /api/providers → ...
```

`HealthBadge` 组件在挂载时调用 `apiFetch("/health")`，根据响应结果显示✅/❌状态，实现"页面能调用 /api/health 并显示后端连接状态"的目标。
