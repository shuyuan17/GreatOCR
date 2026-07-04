from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict

from greatocr.app.db import TaskDatabase


router = APIRouter(prefix="/preferences", tags=["preferences"])

# 默认偏好设置
DEFAULT_PREFERENCES: dict[str, str] = {
    "ocr_language": "auto",
    "sensitive_file_mode": "false",
    "pdf_process_all_pages": "true",
    "pdf_default_page_range": "",
    "output_default_dir": "",
    "output_same_as_input": "true",
    "result_export_docx": "true",
    "result_generate_quality_report": "true",
}


class PreferencesUpdate(BaseModel):
    model_config = ConfigDict(frozen=True)

    preferences: dict[str, str]


def _database(request: Request) -> TaskDatabase:
    database = getattr(request.app.state, "database", None)
    if database is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "DATABASE_UNAVAILABLE"},
        )
    return database


@router.get("")
def get_preferences(request: Request) -> dict[str, str]:
    """获取所有偏好设置。返回合并了默认值的完整偏好字典。"""
    database = _database(request)
    stored = database.get_preferences()
    # 合并默认值（用户已设置的覆盖默认值）
    merged = {**DEFAULT_PREFERENCES, **stored}
    return merged


@router.put("")
def update_preferences(
    payload: PreferencesUpdate,
    request: Request,
) -> dict[str, str]:
    """批量更新偏好设置。只更新传入的键，未传入的键保持不变。"""
    database = _database(request)
    database.set_preferences(payload.preferences)
    stored = database.get_preferences()
    merged = {**DEFAULT_PREFERENCES, **stored}
    return merged
