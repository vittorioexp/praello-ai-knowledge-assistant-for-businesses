"""Authenticated encryption for external connector credentials."""

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from enterprise_ai.domain.exceptions import ValidationError


class ConnectorTokenCipher:
    """Encrypt connector tokens using the application secret."""

    def __init__(self, application_secret: str) -> None:
        key = base64.urlsafe_b64encode(hashlib.sha256(application_secret.encode()).digest())
        self._cipher = Fernet(key)

    def encrypt(self, token: str) -> str:
        return self._cipher.encrypt(token.encode()).decode()

    def decrypt(self, encrypted_token: str) -> str:
        try:
            return self._cipher.decrypt(encrypted_token.encode()).decode()
        except InvalidToken as exc:
            raise ValidationError("Connector credential cannot be decrypted") from exc