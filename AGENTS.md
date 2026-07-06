# AGENTS.md

面向在 GreatOCR 项目中工作的 AI Agent / 协作者的重要约定。

## 启动方式

- **Release 用户**：`install.bat`（仅首次）→ `start.bat`（每次）
- **开发者 / 演示**：`python scripts/demo.py`（需先完成 `install.bat`）

`scripts/demo.py` 是开发 / 演示用启动器，会生成共享 session token 并同时启动后端
（`.venv/Scripts/python.exe scripts/serve.py`，绑定 `127.0.0.1:8399`）与前端
（`frontend/node_modules/vite/bin/vite.js`，端口 `5173`），将同一个 token 分别注入
`GREATOCR_SESSION_TOKEN` 与 `VITE_GREAT_OCR_TOKEN`。

## 修改启动 / 流程时必须同步 demo.py

如果任务影响以下任意一项，必须检查并**必要时**更新 `scripts/demo.py`：

- 启动流程（后端 / 前端的启动命令或参数）
- 前端路由（会影响手动测试时访问的页面）
- API（请求地址、代理、鉴权方式，尤其是 `GREATOCR_SESSION_TOKEN` / `VITE_GREAT_OCR_TOKEN` 的传递）
- 任务流程（OCR 任务生命周期、状态、输出）
- Demo 流程（开发者手动测试路径，依赖 `demo.py` 正确启动前后端）

`scripts/demo.py` 仅使用标准库，不依赖 `.venv` 中的任何包；修改时保持其可独立运行。

## 不要提交的内容

- `.venv`
- `node_modules`
- `data`
- API Key（含 `MinerU API key.txt` 与 `credentials.json`）
