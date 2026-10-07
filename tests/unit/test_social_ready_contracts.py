from datetime import datetime, timezone, timedelta
from packages.connectors.social.models import (
    SocialProvider,
    PublicationStatus,
    SocialAccountStatus,
    ConnectedSocialAccount
)
from packages.connectors.social.base import SocialPublisher
from packages.connectors.social.sandbox import SandboxSocialPublisher
from packages.connectors.social.vault import EncryptedOAuthTokenVault


class BaseSocialPublisherContractTest:
    """Reusable contract test suite applicable to any SocialPublisher implementation."""

    def assert_publisher_conforms(self, publisher: SocialPublisher):
        # 1. Immediate publication
        pub_res = publisher.publish(
            content="Hello world from contract test #AI",
            media_urls=["https://example.com/image.png"]
        )
        assert pub_res.platform_post_id is not None
        assert pub_res.status == PublicationStatus.PUBLISHED
        assert pub_res.published_at is not None
        assert pub_res.permalink_url is not None

        # 2. Status verification
        status = publisher.get_status(pub_res.platform_post_id)
        assert status == PublicationStatus.PUBLISHED

        # 3. Scheduled publication
        future_time = datetime.now(timezone.utc) + timedelta(days=2)
        sched_res = publisher.schedule(
            content="Scheduled future announcement",
            scheduled_at=future_time
        )
        assert sched_res.platform_post_id is not None
        assert sched_res.status == PublicationStatus.SCHEDULED
        assert sched_res.scheduled_at == future_time

        # 4. Deletion
        assert publisher.delete(pub_res.platform_post_id) is True
        assert publisher.get_status(pub_res.platform_post_id) == PublicationStatus.DELETED


def test_sandbox_social_publisher_adheres_to_contract():
    """Validates SandboxSocialPublisher against the reusable SocialPublisher contract."""
    publisher = SandboxSocialPublisher(provider=SocialProvider.LINKEDIN)
    tester = BaseSocialPublisherContractTest()
    tester.assert_publisher_conforms(publisher)


def test_connected_social_account_schema():
    """Validates the ConnectedSocialAccount data model schema."""
    now = datetime.now(timezone.utc)
    account = ConnectedSocialAccount(
        id="acc_123",
        workspace_id="ws_main",
        provider=SocialProvider.X,
        account_id="@tech_insights",
        account_name="Tech Insights Official",
        granted_scopes=["tweet.read", "tweet.write", "users.read"],
        status=SocialAccountStatus.ACTIVE,
        token_expires_at=now + timedelta(hours=2),
        connected_at=now
    )
    assert account.provider == SocialProvider.X
    assert account.status == SocialAccountStatus.ACTIVE
    assert "tweet.write" in account.granted_scopes


def test_oauth_token_vault_encryption_at_rest():
    """Verifies that tokens stored in EncryptedOAuthTokenVault are encrypted at rest."""
    vault = EncryptedOAuthTokenVault(vault_key="super-secret-vault-master-key-32b!")
    ws = "ws_finance"
    provider = "linkedin"
    account = "acc_linkedin_corporate"
    raw_token = "secret_access_token_super_confidential_12345"

    vault.store_token(
        workspace_id=ws,
        provider=provider,
        account_id=account,
        access_token=raw_token,
        refresh_token="secret_refresh_token_xyz",
        scopes=["w_member_social", "r_liteprofile"]
    )

    # 1. Check raw stored storage: must NOT contain plaintext access token
    storage_key = f"{ws}:{provider}:{account}"
    encrypted_blob = vault._storage[storage_key]
    assert raw_token not in encrypted_blob

    # 2. Retrieve and decrypt
    record = vault.get_token(ws, provider, account)
    assert record is not None
    assert record["access_token"] == raw_token
    assert record["refresh_token"] == "secret_refresh_token_xyz"
    assert "w_member_social" in record["scopes"]


def test_oauth_token_vault_rotation_and_revocation():
    """Verifies token rotation and revocation in the encrypted vault."""
    vault = EncryptedOAuthTokenVault()
    ws = "ws_test"
    provider = "x"
    account = "@brand_account"

    vault.store_token(ws, provider, account, access_token="token_v1")
    assert vault.get_token(ws, provider, account)["access_token"] == "token_v1"

    # Rotate
    vault.rotate_token(ws, provider, account, new_access_token="token_v2_rotated")
    assert vault.get_token(ws, provider, account)["access_token"] == "token_v2_rotated"

    # Revoke
    assert vault.revoke_token(ws, provider, account) is True
    assert vault.get_token(ws, provider, account) is None
    assert vault.revoke_token(ws, provider, account) is False


def test_oauth_token_vault_strict_tenant_isolation():
    """Verifies that Workspace A cannot access, decrypt, or tamper with Workspace B's token."""
    vault = EncryptedOAuthTokenVault()
    ws_a = "ws_alpha"
    ws_b = "ws_beta"
    provider = "linkedin"
    account = "common_account_id"

    vault.store_token(ws_a, provider, account, access_token="alpha_secret_token")

    # Workspace B querying the same account must receive None
    assert vault.get_token(ws_b, provider, account) is None

    # Tampering attack: Workspace B copies the ciphertext from A into its own storage key
    key_a = vault._make_key(ws_a, provider, account)
    key_b = vault._make_key(ws_b, provider, account)
    vault._storage[key_b] = vault._storage[key_a]

    # Because AES-GCM authenticates workspace_id as AAD, decrypting with ws_b will fail!
    assert vault.get_token(ws_b, provider, account) is None
