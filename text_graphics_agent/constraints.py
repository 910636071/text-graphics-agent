"""Finite checks for disposable child-agent proposals."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from .records import AgentProposal, CheckedRecord, TaskSpec


_FORBIDDEN_METADATA_KEYS = {
    "raw_user_text",
    "raw_text",
    "raw_request",
    "atomic_intents",
    "user_supplied_claims",
}


class Constraint:
    """Abstract base class for all semantic firewall constraints."""
    constraint_id: str = ""

    def check(self, task: TaskSpec, proposal: AgentProposal) -> list[str]:
        """Returns a list of violation codes. Empty list means validation passed."""
        raise NotImplementedError


class EnvelopeConstraint(Constraint):
    """Checks the RecordEnvelope parameters for schema version, field validity, and timestamps."""
    constraint_id: str = "envelope"

    def check(self, task: TaskSpec, proposal: AgentProposal) -> list[str]:
        violations: list[str] = []
        envelope = proposal.envelope
        if envelope.record_schema_version != "tga.record.v1":
            violations.append("bad_record_schema_version")
        for field_name in ("actor", "target", "cause", "result", "scope_id"):
            value = getattr(envelope, field_name)
            if not isinstance(value, str) or not value.strip():
                violations.append(f"bad_envelope:{field_name}")
        if envelope.visibility not in {"internal", "review", "public"}:
            violations.append("bad_envelope:visibility")
        try:
            datetime.fromisoformat(envelope.timestamp)
        except ValueError:
            violations.append("bad_envelope:timestamp")
        return violations


class TaskMismatchConstraint(Constraint):
    """Ensures that the proposal references the correct TaskSpec ID."""
    constraint_id: str = "task_mismatch"

    def check(self, task: TaskSpec, proposal: AgentProposal) -> list[str]:
        if proposal.task_id != task.task_id:
            return ["task_mismatch"]
        return []


class SanitizedTaskConstraint(Constraint):
    """Verifies that the task was properly sanitized by the mother agent."""
    constraint_id: str = "sanitized_task"

    def check(self, task: TaskSpec, proposal: AgentProposal) -> list[str]:
        violations: list[str] = []
        if not task.sanitized:
            violations.append("task_not_sanitized")
        if task.sanitized_provenance != "mother_clean_v1":
            violations.append("bad_sanitized_provenance")
        return violations


class AuthorityConstraint(Constraint):
    """Ensures the disposable child agent does not try to claim high-privileged roles."""
    constraint_id: str = "authority"

    def check(self, task: TaskSpec, proposal: AgentProposal) -> list[str]:
        if proposal.child_role.lower() in {"mother", "orchestrator", "ledger"}:
            return ["mother_may_not_author"]
        return []


class MetadataLeakConstraint(Constraint):
    """Recursively checks metadata structure to ensure raw user texts do not leak to the child."""
    constraint_id: str = "metadata_leak"

    def check(self, task: TaskSpec, proposal: AgentProposal) -> list[str]:
        if self._metadata_has_forbidden_key(proposal.metadata):
            return ["raw_user_text_leaked_to_child"]
        return []

    def _metadata_has_forbidden_key(self, value: Any) -> bool:
        if isinstance(value, dict):
            for key, child in value.items():
                if str(key) in _FORBIDDEN_METADATA_KEYS:
                    return True
                if self._metadata_has_forbidden_key(child):
                    return True
        elif isinstance(value, (list, tuple)):
            return any(self._metadata_has_forbidden_key(child) for child in value)
        return False


class ClaimConstraint(Constraint):
    """Ensures the proposal claim is not empty."""
    constraint_id: str = "claim"

    def check(self, task: TaskSpec, proposal: AgentProposal) -> list[str]:
        if not proposal.claim.strip():
            return ["empty_claim"]
        return []


class EvidenceConstraint(Constraint):
    """Ensures that evidence is provided, and is not solely based on raw user semantics."""
    constraint_id: str = "evidence"

    def check(self, task: TaskSpec, proposal: AgentProposal) -> list[str]:
        if not proposal.evidence:
            return ["missing_evidence"]
        if all(item.startswith("user:") for item in proposal.evidence):
            return ["user_semantics_only"]
        return []


class TestConstraint(Constraint):
    """Ensures the child supplies verification/test commands if the task requires tests."""
    constraint_id: str = "test"

    def check(self, task: TaskSpec, proposal: AgentProposal) -> list[str]:
        if task.requires_tests and not proposal.test_commands:
            return ["missing_test_commands"]
        return []


class ScopeConstraint(Constraint):
    """Enforces boundaries. The proposal must not touch scopes outside the TaskSpec's whitelist."""
    constraint_id: str = "scope"

    def check(self, task: TaskSpec, proposal: AgentProposal) -> list[str]:
        violations: list[str] = []
        allowed = set(task.allowed_scopes)
        for scope in proposal.proposed_scopes:
            if scope not in allowed and not any(
                scope.startswith(prefix.rstrip("*")) for prefix in allowed if prefix.endswith("*")
            ):
                violations.append(f"scope_escape:{scope}")
        return violations


class ForbiddenOutputConstraint(Constraint):
    """Ensures the child does not try to emit forbidden outputs (like writing direct facts)."""
    constraint_id: str = "forbidden_output"

    def check(self, task: TaskSpec, proposal: AgentProposal) -> list[str]:
        violations: list[str] = []
        forbidden = set(task.forbidden_outputs)
        for output in proposal.proposed_outputs:
            if output in forbidden:
                violations.append(f"forbidden_output:{output}")
        return violations


class AnchorConstraint(Constraint):
    """Ensures that the output contains all the mandatory semantic anchors requested by the task."""
    constraint_id: str = "anchor"

    def check(self, task: TaskSpec, proposal: AgentProposal) -> list[str]:
        violations: list[str] = []
        anchor_blob = " ".join((proposal.claim, proposal.required_anchor_text, " ".join(proposal.evidence)))
        for anchor in task.required_anchors:
            if anchor and anchor not in anchor_blob:
                violations.append(f"anchor_missing:{anchor}")
        return violations


class ConfidenceConstraint(Constraint):
    """Verifies that the child confidence rating is within the valid [0.0, 1.0] float range."""
    constraint_id: str = "confidence"

    def check(self, task: TaskSpec, proposal: AgentProposal) -> list[str]:
        if not (0.0 <= proposal.confidence <= 1.0):
            return ["confidence_out_of_range"]
        return []


class ConstraintChecker:
    """Rejects semantic pollution before a proposal can become accepted state.

    Allows loading custom constraints for extensible policy checks.
    """

    def __init__(self, constraints: list[Constraint] | None = None) -> None:
        from .config import load_config
        disabled: list[str] = []
        try:
            disabled = load_config().get("disabled_constraints") or []
        except Exception:
            pass

        all_constraints = [
            EnvelopeConstraint(),
            TaskMismatchConstraint(),
            SanitizedTaskConstraint(),
            AuthorityConstraint(),
            MetadataLeakConstraint(),
            ClaimConstraint(),
            EvidenceConstraint(),
            TestConstraint(),
            ScopeConstraint(),
            ForbiddenOutputConstraint(),
            AnchorConstraint(),
            ConfidenceConstraint(),
        ]

        if constraints is None:
            self.constraints = [
                c for c in all_constraints if c.constraint_id not in disabled
            ]
        else:
            self.constraints = [
                c for c in constraints if c.constraint_id not in disabled
            ]

    def check(self, task: TaskSpec, proposal: AgentProposal) -> CheckedRecord:
        violations: list[str] = []
        for constraint in self.constraints:
            violations.extend(constraint.check(task, proposal))

        return CheckedRecord(
            proposal=proposal,
            accepted=not violations,
            violations=tuple(violations),
        )
