import pytest

from cineyield.schemas.workflow import (
    TERMINAL_STATES,
    InvalidTransitionError,
    WorkflowRecord,
    WorkflowState,
    allowed_next,
    transition,
)

# --- transition() ---

def test_valid_ingested_to_analyzing():
    result = transition(WorkflowState.INGESTED, WorkflowState.ANALYZING)
    assert result == WorkflowState.ANALYZING


def test_valid_analyzing_to_scene_ready():
    result = transition(WorkflowState.ANALYZING, WorkflowState.SCENE_READY)
    assert result == WorkflowState.SCENE_READY


def test_valid_analyzing_to_blocked():
    result = transition(WorkflowState.ANALYZING, WorkflowState.BLOCKED)
    assert result == WorkflowState.BLOCKED


def test_valid_matched_to_rights_review():
    result = transition(WorkflowState.MATCHED, WorkflowState.RIGHTS_REVIEW)
    assert result == WorkflowState.RIGHTS_REVIEW


def test_valid_producer_review_to_approved():
    result = transition(WorkflowState.PRODUCER_REVIEW, WorkflowState.APPROVED)
    assert result == WorkflowState.APPROVED


def test_valid_producer_review_to_rejected():
    result = transition(WorkflowState.PRODUCER_REVIEW, WorkflowState.REJECTED)
    assert result == WorkflowState.REJECTED


# --- invalid transitions ---

def test_invalid_ingested_to_approved():
    with pytest.raises(InvalidTransitionError) as exc_info:
        transition(WorkflowState.INGESTED, WorkflowState.APPROVED)
    assert exc_info.value.from_state == WorkflowState.INGESTED
    assert exc_info.value.to_state == WorkflowState.APPROVED


def test_invalid_backwards_transition():
    with pytest.raises(InvalidTransitionError):
        transition(WorkflowState.SCENE_READY, WorkflowState.INGESTED)


def test_terminal_approved_has_no_outbound():
    with pytest.raises(InvalidTransitionError):
        transition(WorkflowState.APPROVED, WorkflowState.MATCHING)


def test_terminal_rejected_has_no_outbound():
    with pytest.raises(InvalidTransitionError):
        transition(WorkflowState.REJECTED, WorkflowState.INGESTED)


def test_terminal_blocked_has_no_outbound():
    with pytest.raises(InvalidTransitionError):
        transition(WorkflowState.BLOCKED, WorkflowState.ANALYZING)


def test_invalid_skip_state():
    with pytest.raises(InvalidTransitionError):
        transition(WorkflowState.INGESTED, WorkflowState.MATCHED)


# --- allowed_next() ---

def test_allowed_next_ingested():
    assert allowed_next(WorkflowState.INGESTED) == {WorkflowState.ANALYZING}


def test_allowed_next_terminal_is_empty():
    assert allowed_next(WorkflowState.APPROVED) == set()
    assert allowed_next(WorkflowState.REJECTED) == set()
    assert allowed_next(WorkflowState.BLOCKED) == set()


# --- WorkflowRecord ---

def test_record_starts_ingested():
    record = WorkflowRecord(asset_id="horizons")
    assert record.state == WorkflowState.INGESTED
    assert record.history == []


def test_record_advance_tracks_history():
    record = WorkflowRecord(asset_id="horizons")
    record = record.advance(WorkflowState.ANALYZING)
    assert record.state == WorkflowState.ANALYZING
    assert WorkflowState.INGESTED in record.history


def test_record_advance_full_happy_path():
    happy_path = [
        WorkflowState.ANALYZING,
        WorkflowState.SCENE_READY,
        WorkflowState.OPPORTUNITY_QUALIFIED,
        WorkflowState.MATCHING,
        WorkflowState.MATCHED,
        WorkflowState.RIGHTS_REVIEW,
        WorkflowState.CREATIVE_REVIEW,
        WorkflowState.PROPOSAL_READY,
        WorkflowState.PRODUCER_REVIEW,
        WorkflowState.APPROVED,
    ]
    record = WorkflowRecord(asset_id="horizons")
    for state in happy_path:
        record = record.advance(state)
    assert record.state == WorkflowState.APPROVED
    assert len(record.history) == len(happy_path)


def test_record_advance_invalid_raises():
    record = WorkflowRecord(asset_id="horizons")
    with pytest.raises(InvalidTransitionError):
        record.advance(WorkflowState.APPROVED)


def test_record_is_terminal():
    approved = WorkflowRecord(asset_id="x", state=WorkflowState.APPROVED)
    rejected = WorkflowRecord(asset_id="x", state=WorkflowState.REJECTED)
    blocked = WorkflowRecord(asset_id="x", state=WorkflowState.BLOCKED)
    active = WorkflowRecord(asset_id="x", state=WorkflowState.ANALYZING)

    assert approved.is_terminal
    assert rejected.is_terminal
    assert blocked.is_terminal
    assert not active.is_terminal


# --- TERMINAL_STATES ---

def test_terminal_states_set():
    assert WorkflowState.APPROVED in TERMINAL_STATES
    assert WorkflowState.REJECTED in TERMINAL_STATES
    assert WorkflowState.BLOCKED in TERMINAL_STATES
    assert WorkflowState.INGESTED not in TERMINAL_STATES
    assert WorkflowState.ANALYZING not in TERMINAL_STATES
