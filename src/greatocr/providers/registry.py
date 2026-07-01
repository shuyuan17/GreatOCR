from __future__ import annotations

from collections.abc import Callable, Iterable
from pathlib import Path

from greatocr.providers.base import DocumentParser
from greatocr.providers.fake import FakeDocumentParser
from greatocr.providers.mineru import MinerUConfig, MinerUDocumentParser
from greatocr.providers.profiles import ProviderProfile, RequiredCapabilities


class UnknownProviderProfile(LookupError):
    """Raised when a configured provider profile cannot be found."""


class ProviderSecretRequired(ValueError):
    """Raised when an online provider has no secret resolver."""


class ProviderRegistry:
    def __init__(self, profiles: Iterable[ProviderProfile]) -> None:
        self._profiles: dict[str, ProviderProfile] = {}
        for profile in profiles:
            if profile.profile_id in self._profiles:
                raise ValueError(f"duplicate provider profile: {profile.profile_id}")
            self._profiles[profile.profile_id] = profile

    def get(self, profile_id: str) -> ProviderProfile:
        try:
            return self._profiles[profile_id]
        except KeyError as exc:
            raise UnknownProviderProfile(
                f"unknown provider profile: {profile_id}"
            ) from exc

    def match(self, requirements: RequiredCapabilities) -> list[ProviderProfile]:
        required = [
            name
            for name, enabled in requirements.model_dump().items()
            if enabled
        ]
        return [
            profile
            for profile in self._profiles.values()
            if all(getattr(profile.capabilities, name) for name in required)
        ]

    def create_parser(
        self,
        profile_id: str,
        secret_resolver: Callable[[str], str] | None,
    ) -> DocumentParser:
        profile = self.get(profile_id)
        if profile.adapter_type == "fake":
            return FakeDocumentParser(Path(profile.endpoint))
        if secret_resolver is None:
            raise ProviderSecretRequired(
                f"provider profile requires a local secret: {profile.profile_id}"
            )
        secret = secret_resolver(profile.profile_id)
        if profile.adapter_type == "mineru":
            return MinerUDocumentParser(
                MinerUConfig(base_url=profile.endpoint, api_key=secret),
                upload_confirmed=False,
            )

        from greatocr.providers.generic_vision import GenericVisionDocumentParser

        return GenericVisionDocumentParser.from_profile(profile, api_key=secret)
