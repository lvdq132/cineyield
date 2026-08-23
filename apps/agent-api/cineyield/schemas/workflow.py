"""Deterministic workflow state machine for CineYield placement pipeline."""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class WorkflowState(str, Enum):
    INGESTED = "INGESTED"
    ANALYZING = "ANALYZING"
    SCENE_READY = "SCENE_READY"
    OPPORTUNITY_QUALIFIED = "OPPORTUNITY_QUALIFIED"
    MATCHING = "MATCHING"
    MATCHED = "MATCHED"
    RIGHTS_REVIEW = "RIGHTS_REVIEW"
    CREATIVE_REVIEW = "CREATIVE_REVIEW"
    PROPOSAL_READY = "PROPOSAL_READY"
    PRODUCER_REVIEW = "PRODUCER_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    BLOCKED = "BLOCKED"


# Valid forward transitions — only these are permitted
_TRANSITIONS: dict[WorkflowState, set[WorkflowState]] = {
    WorkflowState.INGESTED: {WorkflowState.ANALYZING},
    WorkflowState.ANALYZING: {
        WorkflowState.SCENE_READY,
        WorkflowState.BLOCKED,
    },
    WorkflowState.SCENE_READY: {
        WorkflowState.OPPORTUNITY_QUALIFIED,
        WorkflowState.BLOCKED,
    },
    WorkflowState.OPPORTUNITY_QUALIFIED: {
        WorkflowState.MATCHING,
        WorkflowState.BLOCKED,
    },
    WorkflowState.MATCHING: {
        WorkflowState.MATCHED,
        WorkflowState.BLOCKED,
    },
    WorkflowState.MATCHED: {
        WorkflowState.RIGHTS_REVIEW,
        WorkflowState.BLOCKED,
    },
    WorkflowState.RIGHTS_REVIEW: {
        WorkflowState.CREATIVE_REVIEW,
        WorkflowState.BLOCKED,
        WorkflowState.REJECTED,
    },
    WorkflowState.CREATIVE_REVIEW: {
        WorkflowState.PROPOSAL_READY,
        WorkflowState.BLOCKED,
        WorkflowState.REJECTED,
    },
    WorkflowState.PROPOSAL_READY: {WorkflowState.PRODUCER_REVIEW},
    WorkflowState.PRODUCER_REVIEW: {
        WorkflowState.APPROVED,
        WorkflowState.REJECTED,
    },
    # Terminal states — no outbound transitions
    WorkflowState.APPROVED: set(),
    WorkflowState.REJECTED: set(),
    WorkflowState.BLOCKED: set(),
}

TERMINAL_STATES = {WorkflowState.APPROVED, WorkflowState.REJECTED, WorkflowState.BLOCKED}


class InvalidTransitionError(ValueError):
    """Raised when a workflow transition is not permitted."""

    def __init__(self, from_state: WorkflowState, to_state: WorkflowState) -> None:
        super().__init__(
            f"Transition {from_state.value} → {to_state.value} is not permitted"
        )
        self.from_state = from_state
        self.to_state = to_state


def transition(current: WorkflowState, next_state: WorkflowState) -> WorkflowState:
    """Return next_state if the transition is valid; raise InvalidTransitionError otherwise."""
    allowed = _TRANSITIONS.get(current, set())
    if next_state not in allowed:
        raise InvalidTransitionError(current, next_state)
    return next_state


def allowed_next(current: WorkflowState) -> set[WorkflowState]:
    """Return the set of states reachable from current."""
    return set(_TRANSITIONS.get(current, set()))


class WorkflowRecord(BaseModel):
    asset_id: str
    state: WorkflowState = WorkflowState.INGESTED
    history: list[WorkflowState] = Field(default_factory=list)

    def advance(self, next_state: WorkflowState) -> "WorkflowRecord":
        """Return a new record with the transition applied."""
        validated = transition(self.state, next_state)
        return WorkflowRecord(
            asset_id=self.asset_id,
            state=validated,
            history=[*self.history, self.state],
        )

    @property
    def is_terminal(self) -> bool:
        return self.state in TERMINAL_STATES
