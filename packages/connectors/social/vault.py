import base64
import hashlib
import json
import os
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional
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
        scopes: Optional[List[str]] = None,
        account_name: Optional[str] = None
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
    Production-ready OAuth Token Vault using AES-GCM 256-bit authenticated encryption.
    Features:
    - Tenant isolation via Authenticated Additional Data (AAD = workspace_id).
    - Cryptographic key ring supporting key versioning and key ID (`kid`) rotation.
    - Fail-closed security validation in production (disallows default or weak keys).
    - Dual persistence: writes to database (ConnectedSocialAccountModel) when session/factory
      is supplied, with in-memory fallback/cache for fast retrieval and test isolation.
    """

    def __init__(
        self,
        vault_key: Optional[str] = None,
        key_ring: Optional[Dict[str, str]] = None,
        active_key_id: str = "v1",
        db_session: Optional[Any] = None,
        session_factory: Optional[Callable[[], Any]] = None
    ):
        env = os.getenv("ENV", "production").lower()

        self._key_ring: Dict[str, bytes] = {}
        if key_ring:
            for kid, kstr in key_ring.items():
                self._key_ring[kid] = hashlib.sha256(kstr.encode("utf-8")).digest()

        raw_key = vault_key or os.getenv("SECRET_VAULT_KEY")

        if not raw_key and not self._key_ring:
            if env == "production":
                raise ValueError("FATAL: SECRET_VAULT_KEY is required and must not be empty in production.")
            raw_key = "default-dev-secret-vault-key-32b-min"

        if env == "production" and raw_key:
            if raw_key == "default-dev-secret-vault-key-32b-min" or len(raw_key) < 32:
                raise ValueError(
                    "FATAL: Insecure or default SECRET_VAULT_KEY is prohibited in production. "
                    "Minimum length: 32 characters."
                )

        if raw_key:
            derived = hashlib.sha256(raw_key.encode("utf-8")).digest()
            if active_key_id not in self._key_ring:
                self._key_ring[active_key_id] = derived

        self.active_key_id = active_key_id
        self._storage: Dict[str, str] = {}
        self.db_session = db_session
        self.session_factory = session_factory

    def _get_session(self) -> Optional[Any]:
        if self.db_session is not None:
            return self.db_session
        if self.session_factory is not None:
            return self.session_factory()
        return None

    def _get_cipher(self, kid: str) -> AESGCM:
        if kid not in self._key_ring:
            raise ValueError(f"Vault key ID '{kid}' not found in key ring.")
        return AESGCM(self._key_ring[kid])

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
        scopes: Optional[List[str]] = None,
        account_name: Optional[str] = None
    ) -> None:
        payload = {
            "workspace_id": workspace_id,
            "provider": provider,
            "account_id": account_id,
            "account_name": account_name,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_at": expires_at.isoformat() if expires_at else None,
            "scopes": scopes or [],
            "updated_at": datetime.now(timezone.utc).isoformat()
        }

        raw_bytes = json.dumps(payload).encode("utf-8")
        # 12-byte cryptographically secure random nonce
        nonce = os.urandom(12)
        # Authenticated Additional Data strictly binds ciphertext to workspace_id
        aad = workspace_id.encode("utf-8")
        cipher = self._get_cipher(self.active_key_id)
        ciphertext = cipher.encrypt(nonce, raw_bytes, aad)

        # Store with envelope tagging the key ID
        envelope = {
            "kid": self.active_key_id,
            "b64": base64.b64encode(nonce + ciphertext).decode("utf-8")
        }
        stored_value = json.dumps(envelope)

        storage_key = self._make_key(workspace_id, provider, account_id)
        self._storage[storage_key] = stored_value

        # Persist to database if a session or factory is available
        session = self._get_session()
        if session is not None:
            try:
                from infra.db.models import ConnectedSocialAccountModel
                account = (
                    session.query(ConnectedSocialAccountModel)
                    .filter(
                        ConnectedSocialAccountModel.workspace_id == workspace_id,
                        ConnectedSocialAccountModel.provider == provider.lower(),
                        ConnectedSocialAccountModel.account_id == account_id
                    )
                    .first()
                )
                if not account:
                    account = ConnectedSocialAccountModel(
                        id=f"csa_{uuid.uuid4().hex[:12]}",
                        workspace_id=workspace_id,
                        provider=provider.lower(),
                        account_id=account_id,
                        account_name=account_name or account_id,
                        encrypted_token_blob=stored_value,
                        key_id=self.active_key_id,
                        scopes=scopes or [],
                        expires_at=expires_at,
                        status="ACTIVE"
                    )
                    session.add(account)
                else:
                    account.encrypted_token_blob = stored_value
                    account.key_id = self.active_key_id
                    account.scopes = scopes or []
                    account.expires_at = expires_at
                    account.status = "ACTIVE"
                    if account_name:
                        account.account_name = account_name
                session.commit()
            except Exception:
                session.rollback()
                raise

    def get_token(
        self,
        workspace_id: str,
        provider: str,
        account_id: str
    ) -> Optional[Dict[str, Any]]:
        storage_key = self._make_key(workspace_id, provider, account_id)
        stored_value = self._storage.get(storage_key)

        # If absent from in-memory cache, attempt fetching from database
        if not stored_value:
            session = self._get_session()
            if session is not None:
                try:
                    from infra.db.models import ConnectedSocialAccountModel
                    account = (
                        session.query(ConnectedSocialAccountModel)
                        .filter(
                            ConnectedSocialAccountModel.workspace_id == workspace_id,
                            ConnectedSocialAccountModel.provider == provider.lower(),
                            ConnectedSocialAccountModel.account_id == account_id
                        )
                        .first()
                    )
                    if account and account.status != "REVOKED" and account.encrypted_token_blob:
                        stored_value = str(account.encrypted_token_blob)
                        self._storage[storage_key] = stored_value
                except Exception:
                    pass

        if not stored_value:
            return None

        try:
            kid = self.active_key_id
            if stored_value.startswith("{"):
                envelope = json.loads(stored_value)
                kid = envelope.get("kid", self.active_key_id)
                b64_data = envelope.get("b64", "")
                raw_blob = base64.b64decode(b64_data.encode("utf-8"))
            else:
                raw_blob = base64.b64decode(stored_value.encode("utf-8"))

            nonce = raw_blob[:12]
            ciphertext = raw_blob[12:]
            aad = workspace_id.encode("utf-8")

            cipher = self._get_cipher(kid)
            decrypted_bytes = cipher.decrypt(nonce, ciphertext, aad)
            payload = json.loads(decrypted_bytes.decode("utf-8"))

            if payload.get("expires_at"):
                payload["expires_at"] = datetime.fromisoformat(payload["expires_at"])
            return payload
        except Exception:
            # Decryption failure, unknown kid, or AAD mismatch (tenant tampering attempt)
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
        account_name = existing.get("account_name") if existing else None
        refresh = new_refresh_token or (existing.get("refresh_token") if existing else None)

        self.store_token(
            workspace_id=workspace_id,
            provider=provider,
            account_id=account_id,
            access_token=new_access_token,
            refresh_token=refresh,
            expires_at=new_expires_at,
            scopes=scopes,
            account_name=account_name
        )

    def revoke_token(
        self,
        workspace_id: str,
        provider: str,
        account_id: str
    ) -> bool:
        storage_key = self._make_key(workspace_id, provider, account_id)
        removed_memory = bool(self._storage.pop(storage_key, None) is not None)

        removed_db = False
        session = self._get_session()
        if session is not None:
            try:
                from infra.db.models import ConnectedSocialAccountModel
                account = (
                    session.query(ConnectedSocialAccountModel)
                    .filter(
                        ConnectedSocialAccountModel.workspace_id == workspace_id,
                        ConnectedSocialAccountModel.provider == provider.lower(),
                        ConnectedSocialAccountModel.account_id == account_id
                    )
                    .first()
                )
                if account:
                    account.status = "REVOKED"
                    session.delete(account)
                    session.commit()
                    removed_db = True
            except Exception:
                session.rollback()

        return removed_memory or removed_db

    def reencrypt_account(
        self,
        workspace_id: str,
        provider: str,
        account_id: str,
        target_key_id: str
    ) -> bool:
        """
        Re-encrypts an existing stored account token under a new key_id (key rotation).
        Decodes using existing key, re-encrypts with target_key_id, and commits back.
        """
        token_data = self.get_token(workspace_id, provider, account_id)
        if not token_data:
            return False

        old_active = self.active_key_id
        try:
            self.active_key_id = target_key_id
            self.store_token(
                workspace_id=workspace_id,
                provider=provider,
                account_id=account_id,
                access_token=token_data["access_token"],
                refresh_token=token_data.get("refresh_token"),
                expires_at=token_data.get("expires_at"),
                scopes=token_data.get("scopes", []),
                account_name=token_data.get("account_name")
            )
            return True
        finally:
            self.active_key_id = old_active
