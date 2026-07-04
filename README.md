# GreatOCR

GreatOCR 是一个面向 Windows 的本地 OCR 文档重建工具，目标是把 PDF 预检、选页、OCR、结构化映射、DOCX 重建和质量报告整合成可稳定使用的桌面化工作流。

当前发布版本：`v2.3.0`

## 主要功能

- PDF 预检：页数、加密状态、页面类型识别
- OCR 任务流：上传文件、选定页码范围、启动任务、查看状态
- Provider 管理：内置 `fake-default` 离线测试链路，支持配置 MinerU
- 结果输出：生成 `result.docx`，可选生成 `quality-report.docx`
- 任务中心：结果查看、下载、打开输出目录、删除记录、批量删除
- 设置中心：Provider 配置、连接测试、常用 OCR/输出偏好设置
- 安全控制：敏感文件模式、Provider 使用约束、凭证本地保存

## Quick Start

### 1. 安装后端依赖

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

### 2. 启动后端

```powershell
.\.venv\Scripts\python.exe scripts\serve.py
```

后端默认启动在 `http://127.0.0.1:8399`。

首次启动会自动完成：

- 创建本地数据目录和 SQLite 数据库
- 写入 `fake-default` provider
- 初始化默认偏好设置

### 3. 启动前端

```powershell
cd frontend
npx pnpm install
npx pnpm dev
```

前端默认启动在 `http://127.0.0.1:5173`。

### 4. 开始使用

- 打开浏览器访问 `http://127.0.0.1:5173`
- 进入“新建任务”上传 PDF
- 选择 `fake-default` 可直接体验完整离线流程
- 如需真实 OCR，可在“设置”中配置 MinerU

## Windows MVP 快速体验（推荐）

从 V2.3 开始，GreatOCR 提供一键安装与启动脚本，无需手动配置。

### 1. 安装

双击 `install.bat`，脚本会自动完成：

- 检查 Python 环境
- 创建 Python 虚拟环境（`.venv`）
- 安装后端依赖
- **自动检测 Node.js**（搜索 PATH 及常见安装位置：nvm / fnm / scoop / volta / 标准安装目录）
- 安装前端依赖

> 如果系统未安装 Python 或 Node.js，脚本会给出清晰提示并引导下载安装。

### 2. 启动

双击 `start.bat`，脚本会自动：

- 启动后端服务（`http://127.0.0.1:8399`）
- 启动前端服务（`http://127.0.0.1:5173`）
- 自动打开浏览器

关闭方式：关闭前端命令行窗口即可。后端窗口可能需要手动关闭。

### 3. 首次使用配置 API Key

- 在浏览器中打开 `http://127.0.0.1:5173`
- 进入 **设置** 页面
- 选择 Provider 并输入 API Key
- 点击 **测试连接** 验证
- 创建任务开始使用

> 使用 `fake-default` Provider 无需 API Key，可直接体验离线 OCR 流程。

### 常见问题

#### 没有 Python

1. 访问 [python.org](https://www.python.org/downloads/) 下载 Python 3.11+
2. 安装时勾选 **"Add Python to PATH"**
3. 重新运行 `install.bat`

#### 没有 Node.js

1. 访问 [nodejs.org](https://nodejs.org/) 下载 Node.js 20+
2. 安装时保持默认选项（会自动添加到 PATH）
3. 重新运行 `install.bat`

> 脚本还会自动搜索以下安装方式：nvm、fnm、scoop、volta、WorkBuddy 托管版本。

#### 端口被占用

如果 8399 或 5173 端口被占用：

- 关闭占用端口的程序，或
- 修改后端/前端配置中的端口号，然后重新启动

#### 依赖安装失败

- 检查网络连接，中国大陆用户建议使用稳定网络
- `install.bat` 已配置清华 PyPI 镜像和 npmmirror 镜像
- 如果镜像源不稳定，可手动安装后再试

---

## 项目结构

- `src/`：核心引擎、CLI、FastAPI 后端
- `frontend/`：React + Vite 前端
- `scripts/`：启动与辅助脚本
- `tests/`：自动化测试
- `docs/`：项目文档与报告
- `releases/`：发布相关材料

## Roadmap

### V2.4

- Windows Packaging
- OCR 识别质量优化
- 版式恢复优化
- 多 Provider 管理能力增强
- Settings 重构
- 批量 OCR 与更多导出格式

## Known Limitations

- Windows MVP 脚本（install.bat / start.bat）依赖 Python 和 Node.js 环境，尚未打包为独立 EXE
- 独立打包版属于 V2.4 范围
- OCR 质量仍可能出现单词粘连、数字格式不一致等问题
- 复杂版式恢复仍有优化空间，尤其是未知块类型和分页漂移
- 印章/签字识别尚未实现
- 当前导出格式以 DOCX 和质量报告为主
