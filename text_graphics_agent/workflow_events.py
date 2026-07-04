"""Small workflow event helpers for operator-visible agent traces."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class WorkflowArtifact:
    artifact_id: str
    kind: str
    title: str
    payload: dict[str, Any]
    append: bool = False
    last_chunk: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def workflow_artifact(
    artifact_id: str,
    *,
    kind: str,
    title: str,
    payload: dict[str, Any],
    append: bool = False,
    last_chunk: bool = True,
) -> dict[str, Any]:
    return WorkflowArtifact(
        artifact_id=artifact_id,
        kind=kind,
        title=title,
        payload=payload,
        append=append,
        last_chunk=last_chunk,
    ).to_dict()


def workflow_event(
    step: str,
    title: str,
    detail: str,
    status: str = "done",
    *,
    title_en: str = "",
    detail_en: str = "",
    child_agent: str | None = None,
    tool: str | None = None,
    details: dict[str, Any] | None = None,
    artifacts: tuple[dict[str, Any], ...] = (),
    **extra: Any,
) -> dict[str, Any]:
    event: dict[str, Any] = {
        "step": step,
        "title": title,
        "detail": detail,
        "status": status,
    }
    if title_en:
        event["title_en"] = title_en
    if detail_en:
        event["detail_en"] = detail_en
    if child_agent:
        event["child_agent"] = child_agent
    if tool:
        event["tool"] = tool
    if details:
        event["details"] = details
    if artifacts:
        event["artifacts"] = list(artifacts)
    event.update(extra)
    return event
