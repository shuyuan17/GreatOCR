# GreatOCR V2.4 Portable Release Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 生成无需管理员权限、无需预装 Python/Node.js 的 Windows 10/11 GreatOCR 便携版，并完成安全、功能和真实样本发布验收。

**Architecture:** React 先构建为静态资源，随 FastAPI/Python 后端一起由 PyInstaller 打包；轻量 launcher 绑定随机回环端口、生成令牌并打开默认浏览器。发布物不包含源码密钥、测试样本、本地模型或 V1 输出。

**Tech Stack:** PyInstaller、Python、Vite、PowerShell、pytest、SHA-256、Windows 10/11。

---

## 文件结构

- Modify: `pyproject.toml`
- Create: `src/greatocr/app/launcher.py`
- Create: `packaging/greatocr.spec`
- Create: `packaging/build-portable.ps1`
- Create: `packaging/verify-portable.ps1`
- Create: `tests/app/test_launcher.py`
- Create: `tests/test_release_contents.py`
- Create: `docs/user-guide.md`
- Create: `docs/acceptance/v2-portable-release-report.md`
- Create: `releases/v2/README.md` only at approved release time.

### Task 1: 可测试的 Windows launcher

**Files:**
- Create: `src/greatocr/app/launcher.py`
- Create: `tests/app/test_launcher.py`

- [ ] **Step 1: 写启动配置测试**

```python
def test_launcher_uses_loopback_random_port_and_token(monkeypatch):
    config = create_launch_config(port_picker=lambda: 53123, token_factory=lambda: "token")
    assert config.base_url == "http://127.0.0.1:53123"
    assert config.session_token == "token"

def test_launcher_refuses_non_loopback_host():
    with pytest.raises(ValueError):
        create_launch_config(host="0.0.0.0")
```

- [ ] **Step 2: 实现启动和退出生命周期**

```python
@dataclass(frozen=True)
class LaunchConfig:
    host: str
    port: int
    session_token: str

def main() -> int:
    config = create_launch_config()
    server = start_server(config)
    webbrowser.open(f"{config.base_url}/?token={config.session_token}")
    return wait_until_exit(server)
```

令牌从 URL 读取后立即移入内存并通过 `history.replaceState` 清除地址栏；退出窗口或托盘命令必须关闭 uvicorn worker。

- [ ] **Step 3: 运行 launcher 测试**

Run: `./.venv/Scripts/python.exe -m pytest tests/app/test_launcher.py tests/app/test_auth.py -v`  
Expected: PASS。

- [ ] **Step 4: 条件提交**

```powershell
git add src/greatocr/app/launcher.py tests/app/test_launcher.py
git commit -m "feat: add portable local application launcher"
```

### Task 2: 固定可复现的便携构建

**Files:**
- Modify: `pyproject.toml`
- Create: `packaging/greatocr.spec`
- Create: `packaging/build-portable.ps1`

- [ ] **Step 1: 添加开发打包依赖**

```toml
[project.optional-dependencies]
dev = ["pytest>=8.0", "reportlab>=4.2", "pyinstaller>=6.12"]
```

- [ ] **Step 2: 编写 PyInstaller spec**

Spec 必须：入口为 `greatocr.app.launcher`；包含 `frontend/dist`；显式收集 pydantic、FastAPI、keyring Windows backend、PyMuPDF 和 python-docx 数据；排除 tests、testsamples、outputs、releases、API key 文件和本地模型。

- [ ] **Step 3: 编写构建脚本**

```powershell
$ErrorActionPreference = "Stop"
& "$PSScriptRoot/../.venv/Scripts/python.exe" -m pytest -q
Push-Location "$PSScriptRoot/../frontend"
npm ci
npm run build
Pop-Location
& "$PSScriptRoot/../.venv/Scripts/pyinstaller.exe" --clean "$PSScriptRoot/greatocr.spec"
Compress-Archive -Path "$PSScriptRoot/../dist/GreatOCR/*" -DestinationPath "$PSScriptRoot/../dist/GreatOCR-portable.zip" -Force
```

- [ ] **Step 4: 运行首次构建并记录体积**

Run: `powershell -ExecutionPolicy Bypass -File packaging/build-portable.ps1`  
Expected: `dist/GreatOCR/GreatOCR.exe` 和 `dist/GreatOCR-portable.zip` 存在。记录压缩与解压体积，不把估算写成承诺。

- [ ] **Step 5: 条件提交**

```powershell
git add pyproject.toml packaging/greatocr.spec packaging/build-portable.ps1
git commit -m "build: add Windows portable packaging"
```

### Task 3: 发布内容和秘密扫描

**Files:**
- Create: `tests/test_release_contents.py`
- Create: `packaging/verify-portable.ps1`

- [ ] **Step 1: 写发布内容失败测试**

```python
FORBIDDEN_NAMES = {"MinerU API key.txt", "testsamples", "outputs", ".env"}

def test_portable_tree_excludes_forbidden_files(portable_dir):
    names = {path.name for path in portable_dir.rglob("*")}
    assert not (names & FORBIDDEN_NAMES)

def test_portable_text_files_do_not_contain_test_secret(portable_dir, monkeypatch):
    monkeypatch.setenv("GREAT_OCR_TEST_SECRET", "never-ship-this")
    assert "never-ship-this" not in readable_release_text(portable_dir)
```

- [ ] **Step 2: 实现验证脚本**

验证脚本检查：必需文件、禁止路径、明文密钥模式、可执行文件启动、health endpoint、关闭后端口释放、ZIP 可解压、每个发布文件 SHA-256。

- [ ] **Step 3: 运行安全验证**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_release_contents.py tests/test_no_secret_leakage.py -v`  
Run: `powershell -ExecutionPolicy Bypass -File packaging/verify-portable.ps1 -PortableDir dist/GreatOCR`  
Expected: PASS。

- [ ] **Step 4: 条件提交**

```powershell
git add tests/test_release_contents.py packaging/verify-portable.ps1
git commit -m "test: verify portable release safety"
```

### Task 4: 干净 Windows 10/11 验收

**Files:**
- Create: `docs/acceptance/v2-portable-release-report.md`

- [ ] **Step 1: 准备离线 fake-provider 验收包**

发布包内不得包含真实业务 PDF。使用程序生成的无敏感两页 PDF，验证无需网络的完整 UI 流程。

- [ ] **Step 2: 在干净 Windows 10 环境执行清单**

记录：无需管理员权限；无 Python/Node.js；启动浏览器；创建任务；页码选择；fake provider 完成；打开输出；关闭后端口释放；API Key 状态属于当前 OS 用户。

- [ ] **Step 3: 在干净 Windows 11 环境重复清单**

额外记录 SmartScreen/企业安全提示。不得通过关闭安全软件来伪造通过；若被拦截，记录文件哈希和拦截信息。

- [ ] **Step 4: 写验收报告**

报告包含系统版本、发布哈希、测试步骤、结果、实际体积、告警和未通过项。

### Task 5: 经确认的真实 MinerU 回归

**Files:**
- Modify: `docs/acceptance/v2-portable-release-report.md`

- [ ] **Step 1: 在上传动作前取得用户明确确认**

确认必须包含：具体 PDF、具体页码、MinerU endpoint、是否敏感、预计发送内容。没有确认则跳过本任务并在报告记录“未授权，未上传”。

- [ ] **Step 2: 只选择已批准页面运行任务**

验证 provider 原始请求使用子 PDF，页数等于选择页数；不得使用整个原 PDF。

- [ ] **Step 3: 人工比较 V1/V2 Word**

至少评估：横竖方向、英文空格/断行、图片/印章、阅读顺序、页眉页脚、表格和返工时间。发布前在开发环境把 DOCX 渲染成 PNG 并逐页检查。

- [ ] **Step 4: 验证失败页重新拼合**

使用 fake 或受控失败注入让一页失败，确认 `result-v1.docx` 含占位；重试该页后生成 `result-v2.docx`，其他页面 provider 调用计数不增加。

### Task 6: 用户说明、校验文件和最终发布

**Files:**
- Create: `docs/user-guide.md`
- Create: `releases/v2/README.md`
- Create: `releases/v2/SHA256SUMS.txt`

- [ ] **Step 1: 编写非技术用户指南**

必须覆盖：启动、选择 PDF/页面、敏感文件、添加 API Key、解析能力标签、任务队列、失败切换、失败页重试、版本文件、关闭程序和删除凭据。

- [ ] **Step 2: 生成发布目录**

仅在用户批准发布时复制 `GreatOCR-portable.zip`、README 和校验文件到 `releases/v2/`。不得修改 `releases/v1/`。

- [ ] **Step 3: 运行最终验证**

Run: `./.venv/Scripts/python.exe -m pytest -v`  
Run: `cd frontend; npm test -- --run`  
Run: `powershell -ExecutionPolicy Bypass -File packaging/verify-portable.ps1 -PortableDir dist/GreatOCR`  
Expected: 全部 PASS。

- [ ] **Step 4: 条件提交**

```powershell
git add docs/user-guide.md docs/acceptance/v2-portable-release-report.md releases/v2
git commit -m "release: publish GreatOCR v2 portable build"
```

仅在有效 Git 仓库且用户已批准发布时执行。
