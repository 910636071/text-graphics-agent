"""Inspectable child-agent cards inspired by A2A AgentCard structure.

These records describe what a disposable child agent may do. They are not
prompts and do not grant authority by themselves.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class AgentSkill:
    skill_id: str
    name: str
    description: str
    tags: tuple[str, ...] = ()
    examples: tuple[str, ...] = ()
    input_modes: tuple[str, ...] = ("text", "task_spec")
    output_modes: tuple[str, ...] = ("agent_proposal",)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AgentCard:
    agent_id: str
    name: str
    description: str
    version: str
    default_input_modes: tuple[str, ...]
    default_output_modes: tuple[str, ...]
    capabilities: dict[str, Any] = field(default_factory=dict)
    skills: tuple[AgentSkill, ...] = ()
    safety_contract: tuple[str, ...] = ()
    approval_required_for: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["skills"] = [skill.to_dict() for skill in self.skills]
        return data


def web_specialist_card(*, child_agent_id: str = "web-child-009", live: bool = False) -> AgentCard:
    """Return the workbench child-agent card shown to operators."""
    return AgentCard(
        agent_id=child_agent_id,
        name="Web Dashboard Specialist" if not live else "Live Web Dashboard Specialist",
        description=(
            "Disposable child agent for scoped web UI inspection, patch planning, "
            "and verification proposals."
        ),
        version="1.0.0",
        default_input_modes=("task_spec",),
        default_output_modes=("agent_proposal", "artifact_update", "status_update"),
        capabilities={
            "streaming": True,
            "disposable": True,
            "proposal_only": True,
            "receives_raw_user_text": False,
            "persistent_memory": False,
        },
        skills=(
            AgentSkill(
                skill_id="inspect_web_dashboard",
                name="Inspect web dashboard",
                description="Read scoped UI or configuration evidence and report observed issues.",
                tags=("ui", "inspection", "evidence"),
                examples=("Check app/static/play.html layout and run tests.",),
            ),
            AgentSkill(
                skill_id="propose_patch_plan",
                name="Propose patch plan",
                description="Return a bounded AgentProposal with evidence, scopes, outputs, and tests.",
                tags=("proposal", "patch_plan", "verification"),
                examples=("Propose a scoped fix for the settings page.",),
            ),
        ),
        safety_contract=(
            "Receives sanitized TaskSpec only.",
            "May propose records but may not approve or commit facts.",
            "Must cite evidence inside allowed scopes.",
            "Must provide verification commands when tests are required.",
        ),
        approval_required_for=("live_model_call", "credential_change", "constraint_disable"),
    )


def default_agent_cards() -> tuple[AgentCard, ...]:
    return (web_specialist_card(), web_specialist_card(child_agent_id="web-child-live", live=True))
