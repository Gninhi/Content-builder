from fastapi import APIRouter, Depends
from typing import Dict, Any
from infra.db.repository import ContentOpsRepository
from apps.api.dependencies import get_repository, UserContext, require_roles

router = APIRouter(tags=["Editorial Calendar"])


@router.get("/v1/calendar")
def get_editorial_calendar(
    repo: ContentOpsRepository = Depends(get_repository),
    user: UserContext = Depends(require_roles("Owner", "Editor", "Viewer", "ServiceAgent"))
) -> Dict[str, Any]:
    return repo.get_editorial_calendar(user.workspace_id)
