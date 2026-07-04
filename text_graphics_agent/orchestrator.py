"""Mother-agent orchestration without authority leakage."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable

from .constraints import ConstraintChecker
from .intent import IntentFrame
from .profiles import RegisteredSpecialist
from .records import AgentProposal, CheckedRecord, ChildSessionRecord, TaskSpec


Specialist = Callable[[TaskSpec], Iterable[AgentProposal]]


@dataclass(frozen=True)
class ScoreCard:
    total: int
    accepted: int
    rejected: int
    violation_counts: dict[str, int]
    destroyed_child_ids: tuple[str, ...] = ()
    child_sessions: tuple[ChildSessionRecord, ...] = ()

    @property
    def acceptance_rate(self) -> float:
        if self.total == 0:
            return 0.0
        return round(self.accepted / self.total, 4)


class MotherAgent:
    """Scheduler and auditor.

    The mother agent dispatches specialists and checks proposals. It does not
    write final artifacts or committed facts.
    """

    def __init__(self, checker: ConstraintChecker | None = None) -> None:
        self.checker = checker or ConstraintChecker()

    def make_clean_task(
        self,
        intent: IntentFrame,
        *,
        task_id: str,
        allowed_scopes: tuple[str, ...],
        required_anchors: tuple[str, ...] = (),
        requires_tests: bool = True,
        requires_evidence_provenance: bool = False,
        memory_hints: tuple[str, ...] = (),
    ) -> TaskSpec:
        """Convert polluted user semantics into a child-safe task.

        The raw user text is intentionally not copied into TaskSpec.

        Memory hints are untrusted context from the mother agent's curated
        memory.  They enter ``mother_notes`` as ``memory_hint`` entries to
        help the mother agent reason, but they NEVER enter ``objective``
        (the child agent's instruction) and they NEVER affect constraint
        decisions.
        """
        notes = [
            "TaskSpec is sanitized; child agents must not receive raw user text.",
            *intent.assumptions,
        ]
        if intent.contamination_markers:
            notes.append("Mother detected user semantic pressure codes: " + ", ".join(intent.contamination_markers))
        # Memory hints are explicitly marked as untrusted context.
        # They appear in mother_notes for auditability but cannot influence
        # the child agent's objective or the constraint layer's decisions.
        for hint in memory_hints:
            notes.append(f"memory_hint (untrusted): {hint}")
        return TaskSpec(
            task_id=task_id,
            objective=intent.stable_goal,
            allowed_scopes=allowed_scopes,
            required_anchors=required_anchors,
            requires_tests=requires_tests,
            requires_evidence_provenance=requires_evidence_provenance,
            sanitized=True,
            sanitized_provenance="mother_clean_v1",
            mother_notes=tuple(notes),
        )

    def review(self, task: TaskSpec, proposals: Iterable[AgentProposal]) -> list[CheckedRecord]:
        return [self.checker.check(task, proposal) for proposal in proposals]

    def dispatch(self, task: TaskSpec, specialists: Iterable[Specialist]) -> tuple[list[CheckedRecord], ScoreCard]:
        self._assert_dispatchable_task(task)
        proposals: list[AgentProposal] = []
        sessions: list[ChildSessionRecord] = []
        for specialist in specialists:
            opened = ChildSessionRecord.open(
                child_agent_id=getattr(specialist, "__name__", "anonymous_child"),
                task_id=task.task_id,
                role="specialist",
            )
            try:
                produced = list(specialist(task))
            except Exception:
                sessions.append(opened.close(proposal_count=0, failed=True))
                raise
            proposals.extend(produced)
            child_counts: dict[str, int] = {}
            for proposal in produced:
                child_counts[proposal.child_agent_id] = child_counts.get(proposal.child_agent_id, 0) + 1
            if not child_counts:
                sessions.append(opened.close(proposal_count=0))
            else:
                for child_id, count in sorted(child_counts.items()):
                    sessions.append(
                        ChildSessionRecord(
                            child_agent_id=child_id,
                            task_id=opened.task_id,
                            role=opened.role,
                            opened_at=opened.opened_at,
                        ).close(proposal_count=count)
                    )
        checked = self.review(task, proposals)
        destroyed = tuple(sorted(
            session.child_agent_id
            for session in sessions
            if session.status == "destroyed"
        ))
        return checked, self.score(
            checked,
            destroyed_child_ids=destroyed,
            child_sessions=tuple(sessions),
        )

    def _assert_dispatchable_task(self, task: TaskSpec) -> None:
        if not task.sanitized or task.sanitized_provenance != "mother_clean_v1":
            raise ValueError("dispatch requires a MotherAgent.make_clean_task TaskSpec")

    def dispatch_registered(
        self,
        task: TaskSpec,
        specialists: Iterable[RegisteredSpecialist],
    ) -> tuple[list[CheckedRecord], ScoreCard]:
        """Dispatch only specialists whose profiles satisfy the clean task."""
        self._assert_dispatchable_task(task)
        runnable: list[Specialist] = []
        profile_violations: dict[str, tuple[str, ...]] = {}

        for specialist in specialists:
            violations = specialist.profile.validate_for_task(task)
            if violations:
                profile_violations[specialist.profile.specialist_id] = violations
                continue
            runnable.append(_named_specialist(specialist.profile.specialist_id, specialist.run))

        if runnable:
            checked, score = self.dispatch(task, runnable)
        else:
            checked = []
            score = self.score([])

        if not profile_violations:
            return checked, score

        violation_counts = dict(score.violation_counts)
        for specialist_id, violations in profile_violations.items():
            for violation in violations:
                key = f"{specialist_id}:{violation}"
                violation_counts[key] = violation_counts.get(key, 0) + 1
        return checked, ScoreCard(
            total=score.total,
            accepted=score.accepted,
            rejected=score.rejected,
            violation_counts=violation_counts,
            destroyed_child_ids=score.destroyed_child_ids,
            child_sessions=score.child_sessions,
        )

    def score(
        self,
        records: Iterable[CheckedRecord],
        *,
        destroyed_child_ids: tuple[str, ...] = (),
        child_sessions: tuple[ChildSessionRecord, ...] = (),
    ) -> ScoreCard:
        rows = list(records)
        violation_counts: dict[str, int] = {}
        for record in rows:
            for violation in record.violations:
                violation_counts[violation] = violation_counts.get(violation, 0) + 1
        accepted = sum(1 for record in rows if record.accepted)
        return ScoreCard(
            total=len(rows),
            accepted=accepted,
            rejected=len(rows) - accepted,
            violation_counts=violation_counts,
            destroyed_child_ids=destroyed_child_ids,
            child_sessions=child_sessions,
        )


def _named_specialist(name: str, run: Specialist) -> Specialist:
    def wrapper(task: TaskSpec) -> Iterable[AgentProposal]:
        return run(task)

    wrapper.__name__ = name
    return wrapper
