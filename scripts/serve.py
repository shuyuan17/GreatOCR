"""GreatOCR V2.3 local web application launcher.

Usage:
  .venv/Scripts/python.exe scripts/serve.py

Starts FastAPI backend at http://127.0.0.1:8399 by default.

On first run it auto-creates:
  1. SQLite database (data/greatocr.db)
  2. fake-default provider (no API key required, for offline testing)
  3. A placeholder credential for that provider
"""

from __future__ import annotations

import sys
import threading
from pathlib import Path

# 确保能找到 src 包
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT / "src"))

import uvicorn
from greatocr.app.db import TaskDatabase
from greatocr.app.main import create_app
from greatocr.app.services.credentials import CredentialService
from greatocr.app.services.task_service import TaskService
from greatocr.app.services.thumbnails import ThumbnailService

# ---------------------------------------------------------------------------
# 路径
# ---------------------------------------------------------------------------
DATA_DIR = _PROJECT_ROOT / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
DB_PATH = DATA_DIR / "greatocr.db"
THUMBNAIL_DIR = DATA_DIR / "thumbnails"
FIXTURE_PATH = _PROJECT_ROOT / "tests" / "fixtures" / "provider_outputs" / "simple_contract.json"

# ---------------------------------------------------------------------------
# 配置常量（与前端 .env.development 中的 VITE_GREAT_OCR_TOKEN 保持一致）
# ---------------------------------------------------------------------------
SESSION_TOKEN = "greatocr-dev-token-2026"
ALLOWED_ORIGIN = "http://localhost:5173"
BIND_HOST = "127.0.0.1"
BIND_PORT = 8399

# ---------------------------------------------------------------------------
# 初始化
# ---------------------------------------------------------------------------
DATA_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
THUMBNAIL_DIR.mkdir(parents=True, exist_ok=True)

database = TaskDatabase(DB_PATH)

# ---------- 创建凭据服务 ----------
# 注意：CredentialService 需要实现 KeyringBackend 协议的对象
class _SystemKeyringBackend:
    """包装系统 keyring，使其符合 KeyringBackend 协议。"""
    def __init__(self) -> None:
        import keyring as _kr
        self._kr = _kr

    def set_password(self, service: str, username: str, password: str) -> None:
        self._kr.set_password(service, username, password)

    def get_password(self, service: str, username: str) -> str | None:
        return self._kr.get_password(service, username)

    def delete_password(self, service: str, username: str) -> None:
        try:
            self._kr.delete_password(service, username)
        except self._kr.errors.PasswordDeleteError:
            pass


class _MemoryKeyring:
    """当系统 keyring 不可用时的简单内存 fallback。"""
    def __init__(self) -> None:
        self._store: dict[tuple[str, str], str] = {}

    def set_password(self, service: str, username: str, password: str) -> None:
        self._store[(service, username)] = password

    def get_password(self, service: str, username: str) -> str | None:
        return self._store.get((service, username))

    def delete_password(self, service: str, username: str) -> None:
        self._store.pop((service, username), None)


try:
    import keyring

    keyring.get_keyring()
    credentials = CredentialService(_SystemKeyringBackend())
    print("[serve] ✓ 使用系统 keyring 存储凭证")
except Exception:
    print("[serve] 系统 keyring 不可用，使用内存存储（重启后需重新配置 API Key）")
    credentials = CredentialService(_MemoryKeyring())

# ---------- 写入 fake-default provider（如果不存在）----------
FAKE_PROFILE_ID = "fake-default"
if database.get_provider(FAKE_PROFILE_ID) is None:
    database.save_provider({
        "profile_id": FAKE_PROFILE_ID,
        "display_name": "Fake Provider（离线测试）",
        "adapter_type": "fake",
        "endpoint": str(FIXTURE_PATH),
        "public": False,
        "capabilities": {
            "native_pdf": True,
            "scanned_pdf": True,
            "coordinates": True,
            "layout": True,
            "tables": True,
            "images": True,
            "formulas": False,
            "languages": ["auto", "en", "zh"],
            "data_residency": "local-fixture",
        },
    })
    # 设置一个占位密钥，使 credential 检查通过
    try:
        credentials.set(FAKE_PROFILE_ID, "fake-placeholder-key")
        print(f"[serve] ✓ 已创建 provider: {FAKE_PROFILE_ID}")
    except Exception as exc:
        print(f"[serve] ⚠ 创建 {FAKE_PROFILE_ID} 密钥时出错: {exc}")

# ---------- 检查 MinerU provider 凭证配置 ----------
MINERU_PROFILE_ID = "mineru-default"
mineru_config = database.get_provider(MINERU_PROFILE_ID)
if mineru_config is None:
    print(f"[serve] ⚠ 未找到 provider: {MINERU_PROFILE_ID}，fake 模式下无法使用 MinerU")
else:
    cred_status = credentials.status(MINERU_PROFILE_ID)
    if cred_status.configured:
        print(f"[serve] ✓ MinerU API Key 已配置: {cred_status.masked}")
    else:
        print(f"[serve] ⚠ MinerU API Key 未配置")
        print(f"[serve]   如需使用真实 OCR，请运行:")
        print(f'[serve]     curl -X POST http://127.0.0.1:{BIND_PORT}/api/providers \\')
        print(f'[serve]       -H "X-GreatOCR-Token: {SESSION_TOKEN}" \\')
        print(f'[serve]       -H "X-GreatOCR-Provider-Key: <你的 MinerU API Key>" \\')
        print(f'[serve]       -H "Content-Type: application/json" \\')
        print(f'[serve]       -d \'{{"profile_id":"mineru-default","display_name":"MinerU","adapter_type":"mineru","endpoint":"https://mineru.net","public":true,"capabilities":{{"tables":true,"images":true}}}}\'')

# ---------- 服务 ----------
thumbnails = ThumbnailService(THUMBNAIL_DIR)
task_service = TaskService(database, credentials, thumbnails)

app = create_app(
    session_token=SESSION_TOKEN,
    allowed_origin=ALLOWED_ORIGIN,
    database=database,
    credential_service=credentials,
    task_service=task_service,
    upload_dir=UPLOAD_DIR,
)


# ---------------------------------------------------------------------------
# 后台 Worker：自动处理 pending 任务
# ---------------------------------------------------------------------------

def _run_background_worker() -> None:
    """在后台线程中轮询 pending 任务并执行 OCR 管道。"""
    import time

    from greatocr.app.services.worker import SerialWorker
    from greatocr.ingest.preflight import run_preflight, InvalidPdfError
    from greatocr.pipeline import run_pipeline
    from greatocr.providers.base import ProviderCapabilities
    from greatocr.providers.profiles import ProviderProfile, RequiredCapabilities
    from greatocr.providers.registry import ProviderRegistry
    from greatocr.security import (
        DataFlowSummary,
        RetentionPolicy,
        SecurityMode,
    )

    def _secret_resolver(profile_id: str) -> str:
        return credentials.resolve(profile_id).get_secret_value()

    worker = SerialWorker(database)

    while True:
        time.sleep(2)
        task = worker.tick()
        if task is None:
            continue

        print(f"[worker] 开始处理任务 {task.task_id}")
        try:
            # 获取 provider 配置
            profile_dict = database.get_provider(task.provider_profile_id)
            if profile_dict is None:
                raise RuntimeError(f"provider {task.provider_profile_id} not found")
            profile = ProviderProfile(**profile_dict)

            # 创建 parser（MinerU 需要标记上传已确认）
            if profile.adapter_type == "mineru":
                from greatocr.providers.mineru import MinerUConfig, MinerUDocumentParser

                secret = _secret_resolver(task.provider_profile_id)
                config = MinerUConfig(base_url=profile.endpoint, api_key=secret)
                parser = MinerUDocumentParser(config, upload_confirmed=True)
            else:
                registry = ProviderRegistry([profile])
                parser = registry.create_parser(
                    task.provider_profile_id, _secret_resolver
                )

            # 预检
            if task.source_path is None:
                raise RuntimeError("source path not available")
            source_path = Path(task.source_path)
            preflight = run_preflight(source_path)

            # 构建安全摘要
            provider_public = bool(profile.public)
            is_local_fixture = (
                profile.capabilities.data_residency == "local-fixture"
            )
            security_summary = DataFlowSummary(
                security_mode=(
                    SecurityMode.SENSITIVE if task.sensitive else SecurityMode.NORMAL
                ),
                source_file_name=source_path.name,
                page_count=preflight.page_count,
                provider_name=profile.display_name,
                provider_endpoint=profile.endpoint or None,
                provider_public=provider_public,
                external_upload_allowed=not is_local_fixture,
                requires_confirmation=False,
                retention_policy=RetentionPolicy(
                    keep_intermediates=False,
                    keep_page_cache=False,
                ),
            )

            # 执行管道
            task_dir = Path(task.output_dir)
            task_dir.mkdir(parents=True, exist_ok=True)
            run_pipeline(
                task_dir=task_dir,
                preflight=preflight,
                parser=parser,
                security_summary=security_summary,
                selected_pages=task.selected_pages or None,
            )

            worker.finish(task.task_id, "succeeded")
            print(f"[worker] 任务 {task.task_id} 处理完成")
        except InvalidPdfError as exc:
            print(f"[worker] 任务 {task.task_id} 文件格式错误: {exc}")
            worker.finish(task.task_id, "failed")
        except Exception as exc:
            print(f"[worker] 任务 {task.task_id} 处理失败: {exc}")
            worker.finish(task.task_id, "failed")


# 启动后台 worker 线程
_worker_thread = threading.Thread(target=_run_background_worker, daemon=True)
_worker_thread.start()

if __name__ == "__main__":
    print(f"[serve] GreatOCR V2.3 后端启动中...")
    print(f"[serve]   地址: http://{BIND_HOST}:{BIND_PORT}")
    print(f"[serve]   数据: {DATA_DIR}")
    uvicorn.run(app, host=BIND_HOST, port=BIND_PORT, log_level="info")
