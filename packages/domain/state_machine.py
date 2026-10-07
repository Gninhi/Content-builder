from enum import Enum
from typing import Set, Dict


class ContentStatus(str, Enum):
    IDEA = "IDEA"
    BRIEFED = "BRIEFED"
    DRAFT = "DRAFT"
    QA_FAILED = "QA_FAILED"
    IN_REVIEW = "IN_REVIEW"
    PENDING_REVIEW = "IN_REVIEW"  # Standard lifecycle alias
    REWRITE_REQUESTED = "REWRITE_REQUESTED"
    REJECTED = "REJECTED"
    APPROVED = "APPROVED"
    SCHEDULED = "SCHEDULED"
    PUBLISHING = "PUBLISHING"
    PUBLISHED = "PUBLISHED"
    PUBLISH_FAILED = "PUBLISH_FAILED"
    FAILED = "PUBLISH_FAILED"  # Standard failure alias
    MEASURED = "MEASURED"
    ARCHIVED = "ARCHIVED"

    @classmethod
    def parse(cls, value: "str | ContentStatus") -> "ContentStatus":
        if isinstance(value, ContentStatus):
            return value
        cleaned = value.strip().upper()
        if cleaned in ("PENDING_REVIEW", "PENDING"):
            return cls.IN_REVIEW
        if cleaned == "FAILED":
            return cls.PUBLISH_FAILED
        return cls(cleaned)


class InvalidStateTransitionError(Exception):
    """Raised when an illegal state transition is attempted."""
    def __init__(self, from_state: ContentStatus, to_state: ContentStatus, reason: str = ""):
        self.from_state = from_state
        self.to_state = to_state
        self.reason = reason
        super().__init__(
            f"Invalid state transition from {from_state.value} to {to_state.value}"
            + (f": {reason}" if reason else "")
        )


class ContentStateMachine:
    """
    Enforces the editorial state machine rules defined in the PRD.
    
    Allowed flow:
    IDEA -> BRIEFED -> DRAFT -> QA_FAILED / IN_REVIEW
    IN_REVIEW -> REWRITE_REQUESTED -> DRAFT
    IN_REVIEW -> REJECTED
    IN_REVIEW -> APPROVED -> SCHEDULED -> PUBLISHING
    PUBLISHING -> PUBLISHED / PUBLISH_FAILED
    PUBLISHED -> MEASURED -> ARCHIVED
    """

    ALLOWED_TRANSITIONS: Dict[ContentStatus, Set[ContentStatus]] = {
        ContentStatus.IDEA: {ContentStatus.BRIEFED, ContentStatus.ARCHIVED},
        ContentStatus.BRIEFED: {ContentStatus.DRAFT, ContentStatus.ARCHIVED},
        ContentStatus.DRAFT: {ContentStatus.QA_FAILED, ContentStatus.IN_REVIEW},
        ContentStatus.QA_FAILED: {ContentStatus.DRAFT, ContentStatus.ARCHIVED},
        ContentStatus.IN_REVIEW: {
            ContentStatus.REWRITE_REQUESTED,
            ContentStatus.REJECTED,
            ContentStatus.APPROVED,
        },
        ContentStatus.REWRITE_REQUESTED: {ContentStatus.DRAFT},
        ContentStatus.REJECTED: {ContentStatus.ARCHIVED},
        ContentStatus.APPROVED: {ContentStatus.SCHEDULED, ContentStatus.ARCHIVED},
        ContentStatus.SCHEDULED: {ContentStatus.PUBLISHING, ContentStatus.APPROVED, ContentStatus.ARCHIVED},
        ContentStatus.PUBLISHING: {ContentStatus.PUBLISHED, ContentStatus.PUBLISH_FAILED},
        ContentStatus.PUBLISH_FAILED: {ContentStatus.SCHEDULED, ContentStatus.ARCHIVED},
        ContentStatus.PUBLISHED: {ContentStatus.MEASURED, ContentStatus.ARCHIVED},
        ContentStatus.MEASURED: {ContentStatus.ARCHIVED},
        ContentStatus.ARCHIVED: set(),
    }

    # Strict prohibitions from PRD Section 4.3:
    # Transitions interdites : Draft vers Published ; QA_FAILED vers Scheduled ;
    # Rejected vers Published ; publication sans approbation liée à la version exacte.
    FORBIDDEN_TRANSITIONS: Set[tuple[ContentStatus, ContentStatus]] = {
        (ContentStatus.DRAFT, ContentStatus.PUBLISHED),
        (ContentStatus.QA_FAILED, ContentStatus.SCHEDULED),
        (ContentStatus.REJECTED, ContentStatus.PUBLISHED),
        (ContentStatus.DRAFT, ContentStatus.SCHEDULED),
        (ContentStatus.IN_REVIEW, ContentStatus.PUBLISHED),
    }

    @classmethod
    def can_transition(cls, current_state: ContentStatus, next_state: ContentStatus) -> bool:
        if (current_state, next_state) in cls.FORBIDDEN_TRANSITIONS:
            return False
        return next_state in cls.ALLOWED_TRANSITIONS.get(current_state, set())

    @classmethod
    def transition(cls, current_state: ContentStatus, next_state: ContentStatus, context: dict | None = None) -> ContentStatus:
        if not cls.can_transition(current_state, next_state):
            raise InvalidStateTransitionError(
                current_state,
                next_state,
                reason="Direct transition forbidden by editorial governance policy."
            )
        return next_state
