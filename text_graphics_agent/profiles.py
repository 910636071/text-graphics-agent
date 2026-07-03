"""Explicit specialist profiles for disposable child agents."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable

from .records import AgentProposal, TaskSpec


SpecialistCallable = Callable[[TaskSpec], Iterable[AgentProposal]]


@dataclass(frozen=True)
class SpecialistProfile:
    """Mother-side contract for one child-agent type.

    Profiles make role, scope, and memory boundaries inspectable before a child
    agent is spawned. A profile is not a prompt; it is a dispatch constraint.
    """

    specialist_id: str
    role: str
    allowed_scopes: tuple[str, ...]
    tools: tuple[str, ...] = ()
    receives_raw_user_text: bool = False
    persistent_memory: bool = False

    def validate_for_task(self, task: TaskSpec) -> tuple[str, ...]:
        violations: list[str] = []
        if not self.specialist_id.strip():
            violations.append("profile_missing_specialist_id")
        if not self.role.strip():
            violations.append("profile_missing_role")
        if self.receives_raw_user_text:
            violations.append("profile_allows_raw_user_text")
        if self.persistent_memory:
            violations.append("profile_allows_persistent_memory")
        for scope in self.allowed_scopes:
            if not _scope_allowed(scope, task.allowed_scopes):
                violations.append(f"profile_scope_escape:{scope}")
        return tuple(violations)


@dataclass(frozen=True)
class RegisteredSpecialist:
    profile: SpecialistProfile
    run: SpecialistCallable


def _scope_allowed(scope: str, allowed_scopes: tuple[str, ...]) -> bool:
    if scope in allowed_scopes:
        return True
    return any(scope.startswith(prefix.rstrip("*")) for prefix in allowed_scopes if prefix.endswith("*"))
