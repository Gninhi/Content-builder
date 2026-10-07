import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from infra.db.database import Base
from infra.db.models import WorkspaceModel, ConnectedSocialAccountModel
from packages.connectors.social.vault import EncryptedOAuthTokenVault


@pytest.fixture
def test_db_session():
    """Provides an isolated in-memory SQLite database session with all tables."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Create test workspace
    ws = WorkspaceModel(
        id="ws_vault_test",
        name="Vault Test Workspace",
        owner_id="owner_1"
    )
    session.add(ws)
    session.commit()

    yield session
    session.close()


def test_vault_encryption_at_rest_and_aad_isolation():
    """Verifies AES-GCM 256-bit encryption and strict workspace AAD binding."""
    strong_key = "a-very-strong-production-master-key-32b-minimum!"
    vault = EncryptedOAuthTokenVault(vault_key=strong_key)

    ws_id = "ws_test_tenancy"
    vault.store_token(
        workspace_id=ws_id,
        provider="linkedin",
        account_id="urn:li:person:12345",
        access_token="secret_linkedin_access_token_abc123",
        refresh_token="secret_linkedin_refresh_token_xyz789",
        expires_at=datetime.now(timezone.utc) + timedelta(days=60),
        scopes=["openid", "profile", "w_member_social"]
    )

    # Raw stored data must not contain plain text token
    storage_key = f"{ws_id}:linkedin:urn:li:person:12345"
    stored_raw = vault._storage.get(storage_key)
    assert stored_raw is not None
    assert "secret_linkedin_access_token_abc123" not in stored_raw
    assert "secret_linkedin_refresh_token_xyz789" not in stored_raw

    # Legitimate retrieval succeeds
    token_data = vault.get_token(ws_id, "linkedin", "urn:li:person:12345")
    assert token_data is not None
    assert token_data["access_token"] == "secret_linkedin_access_token_abc123"
    assert token_data["refresh_token"] == "secret_linkedin_refresh_token_xyz789"

    # Cross-tenant tampering attempt (another workspace querying or tampered AAD) fails closed
    rogue_data = vault.get_token("ws_attacker_workspace", "linkedin", "urn:li:person:12345")
    assert rogue_data is None


def test_vault_fail_closed_in_production_on_weak_or_default_key(monkeypatch):
    """Enforces fail-closed startup in production if SECRET_VAULT_KEY is default or weak."""
    monkeypatch.setenv("ENV", "production")

    # Default dev key in production -> must raise ValueError
    with pytest.raises(ValueError, match="Insecure or default SECRET_VAULT_KEY is prohibited in production"):
        EncryptedOAuthTokenVault(vault_key="default-dev-secret-vault-key-32b-min")

    # Short key in production -> must raise ValueError
    with pytest.raises(ValueError, match="Insecure or default SECRET_VAULT_KEY is prohibited in production"):
        EncryptedOAuthTokenVault(vault_key="short-key-123")

    # Strong key (>= 32 chars) succeeds
    vault = EncryptedOAuthTokenVault(vault_key="super-strong-and-secure-production-vault-key-32b-plus!")
    assert vault is not None


def test_vault_key_rotation_with_kid():
    """Verifies cryptographic key rotation from kid v1 to v2 without data loss."""
    key_v1 = "initial-primary-vault-key-32-chars-long!"
    key_v2 = "rotated-secondary-vault-key-32-chars-long!"

    key_ring = {
        "v1": key_v1,
        "v2": key_v2
    }

    # Initialize vault with v1 active
    vault = EncryptedOAuthTokenVault(
        key_ring=key_ring,
        active_key_id="v1"
    )

    ws_id = "ws_rotate_test"
    vault.store_token(
        workspace_id=ws_id,
        provider="x",
        account_id="twitter_user_123",
        access_token="initial_x_token_abc",
        refresh_token="initial_x_refresh_def"
    )

    # Initial token was encrypted with v1
    storage_key = f"{ws_id}:x:twitter_user_123"
    assert '"kid": "v1"' in vault._storage[storage_key]

    # Rotate account to v2
    reencrypted = vault.reencrypt_account(
        workspace_id=ws_id,
        provider="x",
        account_id="twitter_user_123",
        target_key_id="v2"
    )
    assert reencrypted is True
    assert '"kid": "v2"' in vault._storage[storage_key]

    # Verify retrieval still works seamlessly with key v2
    decrypted = vault.get_token(ws_id, "x", "twitter_user_123")
    assert decrypted is not None
    assert decrypted["access_token"] == "initial_x_token_abc"

    # Simulate decommissioning old key v1 from key ring
    decommissioned_key_ring = {"v2": key_v2}
    new_vault = EncryptedOAuthTokenVault(
        key_ring=decommissioned_key_ring,
        active_key_id="v2"
    )
    new_vault._storage[storage_key] = vault._storage[storage_key]
    assert new_vault.get_token(ws_id, "x", "twitter_user_123")["access_token"] == "initial_x_token_abc"


def test_vault_database_persistence_and_retrieval(test_db_session):
    """Proves persistence in ConnectedSocialAccountModel and retrieval across vault instances."""
    vault_key = "durable-database-vault-encryption-key-32b!"
    vault1 = EncryptedOAuthTokenVault(vault_key=vault_key, db_session=test_db_session)

    ws_id = "ws_vault_test"
    vault1.store_token(
        workspace_id=ws_id,
        provider="linkedin",
        account_id="urn:li:person:persist123",
        account_name="Jane Doe",
        access_token="db_persisted_access_token",
        refresh_token="db_persisted_refresh_token",
        scopes=["openid", "profile"]
    )

    # Check model directly in SQLite
    row = (
        test_db_session.query(ConnectedSocialAccountModel)
        .filter(
            ConnectedSocialAccountModel.workspace_id == ws_id,
            ConnectedSocialAccountModel.provider == "linkedin",
            ConnectedSocialAccountModel.account_id == "urn:li:person:persist123"
        )
        .first()
    )
    assert row is not None
    assert row.account_name == "Jane Doe"
    assert row.status == "ACTIVE"
    assert row.key_id == "v1"
    assert "db_persisted_access_token" not in row.encrypted_token_blob

    # Create a fresh, second vault instance (empty in-memory cache) sharing same DB session
    vault2 = EncryptedOAuthTokenVault(vault_key=vault_key, db_session=test_db_session)
    assert len(vault2._storage) == 0

    # Retrieve from DB through vault2
    retrieved = vault2.get_token(ws_id, "linkedin", "urn:li:person:persist123")
    assert retrieved is not None
    assert retrieved["access_token"] == "db_persisted_access_token"
    assert retrieved["account_name"] == "Jane Doe"

    # Test revocation
    revoked = vault2.revoke_token(ws_id, "linkedin", "urn:li:person:persist123")
    assert revoked is True
    assert vault2.get_token(ws_id, "linkedin", "urn:li:person:persist123") is None

    # DB record is purged
    deleted_row = (
        test_db_session.query(ConnectedSocialAccountModel)
        .filter(ConnectedSocialAccountModel.account_id == "urn:li:person:persist123")
        .first()
    )
    assert deleted_row is None
