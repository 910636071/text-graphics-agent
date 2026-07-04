"""Human approval checkpoint rules for risky dashboard actions."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class ApprovalReason:
    reason_id: str
    label: str
    detail: str
    severity: str = "review"


@dataclass(frozen=True)
class ApprovalDecision:
    required: bool
    action_id: str
    title: str
    summary: str
    reasons: tuple[ApprovalReason, ...] = ()


APPROVAL_POLICY: dict[str, Any] = {
    "approval_required_for": [
        "state_write",
        "external_publish",
        "credential_change",
        "constraint_disable",
        "scope_boundary_change",
        "live_model_call",
    ],
    "decision_authority": "human_checkpoint",
    "auto_apply_allowed": False,
}


def _as_list(value: Any) -> list[str]:
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, tuple):
        return [str(item).strip() for item in value if str(item).strip()]
    return []


def normalize_config_for_review(config: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(config)
    normalized["allowed_scopes"] = _as_list(normalized.get("allowed_scopes"))
    normalized["required_anchors"] = _as_list(normalized.get("required_anchors"))
    normalized["disabled_constraints"] = _as_list(normalized.get("disabled_constraints"))
    return normalized


def no_approval(action_id: str = "none") -> ApprovalDecision:
    return ApprovalDecision(
        required=False,
        action_id=action_id,
        title="No approval required",
        summary="This action stays inside the safe automatic boundary.",
    )


def approval_payload(decision: ApprovalDecision) -> dict[str, Any]:
    return {
        **asdict(decision),
        "policy": APPROVAL_POLICY,
    }


def evaluate_config_change(current: dict[str, Any], proposed: dict[str, Any]) -> ApprovalDecision:
    current_norm = normalize_config_for_review(current)
    proposed_norm = normalize_config_for_review(proposed)
    reasons: list[ApprovalReason] = []

    if (current_norm.get("api_key") or "") != (proposed_norm.get("api_key") or ""):
        reasons.append(
            ApprovalReason(
                reason_id="credential_change",
                label="Credential change",
                detail="API key changes can enable live provider calls and must be approved by a human.",
                severity="critical",
            )
        )

    if current_norm.get("api_provider") != proposed_norm.get("api_provider"):
        reasons.append(
            ApprovalReason(
                reason_id="provider_route_change",
                label="Provider route change",
                detail="Changing the model provider can route prompts to a different external service.",
            )
        )

    if current_norm.get("model_name") != proposed_norm.get("model_name"):
        reasons.append(
            ApprovalReason(
                reason_id="model_route_change",
                label="Model route change",
                detail="Changing the model name affects live LLM behavior and review reproducibility.",
            )
        )

    if set(current_norm.get("allowed_scopes", [])) != set(proposed_norm.get("allowed_scopes", [])):
        reasons.append(
            ApprovalReason(
                reason_id="scope_boundary_change",
                label="Scope boundary change",
                detail="Allowed scope edits change which files a child proposal may touch.",
                severity="critical",
            )
        )

    if set(current_norm.get("required_anchors", [])) != set(proposed_norm.get("required_anchors", [])):
        reasons.append(
            ApprovalReason(
                reason_id="verification_contract_change",
                label="Verification contract change",
                detail="Required anchors are the evidence contract for accepting child proposals.",
            )
        )

    current_disabled = set(current_norm.get("disabled_constraints", []))
    proposed_disabled = set(proposed_norm.get("disabled_constraints", []))
    newly_disabled = sorted(proposed_disabled - current_disabled)
    if newly_disabled:
        reasons.append(
            ApprovalReason(
                reason_id="constraint_disable",
                label="Constraint disable",
                detail="Disabling constraints weakens the semantic firewall: " + ", ".join(newly_disabled),
                severity="critical",
            )
        )

    if not reasons:
        return no_approval("config_update")

    return ApprovalDecision(
        required=True,
        action_id="config_update",
        title="Human approval required",
        summary="This settings change crosses a safety boundary and will not be applied automatically.",
        reasons=tuple(reasons),
    )


def evaluate_live_model_call(provider: str, model_name: str) -> ApprovalDecision:
    return ApprovalDecision(
        required=True,
        action_id="live_model_call",
        title="Human approval required",
        summary="Live LLM execution sends the sanitized TaskSpec to an external model provider.",
        reasons=(
            ApprovalReason(
                reason_id="live_model_call",
                label="Live model call",
                detail=f"Provider={provider or 'unknown'}, model={model_name or 'default'}; approve before leaving local deterministic mode.",
                severity="critical",
            ),
        ),
    )
