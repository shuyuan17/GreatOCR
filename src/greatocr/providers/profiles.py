from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from greatocr.providers.base import ProviderCapabilities


class ProviderProfile(BaseModel):
    model_config = ConfigDict(frozen=True)

    profile_id: str
    display_name: str
    adapter_type: Literal["mineru", "generic_vision", "fake", "deepseek"]
    endpoint: str
    model_name: str | None = None
    public: bool = True
    verified: bool = False
    capabilities: ProviderCapabilities


class RequiredCapabilities(BaseModel):
    model_config = ConfigDict(frozen=True)

    text: bool = True
    layout: bool = False
    tables: bool = False
    images: bool = False
    formulas: bool = False
