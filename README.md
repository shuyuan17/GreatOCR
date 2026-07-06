# GreatOCR

GreatOCR 是一个面向 Windows 的本地 OCR 工作流工具，包含 FastAPI 后端与 React 前端。

当前发布版本：`v2.3.0`

## 主要功能

- PDF 预检、上传与 OCR 任务启动
- 任务中心查看状态、结果下载与输出目录打开
- Settings 中配置 MinerU Provider、API Key、Base URL 与连接测试
- 生成 `result.docx`，可选生成 `quality-report.docx`
- 本地偏好设置持久化保存

## Windows Release 使用流程

1. 安装 Python 3.11+，并勾选 **Add Python to PATH**
2. 安装 Node.js LTS，并确保 npm 可用
3. 双击 `install.bat`（仅首次）
4. 双击 `start.bat`（以后每次）
5. 浏览器自动打开后进入 **Settings**
6. 填写 `MinerU API Key`
7. 按需填写 `Base URL`
8. 点击 **测试连接**
9. 保存配置后开始 OCR

## install.bat（仅首次运行）

`install.bat` 会自动完成：

- 检查 Python
- 检查 Node.js
- 检查 npm
- 创建 `.venv`
- 安装 Python 依赖
- 安装前端依赖
- 安装 pnpm（如缺失）
- 写入安装完成标记

首次安装完成后，不需要再次安装依赖。

## start.bat（后续每次运行）

`start.bat` 只负责：

- 检查是否已完成安装
- 启动后端服务 `http://127.0.0.1:8399`
- 启动前端服务 `http://localhost:5173`
- 自动打开浏览器

`start.bat` 不会：

- 安装依赖
- 下载 pnpm
- 重新安装 `node_modules`
- 询问开发工具确认

## Provider 与 API Key

- Release 默认不显示 `Fake Provider`
- 首次启动会自动创建 `mineru-default`
- API Key 不会写入 Git
- API Key 不会进入 Release ZIP
- API Key 优先保存在系统 keyring
- 如果系统 keyring 不可用，API Key 会保存在 `%LOCALAPPDATA%\GreatOCR\credentials.json`

## 常见问题

### 没有 Python

1. 前往 [python.org](https://www.python.org/downloads/)
2. 安装 Python 3.11+
3. 勾选 **Add Python to PATH**
4. 重新运行 `install.bat`

### 没有 Node.js

1. 前往 [nodejs.org](https://nodejs.org/)
2. 安装 Node.js LTS
3. 重新运行 `install.bat`

### 端口被占用

如果 `8399` 或 `5173` 已被占用，请关闭占用程序后重新运行 `start.bat`。

### 依赖安装失败

- 检查网络连接
- 重新运行 `install.bat`
- 如公司网络有限制，请允许常见 Python / npm 包源访问

## 项目结构

- `src/`：后端与核心逻辑
- `frontend/`：React + Vite 前端
- `scripts/`：安装、启动与辅助脚本
- `tests/`：自动化测试
- `docs/`：项目文档

## Known Limitations

- 当前仍依赖本机已安装的 Python 和 Node.js
- 当前仍是本地 Web 版，不是独立 EXE
- Windows 独立打包属于后续版本范围
