# VALIDATION REPORT

- 工作目录: `D:\codeprojects\codex-workspace\GreatOCR\.worktrees\v2-3-local-web-app`
- 验证时间: 2026-07-02
- 当前分支: `codex/v2-3-local-web-app`
- QA 约束: 未修改任何业务代码

## 1. 拉取结果

- 已执行 `git pull --ff-only`
- 结果: `Already up to date.`

## 2. 启动依据

- `PROJECT_STATUS.md`
- `RUN_REPORT.md`
- `FRONTEND_REPORT.md`
- `releases/v1/README.md`

实际采用的启动方式与 `FRONTEND_REPORT.md` 一致：

- 后端: 通过 `create_app(...)` + `uvicorn.run(...)` 启动到 `127.0.0.1:8399`
- 前端: 启动 Vite 开发服务到 `127.0.0.1:5173`

说明:

- 本次 QA shell 环境默认 `PATH` 中没有 `node` / `npm`
- 因此按文档直接调用 `frontend\\node_modules\\.bin\\vite.cmd` 的首次尝试未成功常驻
- 改为显式使用工作区提供的 Node.js 运行时后，前端成功启动

## 3. 验证结果

### 3.1 后端是否可以启动

- 结果: 通过
- 监听地址: `127.0.0.1:8399`
- 启动日志:

```text
INFO:     Started server process [8984]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8399 (Press CTRL+C to quit)
```

- 日志文件:
  - `.qa-logs/backend.stdout.log`
  - `.qa-logs/backend.stderr.log`

### 3.2 前端是否可以启动

- 结果: 通过
- 监听地址: `127.0.0.1:5173`
- 首次按文档直接启动现象:
  - `node` 不在默认 `PATH`
  - `node -v` / `npm -v` 均返回 `CommandNotFoundException`
- 在当前 QA 环境中的可运行方式:
  - 使用工作区提供的 Node.js 运行时显式启动 `frontend/node_modules/vite/bin/vite.js`

### 3.3 前端是否能够访问 `/api/health`

- 结果: 通过

后端直连验证:

```json
{"StatusCode":200,"Content":"{\"status\":\"ok\"}"}
```

前端代理访问验证:

```json
{"StatusCode":200,"Content":"{\"status\":\"ok\"}"}
```

错误 token 验证:

```json
{"StatusCode":401,"Message":"远程服务器返回错误: (401) 未经授权。"}
```

结论:

- 前端 `http://127.0.0.1:5173/api/health` 已成功代理到后端
- 正确 token 返回 `200 {"status":"ok"}`
- 错误 token 返回 `401`

### 3.4 页面是否正常显示

- 结果: 通过
- 页面标题: `GreatOCR`
- 页面地址: `http://127.0.0.1:5173/`

应用内浏览器实际页面快照显示:

```text
- banner:
  - heading "GreatOCR" [level=1]
  - navigation:
    - link "首页"
    - link "任务中心"
    - link "新建任务"
    - link "设置"
  - generic: ✅ 后端已连接
- main:
  - heading "欢迎使用 GreatOCR" [level=2]
  - paragraph: 本地文档处理工具 — PDF 重建 · 图片增强 · 多语言翻译
```

页面 HTML 访问结果:

```json
{"StatusCode":200,"HasGreatOCR":true,"HasRootDiv":true}
```

## 4. 额外观察

- 浏览器控制台未见阻塞性错误
- 存在 2 条 React Router v7 future flag 警告，但不影响当前页面加载、导航渲染和 `/api/health` 连通性

## 5. 总结

本次 QA 验证结论:

- 后端可以启动: 通过
- 前端可以启动: 通过
- 前端可以访问 `/api/health`: 通过
- 页面可以正常显示: 通过

整体结论:

- 当前分支在本次 QA 环境中可成功启动前后端并完成基础联通验证
- 未修改任何业务代码
