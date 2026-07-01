from pathlib import Path

import pytest
from pydantic import ValidationError

from greatocr.providers.base import ProviderCapabilities
from greatocr.providers.fake import FakeDocumentParser
from greatocr.providers.profiles import ProviderProfile, RequiredCapabilities
from greatocr.providers.registry import ProviderRegistry, UnknownProviderProfile


FIXTURE = Path("tests/fixtures/provider_outputs/simple_contract.json")


def text_only_profile() -> ProviderProfile:
    return ProviderProfile(
        profile_id="text-only",
        display_name="Text only",
        adapter_type="fake",
        endpoint=str(FIXTURE),
        public=False,
        verified=True,
        capabilities=ProviderCapabilities(
            native_pdf=True,
            scanned_pdf=True,
            coordinates=False,
            tables=False,
            formulas=False,
            languages=["en"],
            text=True,
            layout=False,
            images=False,
        ),
    )


def mineru_profile() -> ProviderProfile:
    return ProviderProfile(
        profile_id="mineru-default",
        display_name="MinerU",
        adapter_type="mineru",
        endpoint="https://mineru.example.test",
        public=True,
        verified=True,
        capabilities=ProviderCapabilities(
            native_pdf=True,
            scanned_pdf=True,
            coordinates=True,
            tables=True,
            formulas=True,
            languages=["auto"],
            text=True,
            layout=True,
            images=True,
        ),
    )


def test_registry_filters_provider_by_required_capabilities() -> None:
    registry = ProviderRegistry([text_only_profile(), mineru_profile()])

    matches = registry.match(RequiredCapabilities(layout=True, tables=True))

    assert [profile.profile_id for profile in matches] == ["mineru-default"]


def test_registry_get_unknown_profile_has_readable_error() -> None:
    registry = ProviderRegistry([mineru_profile()])

    with pytest.raises(UnknownProviderProfile, match="missing-profile"):
        registry.get("missing-profile")


def test_registry_rejects_unknown_adapter_type() -> None:
    payload = mineru_profile().model_dump()
    payload["adapter_type"] = "arbitrary-python-plugin"

    with pytest.raises(ValidationError):
        ProviderProfile.model_validate(payload)


def test_registry_creates_fake_parser_without_a_secret() -> None:
    registry = ProviderRegistry([text_only_profile()])

    parser = registry.create_parser("text-only", secret_resolver=None)

    assert isinstance(parser, FakeDocumentParser)
