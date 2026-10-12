import pytest
from datetime import datetime, timezone, timedelta
from typing import Type
from packages.connectors.social.base import SocialPublisher
from packages.connectors.social.linkedin import LinkedInSocialPublisher
from packages.connectors.social.x_twitter import XSocialPublisher
from packages.connectors.social.sandbox import SandboxSocialPublisher
from packages.connectors.social.models import PublicationStatus, SocialProvider


@pytest.mark.parametrize("publisher_cls,provider", [
    (LinkedInSocialPublisher, SocialProvider.LINKEDIN),
    (XSocialPublisher, SocialProvider.X),
    (SandboxSocialPublisher, SocialProvider.LINKEDIN),
])
def test_social_publishers_liskov_interchangeability(publisher_cls: Type[SocialPublisher], provider: SocialProvider):
    """
    Liskov Substitution Principle (LSP) characterization test:
    Any SocialPublisher implementation must be completely interchangeable
    when executing the core contract operations (publish, schedule, get_status, delete).
    """
    if publisher_cls == SandboxSocialPublisher:
        publisher: SocialPublisher = publisher_cls(provider=provider)
    else:
        publisher = publisher_cls(sandbox_mode=True)

    assert isinstance(publisher, SocialPublisher)
    assert publisher.provider == provider

    # 1. Immediate Publication
    content = f"Characterization test message for {provider.value} #Test"
    res = publisher.publish(content=content, media_urls=["https://example.com/asset.png"])
    assert res.platform_post_id is not None
    assert res.status == PublicationStatus.PUBLISHED
    assert res.published_at is not None
    assert res.permalink_url is not None
    assert isinstance(res.platform_post_id, str)

    post_id = res.platform_post_id

    # 2. Get Status
    status = publisher.get_status(post_id)
    assert status == PublicationStatus.PUBLISHED

    # 3. Schedule Publication
    future = datetime.now(timezone.utc) + timedelta(days=3)
    sched_res = publisher.schedule(content="Scheduled content", scheduled_at=future)
    assert sched_res.platform_post_id is not None
    assert sched_res.status == PublicationStatus.SCHEDULED
    assert sched_res.scheduled_at == future

    # 4. Delete
    deleted = publisher.delete(post_id)
    assert deleted is True
    assert publisher.get_status(post_id) == PublicationStatus.DELETED
