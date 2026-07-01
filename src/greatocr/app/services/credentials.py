from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel, ConfigDict, SecretStr


class KeyringBackend(Protocol):
    def set_password(self, service: str, username: str, password: str) -> None: ...

    def get_password(self, service: str, username: str) -> str | None: ...

    def delete_password(self, service: str, username: str) -> None: ...


class CredentialStatus(BaseModel):
    model_config = ConfigDict(frozen=True)

    configured: bool
    masked: str | None = None


class CredentialNotConfigured(RuntimeError):
    pass


class CredentialService:
    def __init__(
        self,
        backend: KeyringBackend,
        service_name: str = "GreatOCR",
    ) -> None:
        self.backend = backend
        self.service_name = service_name

    def set(self, profile_id: str, secret: str) -> None:
        value = secret.strip()
        if not value:
            raise ValueError("API key cannot be empty")
        self.backend.set_password(self.service_name, profile_id, value)

    def resolve(self, profile_id: str) -> SecretStr:
        value = self.backend.get_password(self.service_name, profile_id)
        if value is None:
            raise CredentialNotConfigured(profile_id)
        return SecretStr(value)

    def status(self, profile_id: str) -> CredentialStatus:
        value = self.backend.get_password(self.service_name, profile_id)
        return CredentialStatus(
            configured=value is not None,
            masked=("********" + value[-4:]) if value else None,
        )

    def delete(self, profile_id: str) -> None:
        if self.backend.get_password(self.service_name, profile_id) is not None:
            self.backend.delete_password(self.service_name, profile_id)
