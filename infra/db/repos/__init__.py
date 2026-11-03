from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session


class BaseDomainRepository:
    def __init__(self, db: Session, root_repo: Any):
        self.db = db
        self._root = root_repo


class WorkspaceRepository(BaseDomainRepository):
    def create_workspace(self, name: str, timezone: str = "UTC", owner_id: str = "system", workspace_id: Optional[str] = None, is_demo: bool = False):
        return self._root.create_workspace(name=name, timezone=timezone, owner_id=owner_id, workspace_id=workspace_id, is_demo=is_demo)

    def get_workspace(self, workspace_id: str):
        return self._root.get_workspace(workspace_id)

    def ensure_workspace(self, workspace_id: str, name: Optional[str] = None, owner_id: str = "system"):
        return self._root.ensure_workspace(workspace_id=workspace_id, name=name, owner_id=owner_id)

    def create_or_version_brand_profile(self, workspace_id: str, audience: List[str], voice: str, pillars: List[str], prohibited_topics: List[str], cta_policy: Dict[str, Any]):
        return self._root.create_or_version_brand_profile(workspace_id, audience, voice, pillars, prohibited_topics, cta_policy)

    def get_latest_brand_profile(self, workspace_id: str):
        return self._root.get_latest_brand_profile(workspace_id)


class VeilleRepository(BaseDomainRepository):
    def create_veille_source(self, *args: Any, **kwargs: Any):
        return self._root.create_veille_source(*args, **kwargs)

    def list_veille_sources(self, workspace_id: str, axis: Optional[str] = None, is_active: Optional[bool] = None):
        return self._root.list_veille_sources(workspace_id=workspace_id, axis=axis, is_active=is_active)

    def save_signal(self, *args: Any, **kwargs: Any):
        return self._root.save_signal(*args, **kwargs)

    def list_signals(self, *args: Any, **kwargs: Any):
        return self._root.list_signals(*args, **kwargs)

    def create_veille_run(self, *args: Any, **kwargs: Any):
        return self._root.create_veille_run(*args, **kwargs)

    def complete_veille_run(self, *args: Any, **kwargs: Any):
        return self._root.complete_veille_run(*args, **kwargs)


class EditorialRepository(BaseDomainRepository):
    def add_source(self, *args: Any, **kwargs: Any):
        return self._root.add_source(*args, **kwargs)

    def list_sources(self, workspace_id: str, limit: int = 50):
        return self._root.list_sources(workspace_id=workspace_id, limit=limit)

    def save_idea(self, *args: Any, **kwargs: Any):
        return self._root.save_idea(*args, **kwargs)

    def list_ideas(self, workspace_id: str, status: Optional[str] = None, limit: int = 50):
        return self._root.list_ideas(workspace_id=workspace_id, status=status, limit=limit)

    def create_brief(self, *args: Any, **kwargs: Any):
        return self._root.create_brief(*args, **kwargs)

    def create_content_package(self, *args: Any, **kwargs: Any):
        return self._root.create_content_package(*args, **kwargs)

    def add_variant(self, *args: Any, **kwargs: Any):
        return self._root.add_variant(*args, **kwargs)

    def record_approval(self, *args: Any, **kwargs: Any):
        return self._root.record_approval(*args, **kwargs)


class PublishingRepository(BaseDomainRepository):
    def schedule_publication(self, *args: Any, **kwargs: Any):
        return self._root.schedule_publication(*args, **kwargs)

    def record_published_post(self, *args: Any, **kwargs: Any):
        return self._root.record_published_post(*args, **kwargs)

    def store_connected_social_account(self, *args: Any, **kwargs: Any):
        return self._root.store_connected_social_account(*args, **kwargs)

    def list_connected_social_accounts(self, workspace_id: str):
        return self._root.list_connected_social_accounts(workspace_id=workspace_id)


class AuthRepository(BaseDomainRepository):
    def get_user(self, user_id: str):
        return self._root.get_user(user_id)

    def get_user_by_email(self, email: str):
        return self._root.get_user_by_email(email)

    def create_user(self, *args: Any, **kwargs: Any):
        return self._root.create_user(*args, **kwargs)

    def record_audit_log(self, *args: Any, **kwargs: Any):
        return self._root.record_audit_log(*args, **kwargs)


class LLMSettingsRepository(BaseDomainRepository):
    def get_workspace_llm_settings(self, workspace_id: str):
        return self._root.get_workspace_llm_settings(workspace_id)

    def upsert_workspace_llm_settings(self, *args: Any, **kwargs: Any):
        return self._root.upsert_workspace_llm_settings(*args, **kwargs)


__all__ = [
    "WorkspaceRepository",
    "VeilleRepository",
    "EditorialRepository",
    "PublishingRepository",
    "AuthRepository",
    "LLMSettingsRepository",
]

