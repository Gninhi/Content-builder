import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch
import httpx

from packages.connectors.social.linkedin import LinkedInSocialPublisher
from packages.connectors.social.x_twitter import XSocialPublisher
from packages.connectors.social.exceptions import (
    TokenExpiringSoonError,
    SocialPublishUnknownError,
    SocialAuthenticationError,
)
from packages.connectors.social.models import PublicationStatus


def test_t12_linkedin_connector_compliance_and_media_omission():
    """
    T12 AUDIT TEST (LinkedIn):
    1. Validation longueur [10, 3000]
    2. Alerte expiration token sous 7 jours (J-7)
    3. At-most-once : Timeout -> SocialPublishUnknownError
    4. PREUVE DE DEFAUT : Omission silencieuse des media_urls et absence de support carrousel/document.
    """
    now = datetime.now(timezone.utc)
    mock_client = MagicMock(spec=httpx.Client)

    # 1. Validation de longueur
    pub = LinkedInSocialPublisher(access_token="tok_test", sandbox_mode=False)
    with pytest.raises(ValueError, match="cannot be empty or under 10 characters"):
        pub.publish("court")
    with pytest.raises(ValueError, match="exceeds 3,000 character limit"):
        pub.publish("A" * 3005)

    # 2. Détection d'expiration proactive (J-7)
    pub_expiring = LinkedInSocialPublisher(
        access_token="tok_test",
        token_expires_at=now + timedelta(days=3),
        sandbox_mode=False
    )
    with pytest.raises(TokenExpiringSoonError, match="expires within 7 days"):
        pub_expiring.publish("Contenu valide pour LinkedIn mais token expirant bientôt.")

    # 3. Timeout réseau -> SocialPublishUnknownError
    pub_live = LinkedInSocialPublisher(
        access_token="tok_test",
        token_expires_at=now + timedelta(days=30),
        author_urn="urn:li:person:author_123",
        sandbox_mode=False
    )
    pub_live._client = mock_client
    mock_client.post.side_effect = httpx.TimeoutException("Read timeout on socket")

    with pytest.raises(SocialPublishUnknownError, match="Status is unknown; reconciliation required"):
        pub_live.publish("Contenu avec timeout de publication sur le réseau.")

    # 4. PREUVE DU DÉFAUT MEDIA (linkedin.py:180-197):
    # Les media_urls sont acceptés en paramètre mais ne sont JAMAIS injectés dans le payload HTTP
    mock_client.post.side_effect = None
    mock_resp = MagicMock()
    mock_resp.status_code = 201
    mock_resp.headers = {"x-restli-id": "urn:li:share:998877"}
    mock_client.post.return_value = mock_resp

    res = pub_live.publish(
        content="Contenu avec carrousel ou document PDF joint",
        media_urls=["https://storage.example.com/carousel_slide_1.pdf"]
    )
    assert res.status == PublicationStatus.PUBLISHED

    # Inspection du payload réellement envoyé par httpx.post (Correction FND-05)
    sent_payload = mock_client.post.call_args[1]["json"]
    assert "content" in sent_payload, "Le conteneur content doit être présent"
    assert "media" in sent_payload["content"], "Le conteneur média LinkedIn doit être généré"
    assert sent_payload["content"]["media"]["id"] == "https://storage.example.com/carousel_slide_1.pdf"

    # Vérification du rejet explicite des médias non supportés (Phase 7)
    with pytest.raises(ValueError, match="Format de média non supporté"):
        pub_live.publish(
            content="Contenu avec binaire exécutable interdit",
            media_urls=["https://storage.example.com/script.exe"]
        )


def test_t12_x_twitter_connector_weighted_length_and_cost_omission():
    """
    T12 AUDIT TEST (X / Twitter) :
    1. Pondération des URL à 23 caractères (t.co)
    2. Rejet des textes dépassant 280 caractères effectifs
    3. Rotation concurrente protégée par verrou thread-safe
    4. PREUVE DE CORRECTION REQ-20 / FND-06 :
       Calcul et affichage du coût financier estimé avant publication.
    """
    x_pub = XSocialPublisher(sandbox_mode=True)

    # 1. Pondération t.co : Une URL de 80 caractères doit compter pour 23
    long_url = "https://example.com/very/long/url/that/would/exceed/standard/limits/if/not/weighted"
    assert len(long_url) > 70
    weighted = x_pub.compute_weighted_length(f"Regardez ce rapport : {long_url}")
    # "Regardez ce rapport : " = 22 caractères + 23 caractères t.co = 45 caractères
    assert weighted == 45

    # 2. Rejet > 280 caractères
    with pytest.raises(ValueError, match="exceeds 280 characters limit"):
        x_pub.publish("A" * 285)

    # 3. Verrou de rafraîchissement présent
    assert hasattr(x_pub, "_refresh_lock"), "Verrou de rafraîchissement atomique manquant !"

    # 4. PREUVE DE CORRECTION REQ-20 / FND-06 :
    assert hasattr(x_pub, "estimate_post_cost_usd"), (
        "XSocialPublisher doit implémenter estimate_post_cost_usd pour REQ-20."
    )
    cost_text = x_pub.estimate_post_cost_usd("Simple tweet sans lien")
    assert cost_text == 0.001

    cost_link = x_pub.estimate_post_cost_usd(f"Tweet avec lien {long_url}")
    assert cost_link == 0.0015

    cost_media = x_pub.estimate_post_cost_usd("Tweet avec photo", media_urls=["https://example.com/pic.jpg"])
    assert cost_media == 0.006
