from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from greatocr.providers.profiles import ProviderProfile, RequiredCapabilities


class FallbackPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    mode: Literal["stop", "ask", "auto"] = "ask"
    approved_profile_ids: list[str] = Field(default_factory=list)


class FallbackChoiceRequired(RuntimeError):
    def __init__(self, candidate_profile_ids: list[str]) -> None:
        super().__init__("fallback provider choice requires explicit user approval")
        self.candidate_profile_ids = candidate_profile_ids


class NoApprovedFallback(RuntimeError):
    """Raised when no approved provider satisfies the task requirements."""


def choose_fallback(
    policy: FallbackPolicy,
    candidates: list[ProviderProfile],
    *,
    requirements: RequiredCapabilities | None = None,
) -> ProviderProfile | None:
    if policy.mode == "stop":
        return None

    requirements = requirements or RequiredCapabilities()
    capable = [profile for profile in candidates if _meets(profile, requirements)]
    if policy.mode == "ask":
        if not capable:
            raise NoApprovedFallback("no capable fallback provider is available")
        raise FallbackChoiceRequired([profile.profile_id for profile in capable])

    approved = set(policy.approved_profile_ids)
    for profile in capable:
        if profile.profile_id in approved:
            return profile
    raise NoApprovedFallback("no preapproved fallback provider satisfies the task")


def _meets(
    profile: ProviderProfile,
    requirements: RequiredCapabilities,
) -> bool:
    return all(
        not enabled or bool(getattr(profile.capabilities, name))
        for name, enabled in requirements.model_dump().items()
    )
