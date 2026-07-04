"""Agent registry and capability-based routing.

The :class:`AgentRegistry` lets specialists declare which intent codes and
goal markers they can handle.  The pipeline queries the registry to pick
the best specialist for a given task instead of hard-coding a single one.

Usage::

    registry = AgentRegistry()

    registry.register(
        specialist_id="code-reviewer",
        factory=lambda scopes, anchors: CodeReviewSpecialist(scopes, anchors),
        handles_intent=("bug_review", "verification"),
        handles_markers=("settings_panel", "layout"),
        card=code_reviewer_card,
    )

    # Pipeline calls:
    entry = registry.select(intent_codes=("bug_review",), goal_markers=("settings_panel",))
    specialist = entry.factory(allowed_scopes, required_anchors)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Protocol

from .specialists import BaseSpecialist


class SpecialistFactory(Protocol):
    """Callable that produces a fresh specialist instance per task."""

    def __call__(self, allowed_scopes: tuple[str, ...] = (), required_anchors: tuple[str, ...] = ()) -> BaseSpecialist:
        ...


@dataclass(frozen=True)
class RegistryEntry:
    """A registered specialist declaration."""

    specialist_id: str
    factory: SpecialistFactory
    handles_intent: tuple[str, ...] = ()
    handles_markers: tuple[str, ...] = ()
    card: dict[str, Any] = field(default_factory=dict)
    priority: int = 0  # higher = preferred when multiple match


class AgentRegistry:
    """Capability-based specialist registry with scoring router.

    Specialists are registered with declarations of which intent codes and
    goal markers they handle.  :meth:`select` scores each candidate against
    the task's intent codes and goal markers, returning the best match.
    """

    def __init__(self) -> None:
        self._entries: list[RegistryEntry] = []

    # ── Registration ────────────────────────────────────────────────

    def register(
        self,
        specialist_id: str,
        factory: SpecialistFactory,
        handles_intent: tuple[str, ...] = (),
        handles_markers: tuple[str, ...] = (),
        card: dict[str, Any] | None = None,
        priority: int = 0,
    ) -> None:
        """Register a specialist with its capability declaration.

        Args:
            specialist_id: Unique identifier for this specialist type.
            factory: Callable that creates a fresh specialist per task.
            handles_intent: Intent codes this specialist can serve.
            handles_markers: Goal markers this specialist understands.
            card: Agent card dict for the frontend (optional).
            priority: Tie-breaker — higher wins when scores are equal.
        """
        # Remove existing entry with the same id (idempotent registration).
        self._entries = [e for e in self._entries if e.specialist_id != specialist_id]
        self._entries.append(
            RegistryEntry(
                specialist_id=specialist_id,
                factory=factory,
                handles_intent=handles_intent,
                handles_markers=handles_markers,
                card=card or {},
                priority=priority,
            )
        )

    def unregister(self, specialist_id: str) -> None:
        """Remove a specialist from the registry."""
        self._entries = [e for e in self._entries if e.specialist_id != specialist_id]

    # ── Query ───────────────────────────────────────────────────────

    def select(
        self,
        intent_codes: tuple[str, ...] = (),
        goal_markers: tuple[str, ...] = (),
    ) -> RegistryEntry | None:
        """Pick the best-matching specialist for the given task signals.

        Scoring:
        - +2 for each matching intent code
        - +1 for each matching goal marker
        - +priority as a tie-breaker

        Returns None if no specialist is registered.
        """
        if not self._entries:
            return None

        best: RegistryEntry | None = None
        best_score = -1

        for entry in self._entries:
            score = entry.priority
            for code in intent_codes:
                if code in entry.handles_intent:
                    score += 2
            for marker in goal_markers:
                if marker in entry.handles_markers:
                    score += 1
            if score > best_score:
                best_score = score
                best = entry

        return best

    def cards(self) -> list[dict[str, Any]]:
        """Return all registered agent cards for the frontend registry."""
        return [e.card for e in self._entries if e.card]

    @property
    def entries(self) -> tuple[RegistryEntry, ...]:
        return tuple(self._entries)


# ── Default registry ───────────────────────────────────────────────────


def _local_simulation_factory(
    allowed_scopes: tuple[str, ...] = (),
    required_anchors: tuple[str, ...] = (),
) -> BaseSpecialist:
    from .specialists import LocalSimulationSpecialist
    return LocalSimulationSpecialist(allowed_scopes=allowed_scopes, required_anchors=required_anchors)


def _live_specialist_factory(
    provider: str,
    api_key: str,
    model: str = "",
) -> SpecialistFactory:
    """Create a factory that produces LiveSpecialist instances.

    The provider/key/model are captured at registration time so the
    pipeline doesn't need to know about LLM configuration.
    """
    def factory(
        allowed_scopes: tuple[str, ...] = (),
        required_anchors: tuple[str, ...] = (),
    ) -> BaseSpecialist:
        from .specialists import LiveSpecialist
        return LiveSpecialist(
            provider=provider,
            api_key=api_key,
            model=model,
            allowed_scopes=allowed_scopes,
        )
    return factory


def default_registry(
    provider: str = "gemini",
    api_key: str = "",
    model: str = "",
    use_live: bool = False,
) -> AgentRegistry:
    """Build the default registry with built-in specialists.

    Args:
        provider: LLM provider for the live specialist.
        api_key: API key for the live specialist.
        model: Model name for the live specialist.
        use_live: If True, register the live specialist; otherwise only
            the local simulation specialist is registered.
    """
    from .agent_cards import web_specialist_card

    registry = AgentRegistry()

    # Local simulation specialist — handles everything, lowest priority.
    registry.register(
        specialist_id="web-child-009",
        factory=_local_simulation_factory,
        handles_intent=("bug_review", "ui_review", "architecture_review", "implementation", "verification", "general_request"),
        handles_markers=("settings_panel", "layout", "spacing", "touch_target_44px", "scroll", "multilingual", "operation_guide", "agent_workflow", "approval_loop"),
        card=web_specialist_card(child_agent_id="web-child-009", live=False).to_dict(),
        priority=0,
    )

    if use_live:
        registry.register(
            specialist_id="web-child-live",
            factory=_live_specialist_factory(provider, api_key, model),
            handles_intent=("bug_review", "ui_review", "architecture_review", "implementation", "verification", "general_request"),
            handles_markers=("settings_panel", "layout", "spacing", "touch_target_44px", "scroll", "multilingual", "operation_guide", "agent_workflow", "approval_loop"),
            card=web_specialist_card(child_agent_id="web-child-live", live=True).to_dict(),
            priority=10,  # prefer live when available
        )

    return registry
