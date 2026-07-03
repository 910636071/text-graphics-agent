"""User-intent firewall.

Raw user text is useful but untrusted. This module turns it into a bounded
IntentFrame before it can become a TaskSpec.
"""

from __future__ import annotations

from dataclasses import dataclass


_BYPASS_MARKERS = (
    "不用验证",
    "不要测试",
    "直接入库",
    "直接写事实",
    "别审",
    "skip tests",
    "no review",
    "write facts",
)

_SCOPE_MARKERS = (
    "顺便",
    "全部",
    "所有",
    "整个",
    "whatever",
    "anything",
)


@dataclass(frozen=True)
class IntentFrame:
    raw_text: str
    stable_goal: str
    intent_codes: tuple[str, ...]
    atomic_intents: tuple[str, ...]
    user_supplied_claims: tuple[str, ...]
    assumptions: tuple[str, ...]
    contamination_markers: tuple[str, ...]

    @property
    def contaminated(self) -> bool:
        return bool(self.contamination_markers)


class IntentDecomposer:
    """A small deterministic first pass, not an LLM judge."""

    def decompose(self, raw_text: str) -> IntentFrame:
        text = " ".join(str(raw_text or "").split())
        contamination: list[str] = []
        lowered = text.lower()

        for marker in _BYPASS_MARKERS:
            if marker.lower() in lowered:
                if "bypass_pressure" not in contamination:
                    contamination.append("bypass_pressure")
        for marker in _SCOPE_MARKERS:
            if marker.lower() in lowered:
                if "scope_pressure" not in contamination:
                    contamination.append("scope_pressure")

        atomic = tuple(part.strip(" ，。；;") for part in text.replace("，", ";").replace("。", ";").split(";") if part.strip())
        claims = tuple(part for part in atomic if any(token in part for token in ("我发现", "确定", "肯定", "事实", "bug")))
        codes = self._intent_codes(lowered)
        goal = self._stable_goal(codes)
        assumptions = ("user request is motivation, not evidence",)

        return IntentFrame(
            raw_text=text,
            stable_goal=goal,
            intent_codes=codes,
            atomic_intents=atomic,
            user_supplied_claims=claims,
            assumptions=assumptions,
            contamination_markers=tuple(contamination),
        )

    def _intent_codes(self, lowered: str) -> tuple[str, ...]:
        codes: list[str] = []
        rules = (
            ("bug_review", ("bug", "问题", "坏了", "抖动", "冲突")),
            ("ui_review", ("ui", "界面", "布局", "对话", "npc", "play")),
            ("architecture_review", ("架构", "agent", "母", "子", "语义污染")),
            ("implementation", ("做", "实现", "修", "优化", "构建")),
            ("verification", ("测试", "验证", "评测", "审查")),
        )
        for code, needles in rules:
            if any(needle in lowered for needle in needles):
                codes.append(code)
        return tuple(codes or ("general_request",))

    def _stable_goal(self, codes: tuple[str, ...]) -> str:
        return "execute sanitized intent codes: " + ",".join(codes)
