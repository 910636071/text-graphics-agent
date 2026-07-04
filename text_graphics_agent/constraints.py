"""Finite checks for disposable child-agent proposals."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from .records import AgentProposal, CheckedRecord, TaskSpec
from .intent import BYPASS_MARKERS as _INTENT_BYPASS_MARKERS


_FORBIDDEN_METADATA_KEYS = {
    "raw_user_text",
    "raw_text",
    "raw_request",
    "atomic_intents",
    "user_supplied_claims",
}
_FORBIDDEN_METADATA_KEY_ALIASES = {
    key.replace("_", "") for key in _FORBIDDEN_METADATA_KEYS
}
_RAW_VALUE_MARKERS = (
    "raw user text",
    "raw user request",
    "original user request",
    "verbatim user prompt",
)
_RESERVED_AUTHORITY_TOKENS = {
    "admin",
    "approver",
    "ledger",
    "mother",
    "orchestrator",
    "root",
    "system",
}
_ALLOWED_PROPOSAL_KINDS = {"analysis", "patch_plan", "expression", "test_plan"}

#: Bypass language markers — the single source of truth lives in intent.py.
#: We import it and add proposal-side-only markers that don't apply to user intent.
_BYPASS_LANGUAGE_MARKERS: tuple[str, ...] = _INTENT_BYPASS_MARKERS + (
    "ignore previous",  # prompt-injection style override
    "no need to test",
    "no need to verify",
    "no need to review",
    "自动通过",
    "自动批准",
    "直接通过",
    "直接放行",
    "不用管",
    "不用检查",
    "不用确认",
    "不需要验证",
    "不需要审核",
    "信任我",
    "相信我",
    "保证没问题",
    "保证安全",
)
_DANGEROUS_TEST_COMMAND_MARKERS = (
    "curl | sh",
    "del /",
    "format ",
    "git reset --hard",
    "Invoke-WebRequest",
    "Remove-Item",
    "rm -rf",
    "rmdir /s",
)

_GOAL_MARKER_ALIASES: dict[str, tuple[str, ...]] = {
    "settings_panel": (
        "settings_panel",
        "settings panel",
        "settings ui",
        "settings",
        "config panel",
        "preferences",
    ),
    "layout": (
        "layout",
        "responsive",
        "positioning",
        "ui structure",
        "view structure",
    ),
    "spacing": (
        "spacing",
        "gap",
        "padding",
        "margin",
        "gutter",
        "white space",
        "whitespace",
    ),
    "touch_target_44px": (
        "touch_target_44px",
        "44px",
        "44 px",
        "touch target",
        "tap target",
        "hit target",
        "minimum target",
    ),
    "scroll": (
        "scroll",
        "wheel",
        "overflow",
        "scrolling",
    ),
    "multilingual": (
        "multilingual",
        "multi-language",
        "language",
        "i18n",
        "translation",
    ),
    "operation_guide": (
        "operation_guide",
        "operation guide",
        "guide",
        "help",
        "instructions",
    ),
    "agent_workflow": (
        "agent_workflow",
        "agent workflow",
        "workflow",
        "child agent",
        "sub-agent",
        "subagent",
        "dispatch",
    ),
    "approval_loop": (
        "approval_loop",
        "approval",
        "approve",
        "human approval",
        "checkpoint",
    ),
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


class ProposalKindConstraint(Constraint):
    """Rejects runtime proposal-kind expansion beyond the finite action set."""
    constraint_id: str = "proposal_kind"

    def check(self, task: TaskSpec, proposal: AgentProposal) -> list[str]:
        kind = str(proposal.proposal_kind)
        if kind not in _ALLOWED_PROPOSAL_KINDS:
            return [f"proposal_kind_expansion:{kind}"]
        return []


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
        violations: list[str] = []
        role_tokens = _split_authority_tokens(proposal.child_role)
        if role_tokens & _RESERVED_AUTHORITY_TOKENS:
            violations.append("mother_may_not_author")

        actor = proposal.envelope.actor.strip().lower()
        if not actor.startswith("child:"):
            violations.append("non_child_actor")
        else:
            actor_suffix = actor.split(":", 1)[1]
            if _split_authority_tokens(actor_suffix) & _RESERVED_AUTHORITY_TOKENS:
                violations.append("privileged_actor_impersonation")
        return violations


class MetadataLeakConstraint(Constraint):
    """Recursively checks metadata structure to ensure raw user texts do not leak to the child."""
    constraint_id: str = "metadata_leak"

    def check(self, task: TaskSpec, proposal: AgentProposal) -> list[str]:
        if self._metadata_has_forbidden_leak(proposal.metadata):
            return ["raw_user_text_leaked_to_child"]
        return []

    def _metadata_has_forbidden_leak(self, value: Any) -> bool:
        if isinstance(value, dict):
            for key, child in value.items():
                normalized_key = _normalize_metadata_key(key)
                if (
                    normalized_key in _FORBIDDEN_METADATA_KEYS
                    or normalized_key.replace("_", "") in _FORBIDDEN_METADATA_KEY_ALIASES
                ):
                    return True
                if self._metadata_has_forbidden_leak(child):
                    return True
        elif isinstance(value, (list, tuple)):
            return any(self._metadata_has_forbidden_leak(child) for child in value)
        elif isinstance(value, str):
            lowered = value.lower()
            return any(marker in lowered for marker in _RAW_VALUE_MARKERS)
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


class EvidenceScopeConstraint(Constraint):
    """Rejects path-like evidence outside the task's allowed scope boundary."""
    constraint_id: str = "evidence_scope"

    def check(self, task: TaskSpec, proposal: AgentProposal) -> list[str]:
        violations: list[str] = []
        for item in proposal.evidence:
            if not _looks_like_scope_path(item):
                continue
            if _scope_has_traversal(item):
                violations.append(f"evidence_path_traversal:{item}")
            elif not _scope_allowed(item, task.allowed_scopes):
                violations.append(f"evidence_scope_escape:{item}")
        return violations


class TestConstraint(Constraint):
    """Ensures the child supplies verification/test commands if the task requires tests."""
    constraint_id: str = "test"

    def check(self, task: TaskSpec, proposal: AgentProposal) -> list[str]:
        if task.requires_tests and not proposal.test_commands:
            return ["missing_test_commands"]
        return []


class TestCommandSafetyConstraint(Constraint):
    """Blocks test commands that look like destructive shell operations."""
    constraint_id: str = "test_command_safety"

    def check(self, task: TaskSpec, proposal: AgentProposal) -> list[str]:
        violations: list[str] = []
        for command in proposal.test_commands:
            lowered = command.lower()
            for marker in _DANGEROUS_TEST_COMMAND_MARKERS:
                if marker.lower() in lowered:
                    violations.append(f"dangerous_test_command:{marker}")
        return violations


class BypassLanguageConstraint(Constraint):
    """Blocks proposal text that tries to waive review, testing, or constraints."""
    constraint_id: str = "bypass_language"

    def check(self, task: TaskSpec, proposal: AgentProposal) -> list[str]:
        haystack = "\n".join((
            proposal.claim,
            proposal.required_anchor_text,
            " ".join(proposal.evidence),
            " ".join(proposal.proposed_outputs),
            " ".join(proposal.test_commands),
        )).lower()
        for marker in _BYPASS_LANGUAGE_MARKERS:
            if marker.lower() in haystack:
                return [f"bypass_language:{marker}"]
        return []


class ScopeConstraint(Constraint):
    """Enforces boundaries. The proposal must not touch scopes outside the TaskSpec's whitelist."""
    constraint_id: str = "scope"

    def check(self, task: TaskSpec, proposal: AgentProposal) -> list[str]:
        violations: list[str] = []
        for scope in proposal.proposed_scopes:
            if _scope_has_traversal(scope):
                violations.append(f"scope_path_traversal:{scope}")
            if not _scope_allowed(scope, task.allowed_scopes):
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
        evidence_blob = " ".join((proposal.claim, " ".join(proposal.evidence)))
        for anchor in task.required_anchors:
            if not anchor:
                continue
            if anchor in evidence_blob:
                continue
            if anchor in proposal.required_anchor_text:
                violations.append(f"anchor_declared_without_evidence:{anchor}")
            else:
                violations.append(f"anchor_missing:{anchor}")
        return violations


class GoalAlignmentConstraint(Constraint):
    """Rejects proposals that drift away from sanitized objective markers."""
    constraint_id: str = "goal_alignment"

    def check(self, task: TaskSpec, proposal: AgentProposal) -> list[str]:
        markers = _task_goal_markers(task)
        if len(markers) < 2:
            return []

        proposal_blob = _proposal_goal_blob(proposal)
        matched = [
            marker
            for marker in markers
            if _goal_marker_present(marker, proposal_blob)
        ]
        minimum_matches = max(1, (len(markers) + 1) // 2)
        if len(matched) >= minimum_matches:
            return []

        missing = [marker for marker in markers if marker not in matched]
        return ["goal_drift:missing:" + ",".join(missing)]


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
            ProposalKindConstraint(),
            TaskMismatchConstraint(),
            SanitizedTaskConstraint(),
            AuthorityConstraint(),
            MetadataLeakConstraint(),
            ClaimConstraint(),
            EvidenceConstraint(),
            EvidenceScopeConstraint(),
            TestConstraint(),
            TestCommandSafetyConstraint(),
            BypassLanguageConstraint(),
            ScopeConstraint(),
            ForbiddenOutputConstraint(),
            AnchorConstraint(),
            GoalAlignmentConstraint(),
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


def _normalize_metadata_key(key: Any) -> str:
    return str(key).strip().replace("-", "_").lower()


def _split_authority_tokens(value: str) -> set[str]:
    normalized = "".join(char if char.isalnum() else " " for char in value.lower())
    return {token for token in normalized.split() if token}


def _scope_has_traversal(scope: str) -> bool:
    normalized = scope.replace("\\", "/").strip()
    first_segment = normalized.split("/", 1)[0]
    return (
        normalized.startswith(("/", "~"))
        or ":" in first_segment
        or any(part == ".." for part in normalized.split("/"))
    )


def _scope_allowed(scope: str, allowed_scopes: tuple[str, ...]) -> bool:
    allowed = set(allowed_scopes)
    if scope in allowed:
        return True
    return any(
        scope.startswith(prefix.rstrip("*"))
        for prefix in allowed_scopes
        if prefix.endswith("*")
    )


def _looks_like_scope_path(value: str) -> bool:
    if value.startswith(("user:", "note:", "manual:", "http://", "https://")):
        return False
    # Must contain a path separator to be considered a path.
    # A lone dot (like "file.") is not enough — natural language sentences
    # contain periods and would cause false positives.
    if "/" not in value and "\\" not in value:
        return False
    # Check for file extension pattern (e.g. "play.html", "config.json")
    last_segment = value.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
    return "." in last_segment


def _task_goal_markers(task: TaskSpec) -> tuple[str, ...]:
    haystack = "\n".join((task.objective, " ".join(task.mother_notes))).lower()
    markers: list[str] = []
    marker_prefix = "goal markers:"
    if marker_prefix in haystack:
        marker_text = haystack.split(marker_prefix, 1)[1].split(";", 1)[0]
        for raw_marker in marker_text.replace(",", " ").split():
            marker = raw_marker.strip()
            if marker in _GOAL_MARKER_ALIASES and marker not in markers:
                markers.append(marker)

    for marker, aliases in _GOAL_MARKER_ALIASES.items():
        if marker in markers:
            continue
        if any(alias.lower() in haystack for alias in aliases):
            markers.append(marker)
    return tuple(markers)


def _proposal_goal_blob(proposal: AgentProposal) -> str:
    return "\n".join((
        proposal.claim,
        " ".join(proposal.evidence),
        " ".join(proposal.proposed_scopes),
        " ".join(proposal.proposed_outputs),
        proposal.required_anchor_text,
        " ".join(proposal.test_commands),
    )).lower()


def _goal_marker_present(marker: str, proposal_blob: str) -> bool:
    return any(alias.lower() in proposal_blob for alias in _GOAL_MARKER_ALIASES[marker])
