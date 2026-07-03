"""Deterministic sample pipeline for Text Graphics Agent."""

from __future__ import annotations

import json

from .orchestrator import MotherAgent
from .intent import IntentDecomposer
from .records import AgentProposal, RecordEnvelope, TaskSpec


def ui_specialist(task: TaskSpec) -> list[AgentProposal]:
    return [
        AgentProposal(
            envelope=RecordEnvelope.for_task(
                actor="child:ui-adversary",
                target=task.task_id,
                cause="adversarial-ui-review",
                scope_id="play-ui",
            ),
            task_id=task.task_id,
            child_agent_id="ui-001",
            child_role="ui_adversary",
            proposal_kind="patch_plan",
            claim="NPC dialogue choice rail stacks vertically; make it a horizontal rail and lock busy-state controls.",
            evidence=("behavior-card-mvp/tests/play_interaction_lock_test.py", "behavior-card-mvp/app/static/play.html"),
            proposed_scopes=("behavior-card-mvp/app/static/play.html", "behavior-card-mvp/tests/*"),
            proposed_outputs=("patch_plan",),
            required_anchor_text="NPC dialogue",
            test_commands=(
                r".\behavior-card-mvp\.venv\Scripts\python.exe behavior-card-mvp\tests\play_interaction_lock_test.py",
            ),
            confidence=0.91,
        )
    ]


def polluted_specialist(task: TaskSpec) -> list[AgentProposal]:
    return [
        AgentProposal(
            envelope=RecordEnvelope.for_task(
                actor="child:semantic-drifter",
                target=task.task_id,
                cause="multimodal-free-association",
                scope_id="world-ledger",
            ),
            task_id=task.task_id,
            child_agent_id="mm-002",
            child_role="visual_storyteller",
            proposal_kind="expression",
            claim="The screenshot implies the elder secretly joined a hidden faction.",
            evidence=(),
            proposed_scopes=("behavior-card-mvp/data/world_modules/adventure/text_exploration_scenes.json",),
            proposed_outputs=("committed_fact", "new_action_type"),
            required_anchor_text="",
            test_commands=(),
            confidence=0.77,
        )
    ]


def build_sample_task() -> TaskSpec:
    intent = IntentDecomposer().decompose(
        "用户想修 /play NPC dialogue，但这只是需求入口，不能把用户语义当事实。"
    )
    return MotherAgent().make_clean_task(
        intent,
        task_id="tga-play-ui-001",
        allowed_scopes=(
            "behavior-card-mvp/app/static/play.html",
            "behavior-card-mvp/tests/*",
        ),
        required_anchors=("NPC dialogue",),
    )


def main() -> None:
    mother = MotherAgent()
    checked, score = mother.dispatch(build_sample_task(), [ui_specialist, polluted_specialist])
    payload = {
        "records": [
            {
                "child": row.proposal.child_agent_id,
                "status": row.status,
                "violations": list(row.violations),
            }
            for row in checked
        ],
        "score": {
            "total": score.total,
            "accepted": score.accepted,
            "rejected": score.rejected,
            "acceptance_rate": score.acceptance_rate,
            "violation_counts": score.violation_counts,
            "destroyed_child_ids": list(score.destroyed_child_ids),
            "child_sessions": [
                {
                    "child_agent_id": session.child_agent_id,
                    "status": session.status,
                    "proposal_count": session.proposal_count,
                }
                for session in score.child_sessions
            ],
        },
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
