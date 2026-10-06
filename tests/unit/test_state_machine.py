import pytest
from packages.domain.state_machine import ContentStatus, ContentStateMachine, InvalidStateTransitionError


def test_valid_sequential_transitions():
    state = ContentStatus.IDEA
    state = ContentStateMachine.transition(state, ContentStatus.BRIEFED)
    assert state == ContentStatus.BRIEFED

    state = ContentStateMachine.transition(state, ContentStatus.DRAFT)
    assert state == ContentStatus.DRAFT

    state = ContentStateMachine.transition(state, ContentStatus.IN_REVIEW)
    assert state == ContentStatus.IN_REVIEW

    state = ContentStateMachine.transition(state, ContentStatus.APPROVED)
    assert state == ContentStatus.APPROVED

    state = ContentStateMachine.transition(state, ContentStatus.SCHEDULED)
    assert state == ContentStatus.SCHEDULED

    state = ContentStateMachine.transition(state, ContentStatus.PUBLISHING)
    assert state == ContentStatus.PUBLISHING

    state = ContentStateMachine.transition(state, ContentStatus.PUBLISHED)
    assert state == ContentStatus.PUBLISHED

    state = ContentStateMachine.transition(state, ContentStatus.MEASURED)
    assert state == ContentStatus.MEASURED

    state = ContentStateMachine.transition(state, ContentStatus.ARCHIVED)
    assert state == ContentStatus.ARCHIVED


def test_forbidden_transitions_raise_error():
    # 1. Draft directly to Published is strictly forbidden
    with pytest.raises(InvalidStateTransitionError):
        ContentStateMachine.transition(ContentStatus.DRAFT, ContentStatus.PUBLISHED)

    # 2. QA_FAILED directly to Scheduled is strictly forbidden
    with pytest.raises(InvalidStateTransitionError):
        ContentStateMachine.transition(ContentStatus.QA_FAILED, ContentStatus.SCHEDULED)

    # 3. Rejected directly to Published is strictly forbidden
    with pytest.raises(InvalidStateTransitionError):
        ContentStateMachine.transition(ContentStatus.REJECTED, ContentStatus.PUBLISHED)

    # 4. Draft directly to Scheduled is forbidden
    with pytest.raises(InvalidStateTransitionError):
        ContentStateMachine.transition(ContentStatus.DRAFT, ContentStatus.SCHEDULED)


def test_review_rejection_and_rewrite():
    # In review to rewrite requested
    st = ContentStateMachine.transition(ContentStatus.IN_REVIEW, ContentStatus.REWRITE_REQUESTED)
    assert st == ContentStatus.REWRITE_REQUESTED

    # Rewrite back to draft
    st = ContentStateMachine.transition(st, ContentStatus.DRAFT)
    assert st == ContentStatus.DRAFT

    # Draft back to in review
    st = ContentStateMachine.transition(st, ContentStatus.IN_REVIEW)
    assert st == ContentStatus.IN_REVIEW

    # In review to rejected
    st = ContentStateMachine.transition(st, ContentStatus.REJECTED)
    assert st == ContentStatus.REJECTED
