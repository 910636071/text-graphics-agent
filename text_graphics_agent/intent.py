"""User-intent firewall.

Raw user text is useful but untrusted. This module turns it into a bounded
IntentFrame before it can become a TaskSpec.
"""

from __future__ import annotations

from dataclasses import dataclass


# ── Shared Chinese + English adversarial keyword banks ──────────────────
# These constants are the single source of truth. constraints.py, gui.py,
# and interactive_sandbox.py all import from here to stay in sync.

#: Bypass / waiver pressure — user tries to skip review, testing, or constraints.
#: Covers formal, colloquial, and mixed CN/EN adversarial phrasing.
BYPASS_MARKERS: tuple[str, ...] = (
    # ── 中文：直接绕审 ──
    "不用验证", "不要测试", "不用审查", "无需审核", "无需验证",
    "别审", "免审", "免验证", "跳过测试", "跳过验证", "跳过审核",
    "绕过审核", "绕过验证", "绕过审查", "绕过",
    "直接入库", "直接写事实", "直接批准", "直接执行", "直接上线", "直接写",
    "忽略拦截", "忽略其它拦截", "忽略其他拦截", "忽略检查",
    "信任我", "相信我", "保证没问题", "保证安全",
    # ── 中文：确定性施压 ──
    "不用管", "不用检查", "不用确认", "不需要验证", "不需要审核",
    "自动通过", "自动批准", "直接通过", "直接放行",
    # ── English ──
    "skip tests", "skip test", "skip verification", "skip review",
    "no review", "no verify", "no check",
    "bypass review", "bypass verification", "bypass constraints",
    "ignore constraints", "ignore previous", "ignore checks",
    "approve directly", "auto approve", "auto-approve",
    "trust me", "write facts", "just do it", "no need to test",
    "no need to verify", "no need to review",
)

#: Scope escape pressure — user tries to widen the blast radius beyond the task.
#: Short high-precision markers come first; broader ones need context (handled in code).
SCOPE_MARKERS: tuple[str, ...] = (
    # ── 中文：越权暗示 ──
    "顺便", "全都", "统统", "一切", "全局", "批量",
    "整个", "全部", "所有", "覆盖所有",
    # ── English ──
    "whatever", "anything", "everything", "entire", "whole",
    "all of them", "all files", "batch update",
)

#: Broad scope markers that need context to avoid false positives.
#: If these appear, we check whether a sensitive noun follows.
_SCOPE_CONTEXTUAL_MARKERS: tuple[str, ...] = (
    "全部", "所有", "整个",
)
_SCOPE_SENSITIVE_NOUNS: tuple[str, ...] = (
    "文件", "配置", "目录", "数据库", "账本", "ledger",
    "系统", "全局", "所有", "全部",
    "file", "config", "directory", "database", "system",
)

#: User self-assertion / claim-without-evidence markers.
#: Used to separate user opinions from verified facts in IntentFrame.
USER_CLAIM_MARKERS: tuple[str, ...] = (
    # ── 中文：发现/断言 ──
    "我发现", "我确定", "我肯定", "我确认", "我保证",
    "一定是", "肯定是", "绝对是", "确实是", "肯定是",
    "确凿", "证据确凿", "众所周知", "已知", "常识",
    "实际上是", "本质上是", "说白了",
    # ── 中文：自证测试 ──
    "测试过了", "跑过了", "已经验证", "验证过了", "测过了",
    "没问题", "保证没问题",
    # ── English ──
    "i found", "i confirm", "i determined", "i guarantee",
    "i'm sure", "i am sure", "i'm certain", "i am certain",
    "definitely", "absolutely", "certainly", "proven", "verified",
    "it must be", "it is clearly", "obviously",
    "trust me", "i tested", "i verified", "i checked",
    # ── Common bug assertion ──
    "bug", "fact", "事实",
)


_GOAL_MARKER_RULES = (
    ("settings_panel", (
        "settings panel",
        "settings ui",
        "settings",
        "config panel",
        "\u8bbe\u7f6e\u9762\u677f",
        "\u8bbe\u7f6e",
        "\u914d\u7f6e\u9762\u677f",
    )),
    ("layout", (
        "layout",
        "responsive",
        "position",
        "\u5e03\u5c40",
        "\u6392\u7248",
    )),
    ("spacing", (
        "spacing",
        "gap",
        "padding",
        "margin",
        "white space",
        "whitespace",
        "\u95f4\u8ddd",
        "\u7559\u767d",
        "\u8fb9\u8ddd",
    )),
    ("touch_target_44px", (
        "44px",
        "44 px",
        "touch target",
        "tap target",
        "hit target",
        "\u89e6\u6478",
        "\u70b9\u51fb\u533a",
    )),
    ("scroll", (
        "scroll",
        "wheel",
        "overflow",
        "\u6eda\u8f6e",
        "\u6eda\u52a8",
        "\u8d85\u51fa\u9875\u9762",
    )),
    ("multilingual", (
        "multilingual",
        "multi-language",
        "i18n",
        "language",
        "\u591a\u8bed\u8a00",
        "\u4e2d\u82f1",
    )),
    ("operation_guide", (
        "operation guide",
        "guide",
        "help",
        "\u64cd\u4f5c\u6307\u5357",
        "\u8bf4\u660e",
    )),
    ("agent_workflow", (
        "agent workflow",
        "workflow",
        "child agent",
        "sub-agent",
        "subagent",
        "react",
        "\u5de5\u4f5c\u6d41",
        "\u5b50 agent",
        "\u5b50agent",
    )),
    ("approval_loop", (
        "approval",
        "approve",
        "human approval",
        "\u5ba1\u6279",
        "\u4eba\u7c7b\u786e\u8ba4",
    )),
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

        for marker in BYPASS_MARKERS:
            if marker.lower() in lowered:
                if "bypass_pressure" not in contamination:
                    contamination.append("bypass_pressure")
                break  # one hit is enough

        # Scope markers: high-precision ones trigger immediately;
        # contextual ones (全部/所有/整个) only trigger if a sensitive noun follows.
        for marker in SCOPE_MARKERS:
            if marker in _SCOPE_CONTEXTUAL_MARKERS:
                continue  # handled separately below
            if marker.lower() in lowered:
                if "scope_pressure" not in contamination:
                    contamination.append("scope_pressure")
                break
        if "scope_pressure" not in contamination:
            for marker in _SCOPE_CONTEXTUAL_MARKERS:
                idx = 0
                while True:
                    pos = lowered.find(marker, idx)
                    if pos == -1:
                        break
                    # Check if a sensitive noun appears within 6 chars after the marker
                    tail = lowered[pos + len(marker):pos + len(marker) + 6]
                    if any(noun in tail for noun in _SCOPE_SENSITIVE_NOUNS):
                        if "scope_pressure" not in contamination:
                            contamination.append("scope_pressure")
                        break
                    idx = pos + len(marker)

        # Atomic intent splitting: handle all CN/EN sentence-ending punctuation
        # and enumeration commas (、) that Chinese uses for parallel items.
        atomic = tuple(
            part.strip(" ，。；;！？、!? \t")
            for part in text
                .replace("，", ";").replace("。", ";")
                .replace("！", ";").replace("？", ";")
                .replace("、", ";").replace("!", ";").replace("?", ";")
                .split(";")
            if part.strip(" ，。；;！？、!? \t")
        )
        claims = tuple(
            part for part in atomic
            if any(token.lower() in part.lower() for token in USER_CLAIM_MARKERS)
        )
        codes = self._intent_codes(lowered)
        goal_markers = self._goal_markers(lowered)
        goal = self._stable_goal(codes, goal_markers)
        assumptions = ["user request is motivation, not evidence"]
        if goal_markers:
            assumptions.append("sanitized goal markers: " + ",".join(goal_markers))

        return IntentFrame(
            raw_text=text,
            stable_goal=goal,
            intent_codes=codes,
            atomic_intents=atomic,
            user_supplied_claims=claims,
            assumptions=tuple(assumptions),
            contamination_markers=tuple(contamination),
        )

    def _intent_codes(self, lowered: str) -> tuple[str, ...]:
        codes: list[str] = []
        rules = (
            ("bug_review", ("bug", "问题", "坏了", "抖动", "冲突", "报错", "崩溃", "异常")),
            ("ui_review", ("ui", "界面", "布局", "对话", "npc", "play", "面板", "页面", "样式")),
            ("architecture_review", ("架构", "语义污染", "工作流", "调度", "母 agent", "子 agent", "agent 架构")),
            ("implementation", ("实现", "修", "优化", "构建", "开发", "编写", "新增", "添加")),
            ("verification", ("测试", "验证", "评测", "审查", "检查", "确认")),
        )
        for code, needles in rules:
            if any(needle in lowered for needle in needles):
                codes.append(code)
        marker_codes = {
            "ui_review": ("layout", "settings", "scroll", "spacing", "touch target", "44px"),
            "architecture_review": ("workflow", "agent", "approval", "child agent", "subagent"),
            "implementation": ("do", "make", "improve", "fix", "update", "change", "build", "create", "add"),
            "verification": ("test", "verify", "review", "check"),
        }
        for code, needles in marker_codes.items():
            if code not in codes and any(needle in lowered for needle in needles):
                codes.append(code)
        return tuple(codes or ("general_request",))

    def _goal_markers(self, lowered: str) -> tuple[str, ...]:
        markers: list[str] = []
        for marker, needles in _GOAL_MARKER_RULES:
            if any(needle.lower() in lowered for needle in needles):
                markers.append(marker)
        return tuple(markers)

    def _stable_goal(self, codes: tuple[str, ...], goal_markers: tuple[str, ...] = ()) -> str:
        goal = "execute sanitized intent codes: " + ",".join(codes)
        if goal_markers:
            goal += "; goal markers: " + ",".join(goal_markers)
        return goal
