import pytest

from greatocr.providers.base import ProviderCapabilities
from greatocr.providers.fallback import (
    FallbackChoiceRequired,
    FallbackPolicy,
    NoApprovedFallback,
    choose_fallback,
)
from greatocr.providers.profiles import ProviderProfile, RequiredCapabilities


def profile(profile_id: str, *, public: bool, layout: bool = True) -> ProviderProfile:
    return ProviderProfile(
        profile_id=profile_id,
        display_name=profile_id,
        adapter_type="mineru",
        endpoint=f"https://{profile_id}.example.test",
        public=public,
        verified=True,
        capabilities=ProviderCapabilities(
            native_pdf=True,
            scanned_pdf=True,
            coordinates=layout,
            layout=layout,
            tables=layout,
            images=layout,
            formulas=False,
            languages=["auto"],
        ),
    )


def test_sensitive_auto_fallback_uses_only_preapproved_profiles() -> None:
    policy = FallbackPolicy(mode="auto", approved_profile_ids=["private-a"])

    chosen = choose_fallback(
        policy,
        [profile("public-b", public=True), profile("private-a", public=False)],
        requirements=RequiredCapabilities(layout=True, tables=True),
    )

    assert chosen.profile_id == "private-a"


def test_ask_mode_never_sends_without_user_choice() -> None:
    candidate = profile("mineru-default", public=True)

    with pytest.raises(FallbackChoiceRequired) as captured:
        choose_fallback(FallbackPolicy(mode="ask"), [candidate])

    assert captured.value.candidate_profile_ids == ["mineru-default"]


def test_auto_mode_rejects_approved_provider_with_insufficient_capabilities() -> None:
    policy = FallbackPolicy(mode="auto", approved_profile_ids=["text-only"])

    with pytest.raises(NoApprovedFallback):
        choose_fallback(
            policy,
            [profile("text-only", public=False, layout=False)],
            requirements=RequiredCapabilities(layout=True),
        )


def test_stop_mode_returns_no_provider() -> None:
    assert choose_fallback(FallbackPolicy(mode="stop"), [profile("a", public=False)]) is None
