import pytest
from unittest.mock import MagicMock
from datetime import datetime, timezone

from packages.connectors.social.vault import EncryptedOAuthTokenVault
from packages.connectors.social.x_twitter import XSocialPublisher
from packages.connectors.social.exceptions import SocialBillingError
from packages.tools.web_search import _SEARCH_CACHE


def test_t8_tenant_isolation_vault_and_database():
    """
    T8 AUDIT TEST: Isolation multi-tenant et protection cryptographique AAD.
    Vérifie que les données et jetons d'un workspace ne peuvent pas fuiter vers un autre.
    """
    mock_db = MagicMock()
    vault = EncryptedOAuthTokenVault(db_session=mock_db)

    # 1. Chiffrement avec workspace_id comme AAD (Authenticated Additional Data)
    raw_token = "ghp_super_secret_oauth_token_12345"
    vault.store_token(
        workspace_id="ws_alpha",
        provider="linkedin",
        account_id="acc_123",
        access_token=raw_token
    )

    # Récupération avec le bon tenant : succès
    record = vault.get_token(workspace_id="ws_alpha", provider="linkedin", account_id="acc_123")
    assert record is not None
    assert record["access_token"] == raw_token

    # Tentative d'accès cross-tenant avec un workspace_id différent (BOLA / IDOR)
    cross_record = vault.get_token(workspace_id="ws_beta", provider="linkedin", account_id="acc_123")
    assert cross_record is None, "Fuite inter-tenant : un workspace différent a pu accéder aux données !"


def test_t9_budget_exhaustion_and_guardrails():
    """
    T9 AUDIT TEST: Épuisement des budgets et garde-fous FinOps.
    Vérifie le blocage immédiat des publications X au plafond mensuel
    et le comptage budgétaire de recherche web.
    """
    # 1. Garde-fou X : SocialBillingError déclenché dès que current_month_publications >= monthly_limit
    publisher = XSocialPublisher(sandbox_mode=True, monthly_limit=5)
    publisher.current_month_publications = 5

    with pytest.raises(SocialBillingError, match="Monthly publication ceiling reached for X"):
        publisher.publish(content="Message test qui doit être bloqué par le garde-fou budgétaire")

    # 2. Suivi de consommation par workspace pour SerpAPI
    cost1 = _SEARCH_CACHE.increment_budget(workspace_id="ws_finops_audit", cost=0.01)
    cost2 = _SEARCH_CACHE.increment_budget(workspace_id="ws_finops_audit", cost=0.01)
    assert cost2 >= cost1 + 1
