import time
from datetime import datetime, timezone, timedelta
import httpx
import pytest

from packages.connectors.social.models import (
    SocialProvider,
    PublicationStatus,
)
from packages.connectors.social.linkedin import LinkedInSocialPublisher
from packages.connectors.social.x_twitter import XSocialPublisher
from packages.connectors.social.exceptions import (
    SocialAuthenticationError,
    SocialPermissionError,
    SocialRateLimitError,
    SocialBillingError,
    SocialDuplicateError,
    SocialPublishUnknownError,
    TokenExpiringSoonError,
)
from tests.unit.test_social_ready_contracts import BaseSocialPublisherContractTest


class TestSocialPublisherContracts:
    """Verifies that LinkedInSocialPublisher and XSocialPublisher strictly conform to the contract."""

    def test_linkedin_publisher_adheres_to_contract(self):
        publisher = LinkedInSocialPublisher(sandbox_mode=True)
        tester = BaseSocialPublisherContractTest()
        tester.assert_publisher_conforms(publisher)

    def test_x_publisher_adheres_to_contract(self):
        publisher = XSocialPublisher(sandbox_mode=True)
        tester = BaseSocialPublisherContractTest()
        tester.assert_publisher_conforms(publisher)


class TestLinkedInSocialPublisherLiveMocked:
    """Tests live HTTP interactions of LinkedInSocialPublisher using MockTransport."""

    def test_linkedin_publish_success_with_version_and_restli_headers(self):
        def handler(request: httpx.Request):
            assert request.method == "POST"
            assert str(request.url) == "https://api.linkedin.com/rest/posts"
            assert request.headers["LinkedIn-Version"] == "202601"
            assert request.headers["X-Restli-Protocol-Version"] == "2.0.0"
            assert request.headers["Authorization"] == "Bearer test_access_token"
            
            headers = {"x-restli-id": "urn:li:share:9876543210"}
            return httpx.Response(201, headers=headers, json={"id": "urn:li:share:9876543210"})

        transport = httpx.MockTransport(handler)
        client = httpx.Client(transport=transport)

        publisher = LinkedInSocialPublisher(
            access_token="test_access_token",
            author_urn="urn:li:person:sub_123",
            api_version="202601",
            sandbox_mode=False,
            http_client=client
        )

        res = publisher.publish(content="State-of-the-art production engineering with LangGraph and AI agents.")
        assert res.platform_post_id == "urn:li:share:9876543210"
        assert res.status == PublicationStatus.PUBLISHED
        assert res.permalink_url == "https://www.linkedin.com/feed/update/urn:li:share:9876543210"

    def test_linkedin_author_resolution_via_userinfo(self):
        def handler(request: httpx.Request):
            if str(request.url) == "https://api.linkedin.com/v2/userinfo":
                return httpx.Response(200, json={"sub": "openid_sub_789", "name": "Alice Dev"})
            elif str(request.url) == "https://api.linkedin.com/rest/posts":
                return httpx.Response(201, headers={"x-restli-id": "urn:li:share:auto_urn_111"})
            return httpx.Response(404)

        transport = httpx.MockTransport(handler)
        client = httpx.Client(transport=transport)

        publisher = LinkedInSocialPublisher(
            access_token="test_token",
            sandbox_mode=False,
            http_client=client
        )

        res = publisher.publish(content="Automated author resolution via OpenID Connect userinfo.")
        assert res.platform_post_id == "urn:li:share:auto_urn_111"
        assert publisher.author_urn == "urn:li:person:openid_sub_789"

    def test_linkedin_token_expiring_soon_alert(self):
        # Token expiring in 3 days (< 7 days threshold)
        near_expiry = datetime.now(timezone.utc) + timedelta(days=3)
        publisher = LinkedInSocialPublisher(
            access_token="test_token",
            token_expires_at=near_expiry,
            sandbox_mode=False
        )

        with pytest.raises(TokenExpiringSoonError) as exc_info:
            publisher.publish(content="This should fail before sending due to J-7 threshold.")
        assert "expires within 7 days" in str(exc_info.value)

    def test_linkedin_error_status_mappings(self):
        # 401 Unauthorized
        client_401 = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(401, text="Invalid token")))
        pub_401 = LinkedInSocialPublisher(access_token="tok", author_urn="urn:li:person:1", sandbox_mode=False, http_client=client_401)
        with pytest.raises(SocialAuthenticationError):
            pub_401.publish(content="Testing 401 unauthorized handling.")

        # 403 Forbidden
        client_403 = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(403, text="Scope missing")))
        pub_403 = LinkedInSocialPublisher(access_token="tok", author_urn="urn:li:person:1", sandbox_mode=False, http_client=client_403)
        with pytest.raises(SocialPermissionError):
            pub_403.publish(content="Testing 403 forbidden handling.")

        # 429 Rate Limit
        client_429 = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(429, headers={"Retry-After": "120"})))
        pub_429 = LinkedInSocialPublisher(access_token="tok", author_urn="urn:li:person:1", sandbox_mode=False, http_client=client_429)
        with pytest.raises(SocialRateLimitError) as exc_429:
            pub_429.publish(content="Testing 429 rate limit handling.")
        assert exc_429.value.retry_after == 120

        # Timeout -> SocialPublishUnknownError (at-most-once safety)
        def timeout_handler(r):
            raise httpx.ReadTimeout("Connection timed out after request sent")

        client_timeout = httpx.Client(transport=httpx.MockTransport(timeout_handler))
        pub_timeout = LinkedInSocialPublisher(access_token="tok", author_urn="urn:li:person:1", sandbox_mode=False, http_client=client_timeout)
        with pytest.raises(SocialPublishUnknownError):
            pub_timeout.publish(content="Testing network timeout conversion to publish unknown.")


class TestXSocialPublisherLiveMocked:
    """Tests live HTTP interactions of XSocialPublisher using MockTransport."""

    def test_x_publish_success(self):
        def handler(request: httpx.Request):
            assert request.method == "POST"
            assert str(request.url) == "https://api.x.com/2/tweets"
            assert request.headers["Authorization"] == "Bearer x_token_123"
            return httpx.Response(201, json={"data": {"id": "184321987654321", "text": "Post text"}})

        transport = httpx.MockTransport(handler)
        client = httpx.Client(transport=transport)

        publisher = XSocialPublisher(
            access_token="x_token_123",
            sandbox_mode=False,
            http_client=client
        )

        res = publisher.publish(content="Shipping resilient agentic pipelines on X.")
        assert res.platform_post_id == "184321987654321"
        assert res.status == PublicationStatus.PUBLISHED
        assert res.permalink_url == "https://x.com/user/status/184321987654321"

    def test_x_automatic_token_refresh_and_rotation(self):
        refreshed_tokens = []

        def on_refreshed(acc_tok, ref_tok, exp_at):
            refreshed_tokens.append((acc_tok, ref_tok, exp_at))

        def handler(request: httpx.Request):
            if str(request.url) == "https://api.x.com/2/oauth2/token":
                return httpx.Response(200, json={
                    "access_token": "new_access_token_rotated",
                    "refresh_token": "new_refresh_token_rotated",
                    "expires_in": 7200
                })
            elif str(request.url) == "https://api.x.com/2/tweets":
                assert request.headers["Authorization"] == "Bearer new_access_token_rotated"
                return httpx.Response(201, json={"data": {"id": "999888777", "text": "OK"}})
            return httpx.Response(404)

        transport = httpx.MockTransport(handler)
        client = httpx.Client(transport=transport)

        # Expired token requiring refresh
        expired_time = datetime.now(timezone.utc) - timedelta(minutes=5)
        publisher = XSocialPublisher(
            access_token="stale_token",
            refresh_token="valid_refresh_token",
            token_expires_at=expired_time,
            client_id="x_client_id_app",
            client_secret="x_client_secret_app",
            on_token_refreshed=on_refreshed,
            sandbox_mode=False,
            http_client=client
        )

        res = publisher.publish(content="Testing automatic token refresh with PKCE rotation.")
        assert res.platform_post_id == "999888777"
        assert publisher.access_token == "new_access_token_rotated"
        assert publisher.refresh_token == "new_refresh_token_rotated"
        assert len(refreshed_tokens) == 1

    def test_x_monthly_ceiling_guardrail(self):
        publisher = XSocialPublisher(
            access_token="tok",
            monthly_limit=5,
            current_month_publications=5,
            sandbox_mode=False
        )

        with pytest.raises(SocialBillingError) as exc_info:
            publisher.publish(content="Exceeding monthly publication ceiling.")
        assert "Monthly publication ceiling reached" in str(exc_info.value)

    def test_x_error_mappings(self):
        # 402 Billing
        client_402 = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(402, text="Credits exhausted")))
        pub_402 = XSocialPublisher(access_token="tok", sandbox_mode=False, http_client=client_402)
        with pytest.raises(SocialBillingError):
            pub_402.publish(content="Testing 402 payment required.")

        # 403 Duplicate
        client_dup = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(403, text="Status is a duplicate.")))
        pub_dup = XSocialPublisher(access_token="tok", sandbox_mode=False, http_client=client_dup)
        with pytest.raises(SocialDuplicateError):
            pub_dup.publish(content="Testing duplicate tweet rejection.")

        # 429 Rate Limit with x-rate-limit-reset header
        reset_time = int(time.time()) + 60
        client_429 = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(429, headers={"x-rate-limit-reset": str(reset_time)})))
        pub_429 = XSocialPublisher(access_token="tok", sandbox_mode=False, http_client=client_429)
        with pytest.raises(SocialRateLimitError) as exc_429:
            pub_429.publish(content="Testing 429 rate limit reset header.")
        assert exc_429.value.retry_after is not None
        assert exc_429.value.retry_after <= 60
