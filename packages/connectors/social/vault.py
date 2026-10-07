import base64
import hashlib
import json
import os
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class BaseOAuthTokenVault(ABC):
    """
    Abstract OAuth Token Vault interface.
    Stores and manages access/refresh tokens with strict tenant isolation and encryption at rest.
    """

    @abstractmethod
    def store_token(
        self,
        workspace_id: str,
        provider: str,
        account_id: str,
        access_token: str,
        refresh_token: Optional[str] = None,
        expires_at: Optional[datetime] = None,
        scopes: Optional[List[str]] = None
    ) -> None:
        """Stores an encrypted OAuth credential record for a workspace."""
        pass

    @abstractmethod
    def get_token(
        self,
        workspace_id: str,
        provider: str,
        account_id: str
    ) -> Optional[Dict[str, Any]]:
        """Retrieves and decrypts the OAuth credential record. Returns None if absent or revoked."""
        pass

    @abstractmethod
    def rotate_token(
        self,
        workspace_id: str,
        provider: str,
        account_id: str,
        new_access_token: str,
        new_refresh_token: Optional[str] = None,
        new_expires_at: Optional[datetime] = None
    ) -> None:
        """Rotates the access and refresh tokens for an existing account."""
        pass

    @abstractmethod
    def revoke_token(
        self,
        workspace_id: str,
        provider: str,
        account_id: str
    ) -> bool:
        """Revokes and purges the stored OAuth credentials."""
        pass


class EncryptedOAuthTokenVault(BaseOAuthTokenVault):
    """
    High-security OAuth Token Vault using AES-GCM 256-bit encryption at rest.
    Keys are cryptographically bound to the specific workspace_id via Authenticated Additional Data (AAD).
    """

    def __init__(self, vault_key: Optional[str] = None):
        raw_key = str(vault_key or os.getenv("SECRET_VAULT_KEY") or "default-dev-secret-vault-key-32b-min")
        # Derive a 256-bit (32 bytes) key using SHA-256
        self._key = hashlib.sha256(raw_key.encode("utf-8")).digest()
        self._aesgcm = AESGCM(self._key)
        # In-memory storage of ciphertexts: (workspace_id, provider, account_id) -> ciphertext_b64
        self._storage: Dict[str, str] = {}

    def _make_key(self, workspace_id: str, provider: str, account_id: str) -> str:
        return f"{workspace_id}:{provider.lower()}:{account_id.lower()}"

    def store_token(
        self,
        workspace_id: str,
        provider: str,
        account_id: str,
        access_token: str,
        refresh_token: Optional[str] = None,
        expires_at: Optional[datetime] = None,
        scopes: Optional[List[str]] = None
    ) -> None:
        payload = {
            "workspace_id": workspace_id,
            "provider": provider,
            "account_id": account_id,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_at": expires_at.isoformat() if expires_at else None,
            "scopes": scopes or [],
            "updated_at": datetime.now(timezone.utc).isoformat()
        }

        raw_bytes = json.dumps(payload).encode("utf-8")
        # 12-byte random nonce for AES-GCM
        nonce = os.urandom(12)
        # Authenticated data binds the record strictly to this workspace_id
        aad = workspace_id.encode("utf-8")
        ciphertext = self._aesgcm.encrypt(nonce, raw_bytes, aad)

        # Store nonce + ciphertext combined as base64
        stored_value = base64.b64encode(nonce + ciphertext).decode("utf-8")
        storage_key = self._make_key(workspace_id, provider, account_id)
        self._storage[storage_key] = stored_value

    def get_token(
        self,
        workspace_id: str,
        provider: str,
        account_id: str
    ) -> Optional[Dict[str, Any]]:
        storage_key = self._make_key(workspace_id, provider, account_id)
        stored_value = self._storage.get(storage_key)
        if not stored_value:
            return None

        try:
            raw_blob = base64.b64decode(stored_value.encode("utf-8"))
            nonce = raw_blob[:12]
            ciphertext = raw_blob[12:]
            aad = workspace_id.encode("utf-8")

            decrypted_bytes = self._aesgcm.decrypt(nonce, ciphertext, aad)
            payload = json.loads(decrypted_bytes.decode("utf-8"))

            # Convert isoformat expires_at back to datetime if present
            if payload.get("expires_at"):
                payload["expires_at"] = datetime.fromisoformat(payload["expires_at"])
            return payload
        except Exception:
            # Decryption failure or AAD mismatch (e.g. cross-tenant tampering attempt)
            return None

    def rotate_token(
        self,
        workspace_id: str,
        provider: str,
        account_id: str,
        new_access_token: str,
        new_refresh_token: Optional[str] = None,
        new_expires_at: Optional[datetime] = None
    ) -> None:
        existing = self.get_token(workspace_id, provider, account_id)
        scopes = existing.get("scopes", []) if existing else []
        refresh = new_refresh_token or (existing.get("refresh_token") if existing else None)

        self.store_token(
            workspace_id=workspace_id,
            provider=provider,
            account_id=account_id,
            access_token=new_access_token,
            refresh_token=refresh,
            expires_at=new_expires_at,
            scopes=scopes
        )

    def revoke_token(
        self,
        workspace_id: str,
        provider: str,
        account_id: str
    ) -> bool:
        storage_key = self._make_key(workspace_id, provider, account_id)
        return bool(self._storage.pop(storage_key, None) is not None)
