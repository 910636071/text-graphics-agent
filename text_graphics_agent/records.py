"""Normalized records for the Text Graphics Agent prototype."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal


Visibility = Literal["internal", "review", "public"]
ProposalKind = Literal["analysis", "patch_plan", "expression", "test_plan"]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class RecordEnvelope:
    """Minimal checked-record envelope.

    This mirrors the project EventLog discipline but is kept independent from
    the game database.
    """

    record_schema_version: str
    actor: str
    target: str
    cause: str
    result: str
    visibility: Visibility
    scope_id: str
    source_record_id: str | None = None
    timestamp: str = field(default_factory=utc_now_iso)

    @classmethod
    def for_task(cls, *, actor: str, target: str, cause: str, scope_id: str) -> "RecordEnvelope":
        return cls(
            record_schema_version="tga.record.v1",
            actor=actor,
            target=target,
            cause=cause,
            result="proposed",
            visibility="review",
            scope_id=scope_id,
        )


@dataclass(frozen=True)
class TaskSpec:
    task_id: str
    objective: str
    allowed_scopes: tuple[str, ...]
    required_anchors: tuple[str, ...] = ()
    forbidden_outputs: tuple[str, ...] = (
        "committed_fact",
        "confirmed_fact",
        "direct_ledger_write",
        "new_action_type",
        "secret_access",
    )
    requires_tests: bool = True
    sanitized: bool = False
    sanitized_provenance: str = ""
    mother_notes: tuple[str, ...] = ()


@dataclass(frozen=True)
class AgentProposal:
    envelope: RecordEnvelope
    task_id: str
    child_agent_id: str
    child_role: str
    proposal_kind: ProposalKind
    claim: str
    evidence: tuple[str, ...]
    proposed_scopes: tuple[str, ...] = ()
    proposed_outputs: tuple[str, ...] = ()
    required_anchor_text: str = ""
    test_commands: tuple[str, ...] = ()
    confidence: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ChildSessionRecord:
    """Auditable lifecycle for a disposable child agent call."""

    child_agent_id: str
    task_id: str
    role: str
    opened_at: str
    closed_at: str | None = None
    status: Literal["open", "destroyed", "failed"] = "open"
    proposal_count: int = 0

    @classmethod
    def open(cls, *, child_agent_id: str, task_id: str, role: str) -> "ChildSessionRecord":
        return cls(
            child_agent_id=child_agent_id,
            task_id=task_id,
            role=role,
            opened_at=utc_now_iso(),
        )

    def close(self, *, proposal_count: int, failed: bool = False) -> "ChildSessionRecord":
        return ChildSessionRecord(
            child_agent_id=self.child_agent_id,
            task_id=self.task_id,
            role=self.role,
            opened_at=self.opened_at,
            closed_at=utc_now_iso(),
            status="failed" if failed else "destroyed",
            proposal_count=proposal_count,
        )


@dataclass(frozen=True)
class CheckedRecord:
    proposal: AgentProposal
    accepted: bool
    violations: tuple[str, ...]
    reviewer: str = "constraint-checker:v1"

    @property
    def status(self) -> str:
        return "accepted" if self.accepted else "rejected"
