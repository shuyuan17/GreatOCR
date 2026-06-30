from __future__ import annotations

import platform
from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, SecretStr

from greatocr import __version__
from greatocr.security import SecurityMode


@dataclass(frozen=True)
class RuntimeInfo:
    python_version: str
    greatocr_version: str


def get_runtime_info() -> RuntimeInfo:
    return RuntimeInfo(
        python_version=platform.python_version(),
        greatocr_version=__version__,
    )


class ProviderConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str = "not_configured"
    endpoint: str | None = None
    api_key: SecretStr | None = None
    public: bool = True
    last_approved: bool = False


class EngineConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    security_mode: SecurityMode = SecurityMode.NORMAL
    provider: ProviderConfig = ProviderConfig()
