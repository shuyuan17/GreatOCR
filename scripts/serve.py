"""GreatOCR V2.3 local web application launcher.

Usage:
  .venv/Scripts/python.exe scripts/serve.py

Starts FastAPI backend at http://127.0.0.1:8399 by default.

On first run it auto-creates:
  1. SQLite database (data/greatocr.db)
  2. mineru-default provider
  3. Default user preferences
"""

from __future__ import annotations

import os
import sys
import threading
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT / "src"))

import uvicorn
from greatocr.app.db import TaskDatabase
from greatocr.app.main import create_app
from greatocr.app.release_bootstrap import ensure_release_defaults, get_user_data_dir
from greatocr.app.services.credentials import CredentialService, JsonCredentialBackend
from greatocr.app.services.provider_connections import probe_provider_connection
from greatocr.app.services.task_service import TaskService
from greatocr.app.services.thumbnails import ThumbnailService

DATA_DIR = _PROJECT_ROOT / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
DB_PATH = DATA_DIR / "greatocr.db"
THUMBNAIL_DIR = DATA_DIR / "thumbnails"
USER_DATA_DIR = get_user_data_dir()
CREDENTIALS_PATH = USER_DATA_DIR / "credentials.json"

SESSION_TOKEN = os.environ["GREATOCR_SESSION_TOKEN"]
ALLOWED_ORIGIN = os.environ.get("GREATOCR_ALLOWED_ORIGIN", "http://localhost:5173")
BIND_HOST = "127.0.0.1"
BIND_PORT = 8399

DATA_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
THUMBNAIL_DIR.mkdir(parents=True, exist_ok=True)

database = TaskDatabase(DB_PATH)


class _SystemKeyringBackend:
    """Wrap the system keyring to match the CredentialService protocol."""

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


try:
    import keyring

    keyring.get_keyring()
    credentials = CredentialService(_SystemKeyringBackend())
    print("[serve] Using system keyring for provider credentials")
except Exception:
    print(f"[serve] System keyring unavailable, using local user config: {CREDENTIALS_PATH}")
    credentials = CredentialService(JsonCredentialBackend(CREDENTIALS_PATH))

ensure_release_defaults(database, data_dir=DATA_DIR)

mineru_config = database.get_provider("mineru-default")
if mineru_config is None:
    print("[serve] MinerU provider profile is missing")
else:
    cred_status = credentials.status("mineru-default")
    if cred_status.configured:
        print(f"[serve] MinerU API key configured: {cred_status.masked}")
    else:
        print("[serve] MinerU API key not configured yet")
        print("[serve] Open Settings in the browser to add your API key and Base URL.")

thumbnails = ThumbnailService(THUMBNAIL_DIR)
task_service = TaskService(database, credentials, thumbnails)

app = create_app(
    session_token=SESSION_TOKEN,
    allowed_origin=ALLOWED_ORIGIN,
    database=database,
    credential_service=credentials,
    provider_connection_tester=probe_provider_connection,
    task_service=task_service,
    upload_dir=UPLOAD_DIR,
)


def _run_background_worker() -> None:
    import time

    from greatocr.app.services.worker import SerialWorker
    from greatocr.ingest.preflight import InvalidPdfError, run_preflight
    from greatocr.pipeline import run_pipeline
    from greatocr.providers.mineru import MinerUConfig, MinerUDocumentParser
    from greatocr.providers.profiles import ProviderProfile
    from greatocr.providers.registry import ProviderRegistry
    from greatocr.security import DataFlowSummary, RetentionPolicy, SecurityMode

    def _secret_resolver(profile_id: str) -> str:
        return credentials.resolve(profile_id).get_secret_value()

    worker = SerialWorker(database)

    while True:
        time.sleep(2)
        task = worker.tick()
        if task is None:
            continue

        print(f"[worker] Starting task {task.task_id}")
        try:
            profile_dict = database.get_provider(task.provider_profile_id)
            if profile_dict is None:
                raise RuntimeError(f"provider {task.provider_profile_id} not found")
            profile = ProviderProfile(**profile_dict)

            if profile.adapter_type == "mineru":
                secret = _secret_resolver(task.provider_profile_id)
                config = MinerUConfig(base_url=profile.endpoint, api_key=secret)
                parser = MinerUDocumentParser(config, upload_confirmed=True)
            else:
                registry = ProviderRegistry([profile])
                parser = registry.create_parser(task.provider_profile_id, _secret_resolver)

            if task.source_path is None:
                raise RuntimeError("source path not available")
            source_path = Path(task.source_path)
            preflight = run_preflight(source_path)

            security_summary = DataFlowSummary(
                security_mode=(
                    SecurityMode.SENSITIVE if task.sensitive else SecurityMode.NORMAL
                ),
                source_file_name=source_path.name,
                page_count=preflight.page_count,
                provider_name=profile.display_name,
                provider_endpoint=profile.endpoint or None,
                provider_public=bool(profile.public),
                external_upload_allowed=True,
                requires_confirmation=False,
                retention_policy=RetentionPolicy(
                    keep_intermediates=False,
                    keep_page_cache=False,
                ),
            )

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
            print(f"[worker] Task {task.task_id} finished")
        except InvalidPdfError as exc:
            print(f"[worker] Task {task.task_id} failed preflight: {exc}")
            worker.finish(task.task_id, "failed")
        except Exception as exc:
            print(f"[worker] Task {task.task_id} failed: {exc}")
            worker.finish(task.task_id, "failed")


_worker_thread = threading.Thread(target=_run_background_worker, daemon=True)
_worker_thread.start()

if __name__ == "__main__":
    print("[serve] GreatOCR backend starting...")
    print(f"[serve] URL: http://{BIND_HOST}:{BIND_PORT}")
    print(f"[serve] Allowed origin: {ALLOWED_ORIGIN}")
    print(f"[serve] Data directory: {DATA_DIR}")
    uvicorn.run(app, host=BIND_HOST, port=BIND_PORT, log_level="info")
