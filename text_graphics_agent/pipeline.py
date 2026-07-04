"""Agent pipeline orchestrator.

The :class:`Pipeline` class is the single entry point for running a user
request through the full TGA safety workflow:

    raw_text → intent firewall → clarification → task sanitization
             → specialist dispatch → constraint verdict → structured result

This module replaces the 558-line ``simulate_pipeline_payload`` god-function
that previously lived in ``gui.py``.  ``gui.py`` now only does HTTP routing
and JSON serialization — all business logic lives here.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from .agent_cards import default_agent_cards, web_specialist_card
from .config import load_config
from .intent import IntentDecomposer
from .memory import MemoryStore, extract_memories_from_task, extract_memories_from_result
from .orchestrator import MotherAgent
from .profiles import RegisteredSpecialist, SpecialistProfile
from .records import AgentProposal, TaskSpec
from .registry import AgentRegistry, default_registry
from .specialists import BaseSpecialist, LiveSpecialist, LocalSimulationSpecialist
from .workflow_events import workflow_artifact, workflow_event


# ── Chat / clarification helpers (moved from gui.py) ────────────────────

_UNDERSTANDING_ACTION_MARKERS = (
    "检查", "修改", "实现", "修", "优化", "构建", "分析", "配置",
    "使用", "声明", "冒用", "伪装", "穿越", "绕审", "调整", "写",
    "生成", "测试", "验证", "动作",
    "check", "review", "fix", "build", "implement", "update", "change",
    "analyze", "configure", "test",
)

_VAGUE_REQUESTS = {
    "看看", "处理一下", "优化一下", "帮我弄一下", "搞一下", "看下",
    "do it", "fix it", "make it better",
}

_CASUAL_CHAT_MARKERS = (
    "单纯聊天", "闲聊", "聊天", "聊聊", "感觉怎么样", "觉得怎么样",
    "你觉得", "你怎么看", "怎么看", "怎么样",
    "hello", "hi", "how are you", "what do you think",
)

_FACT_WRITE_MARKERS = (
    "事实", "直接写", "write facts",
    "confirmed_fact", "committed_fact", "direct_ledger_write",
)


def _normalize_task_scopes(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        raw_items = value.replace("\n", ",").replace(";", ",").replace("；", ",").replace("，", ",").split(",")
    elif isinstance(value, (list, tuple)):
        raw_items = value
    else:
        raw_items = (value,)
    scopes: list[str] = []
    seen: set[str] = set()
    for item in raw_items:
        scope = str(item or "").strip().replace("\\", "/")
        while scope.startswith("./"):
            scope = scope[2:]
        if not scope or scope in seen:
            continue
        scopes.append(scope)
        seen.add(scope)
    return tuple(scopes)


def _normalize_task_anchors(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        raw_items = value.replace("\n", ",").replace(";", ",").replace("；", ",").replace("，", ",").split(",")
    elif isinstance(value, (list, tuple)):
        raw_items = value
    else:
        raw_items = (value,)
    anchors: list[str] = []
    seen: set[str] = set()
    for item in raw_items:
        anchor = " ".join(str(item or "").split())
        if not anchor or anchor in seen:
            continue
        anchors.append(anchor[:120])
        seen.add(anchor)
    return tuple(anchors)


def _normalize_conversation_history(value: Any, limit: int = 8) -> tuple[dict[str, str], ...]:
    if not isinstance(value, list):
        return ()
    normalized: list[dict[str, str]] = []
    for item in value[-limit:]:
        if not isinstance(item, dict):
            continue
        role = str(item.get("role") or "").strip()
        content = str(item.get("content") or "").strip()
        if role and content:
            normalized.append({"role": role, "content": content})
    return tuple(normalized)


def _invalid_task_scopes(scopes: tuple[str, ...]) -> tuple[str, ...]:
    invalid: list[str] = []
    for scope in scopes:
        normalized = scope.replace("\\", "/")
        first_segment = normalized.split("/", 1)[0]
        if (
            normalized.startswith(("/", "~"))
            or ":" in first_segment
            or any(part == ".." for part in normalized.split("/"))
        ):
            invalid.append(scope)
    return tuple(invalid)


def _has_task_action_marker(raw_text: str) -> bool:
    lowered = str(raw_text or "").lower()
    return any(marker in lowered for marker in _UNDERSTANDING_ACTION_MARKERS)


def _is_casual_chat_request(raw_text: str) -> bool:
    text = " ".join(str(raw_text or "").split())
    if not text or text.lower() in _VAGUE_REQUESTS:
        return False
    lowered = text.lower()
    if _has_task_action_marker(lowered):
        return False
    return any(marker in lowered for marker in _CASUAL_CHAT_MARKERS)


def _should_continue_chat(raw_text: str, conversation_history: tuple[dict[str, str], ...]) -> bool:
    if not conversation_history:
        return False
    text = " ".join(str(raw_text or "").split())
    if not text or text.lower() in _VAGUE_REQUESTS:
        return False
    return not _has_task_action_marker(text)


def _chat_agent_descriptor() -> dict[str, Any]:
    return {
        "agent_id": "tga-chat",
        "name": "TGA Chat",
        "description": "Direct conversation mode for non-task user input.",
        "version": "1.0.0",
        "default_input_modes": ["text"],
        "default_output_modes": ["assistant_message", "status_update"],
        "capabilities": {
            "streaming": False,
            "disposable": False,
            "proposal_only": False,
            "receives_raw_user_text": True,
            "persistent_memory": False,
        },
        "skills": [],
        "safety_contract": [
            "Does not dispatch a child agent for casual conversation.",
            "Does not create TaskSpec, AgentProposal, or checked state.",
            "Directs executable work back into the scoped agent workflow.",
        ],
        "approval_required_for": [],
    }


def _casual_chat_message(raw_text: str, conversation_history: tuple[dict[str, str], ...] = ()) -> tuple[str, str]:
    has_cjk = any("\u4e00" <= char <= "\u9fff" for char in str(raw_text or ""))
    if conversation_history:
        zh = (
            "可以连续聊。我会保留当前浏览器会话里的最近几轮普通聊天，用它来理解你后续的"
            "“那怎么办、为什么、继续说”这类追问。但它仍然不会自动变成执行任务；"
            "只有你明确说检查、实现、修复、验证，并给出文件或验收标准时，才会切到 TaskSpec 和子 agent。"
        )
        en = (
            "Yes, this can continue as a conversation. I keep the recent casual-chat turns from this browser session "
            "so follow-ups like 'why' or 'go on' stay in context. It still does not become an executable task until "
            "you explicitly ask to inspect, implement, fix, or verify with a file or acceptance criterion."
        )
    else:
        zh = (
            "可以，这类输入应该按普通聊天处理，不该逼你补文件范围或验收标准。"
            "就这个 agent 平台本身看，核心边界是有价值的：任务要变成 TaskSpec，子 agent 只拿受控任务，"
            "失败时给出原因。现在主要短板是入口太硬，普通用户需要先能自然聊天，再在需要执行时一键转成任务。"
            "如果你要我真正干活，就补一句“检查/实现/修复/验证”加文件或验收标准。"
        )
        en = (
            "This should be handled as normal chat, not as a scoped task that asks for files or acceptance criteria. "
            "The platform has a useful core boundary: work becomes a TaskSpec, child agents receive controlled tasks, "
            "and failures explain why they were blocked. The weak spot is the entry experience: users need to chat "
            "naturally first, then turn the conversation into a task when they want execution."
        )
    return (zh if has_cjk else en, en)


def _chat_response(
    raw_text: str,
    conversation_history: tuple[dict[str, str], ...],
    *,
    provider: str,
    api_key: str,
    model: str,
    use_live: bool,
) -> tuple[str, str, str, str]:
    fallback_message, fallback_en = _casual_chat_message(raw_text, conversation_history)
    if not use_live:
        return fallback_message, fallback_en, "local_fallback", ""

    try:
        from .api_benchmark import call_live_chat

        live_message = call_live_chat(
            provider=provider,
            api_key=api_key.strip(),
            model=model,
            messages=_live_chat_messages(raw_text, conversation_history),
            timeout=45.0,
        )
    except Exception as exc:
        return fallback_message, fallback_en, "local_fallback", f"{type(exc).__name__}: {str(exc)[:240]}"

    if not live_message:
        return fallback_message, fallback_en, "local_fallback", "empty live chat response"
    return live_message, live_message, "live_llm", ""


def _live_chat_messages(raw_text: str, conversation_history: tuple[dict[str, str], ...]) -> list[dict[str, str]]:
    messages = [
        {
            "role": "system",
            "content": (
                "You are TGA Chat, the non-task conversation mode inside Text Graphics Agent. "
                "Reply naturally to the user. You may discuss ideas and answer questions, but you must not claim to have inspected, "
                "modified, tested, or written local files. If the user asks for executable work, tell them to provide file scope and "
                "acceptance criteria so the request can enter the TaskSpec workflow. Do not produce AgentProposal JSON."
            ),
        }
    ]
    for turn in conversation_history[-6:]:
        role = "assistant" if turn.get("role") == "assistant" else "user"
        content = " ".join(str(turn.get("content") or "").split())
        if content:
            messages.append({"role": role, "content": content[:800]})
    messages.append({"role": "user", "content": str(raw_text or "")[:1600]})
    return messages


def _clarification_questions(raw_text: str) -> list[str]:
    text = " ".join(str(raw_text or "").split())
    lowered = text.lower()
    if not text or len(text) < 6 or lowered in _VAGUE_REQUESTS:
        return [
            "请补充你要 agent 处理的具体对象，例如文件、页面、模块或配置项。",
            "请说明期望结果，例如修复、分析、生成方案、运行验证或提交变更。",
        ]
    if not any(marker in lowered for marker in _UNDERSTANDING_ACTION_MARKERS):
        return [
            "我还没有识别到明确动作。请说明要检查、修改、实现、分析还是验证。",
            "请给出至少一个范围或验收标准，避免子 agent 自行扩大任务。",
        ]
    return []


def _clarification_questions_en(raw_text: str) -> list[str]:
    text = " ".join(str(raw_text or "").split())
    lowered = text.lower()
    if not text or len(text) < 6 or lowered in _VAGUE_REQUESTS:
        return [
            "Add the concrete object the agent should handle, such as a file, page, module, or config item.",
            "State the expected outcome, such as a fix, analysis, plan, verification run, or submitted change.",
        ]
    if not any(marker in lowered for marker in _UNDERSTANDING_ACTION_MARKERS):
        return [
            "I did not detect a clear action. Say whether this is an inspection, change, implementation, analysis, or verification task.",
            "Add at least one scope or acceptance criterion so the child agent cannot expand the task by itself.",
        ]
    return []


def _rejection_next_step(violations: list[str]) -> str:
    if any(v.startswith("goal_drift:") for v in violations):
        return "repair_goal"
    if any(v.startswith(("scope_escape:", "scope_path_traversal:", "evidence_path_traversal:")) for v in violations):
        return "revise_scope"
    if any(v.startswith(("bypass_language:", "dangerous_test_command:", "proposal_kind_expansion:")) for v in violations):
        return "revise_request"
    if any(v.startswith("forbidden_output:") for v in violations):
        return "request_ledger_approval"
    return "clarify_and_retry"


def _goal_marker_note(objective: str) -> str:
    lowered = objective.lower()
    marker_prefix = "goal markers:"
    if marker_prefix not in lowered:
        return ""
    marker_text = lowered.split(marker_prefix, 1)[1].split(";", 1)[0]
    markers = [m.strip() for m in marker_text.replace(",", " ").split() if m.strip()]
    return ", ".join(markers)


# ── Pipeline result type ───────────────────────────────────────────────


class PipelineResult:
    """Structured result from :meth:`Pipeline.submit`.

    Attributes are populated depending on the execution path taken (chat,
    clarification, error, or full dispatch).
    """

    def __init__(self) -> None:
        self.status: str = "complete"
        self.mode: str | None = None
        self.needs_clarification: bool = False
        self.next_action: str = "complete"
        self.message: str | None = None
        self.message_en: str | None = None
        self.user_result: str | None = None
        self.conversation_history: list[dict[str, str]] = []
        self.agent_registry: list[dict[str, Any]] = []
        self.selected_agent: dict[str, Any] = {}
        self.intent: dict[str, Any] = {}
        self.task: dict[str, Any] = {}
        self.proposal: dict[str, Any] = {}
        self.checked_record: dict[str, Any] = {}
        self.clarification_questions: list[str] = []
        self.clarification_questions_en: list[str] = []
        self.workflow_events: list[dict[str, Any]] = []
        self.error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to the dict shape expected by the web frontend."""
        d: dict[str, Any] = {"status": self.status}
        if self.mode is not None:
            d["mode"] = self.mode
        d["needs_clarification"] = self.needs_clarification
        if self.message is not None:
            d["message"] = self.message
        if self.message_en is not None:
            d["message_en"] = self.message_en
        if self.user_result is not None:
            d["user_result"] = self.user_result
        if self.conversation_history:
            d["conversation_history"] = self.conversation_history
        d["agent_registry"] = self.agent_registry
        d["selected_agent"] = self.selected_agent
        d["workflow_events"] = self.workflow_events
        d["next_action"] = self.next_action
        if self.intent:
            d["intent"] = self.intent
        if self.task:
            d["task"] = self.task
        if self.proposal:
            d["proposal"] = self.proposal
        if self.checked_record:
            d["checked_record"] = self.checked_record
        if self.clarification_questions:
            d["clarification_questions"] = self.clarification_questions
        if self.clarification_questions_en:
            d["clarification_questions_en"] = self.clarification_questions_en
        if self.error:
            d["error"] = self.error
        return d


# ── Pipeline ───────────────────────────────────────────────────────────


class Pipeline:
    """Orchestrates the full TGA request workflow.

    Usage::

        pipeline = Pipeline()
        result = pipeline.submit(raw_text="Fix settings panel layout")
        return result.to_dict()

    The pipeline reads configuration from ``config.json`` on each call,
    so changes to settings take effect immediately.
    """

    def __init__(self, registry: AgentRegistry | None = None) -> None:
        self._mother = MotherAgent()
        self._decomposer = IntentDecomposer()
        self._registry = registry  # built lazily in submit() if None
        self._memory = MemoryStore()

    def submit(
        self,
        raw_text: str,
        run_live: bool = False,
        task_scopes: Any = None,
        task_anchors: Any = None,
        conversation_history: Any = None,
        specialist: BaseSpecialist | None = None,
    ) -> PipelineResult:
        """Run *raw_text* through the full safety pipeline.

        Args:
            raw_text: Untrusted user input (will be sanitized).
            run_live: If True and an API key is configured, use a live LLM.
            task_scopes: Per-request file scope override (string or list).
            task_anchors: Per-request required evidence anchors (string or list).
            conversation_history: Browser-supplied chat history for continuity.
            specialist: Optional custom specialist.  If None, a local or live
                specialist is auto-selected based on *run_live* and config.

        Returns:
            A :class:`PipelineResult` describing the outcome.
        """
        result = PipelineResult()
        config = load_config()

        configured_scopes = tuple(str(s) for s in (config.get("allowed_scopes") or []))
        requested_scopes = _normalize_task_scopes(task_scopes)
        requested_anchors = _normalize_task_anchors(task_anchors)
        chat_history = _normalize_conversation_history(conversation_history)
        invalid_scopes = _invalid_task_scopes(requested_scopes)
        allowed_scopes = requested_scopes or configured_scopes
        required_anchors = requested_anchors or tuple(config.get("required_anchors") or [])
        api_key = config.get("api_key") or ""
        provider = config.get("api_provider") or "gemini"
        model = config.get("model_name") or ""
        use_live_child = bool(run_live and api_key.strip())

        # ── Build or use registry ─────────────────────────────────
        if self._registry is None:
            self._registry = default_registry(
                provider=provider,
                api_key=api_key,
                model=model,
                use_live=use_live_child,
            )

        # If no custom specialist was passed, use registry routing.
        # Otherwise fall back to the legacy card for display purposes.
        registry_entry = None
        if specialist is None:
            registry_entry = self._registry.select(
                intent_codes=tuple(),  # will refine after intent decomposition
                goal_markers=tuple(),
            )

        if registry_entry and registry_entry.card:
            result.selected_agent = registry_entry.card
        else:
            selected_card = web_specialist_card(
                child_agent_id="web-child-live" if use_live_child else "web-child-009",
                live=use_live_child,
            )
            result.selected_agent = selected_card.to_dict()

        registry_cards = self._registry.cards()
        result.agent_registry = registry_cards if registry_cards else [card.to_dict() for card in default_agent_cards()]

        # ── Step 1: Intent firewall ───────────────────────────────
        intent = self._decomposer.decompose(raw_text)
        result.intent = asdict(intent)
        result.workflow_events.extend(self._intent_events(intent))

        # ── Step 2: Casual chat shortcut ──────────────────────────
        if _is_casual_chat_request(raw_text) or _should_continue_chat(raw_text, chat_history):
            self._handle_chat(raw_text, chat_history, result, provider, api_key, model, use_live_child)
            return result

        # ── Step 3: Clarification check ───────────────────────────
        questions = _clarification_questions(raw_text)
        questions_en = _clarification_questions_en(raw_text)
        if questions:
            self._handle_clarification(questions, questions_en, result)
            return result

        # ── Step 4: Invalid scope check ───────────────────────────
        if invalid_scopes:
            self._handle_invalid_scopes(invalid_scopes, result)
            return result

        # ── Step 5: Task sanitization ─────────────────────────────
        # Recall curated memory — these are UNTRUSTED hints that help the
        # mother agent reason, but they never enter objective or affect
        # constraint decisions.
        memory_entries = self._memory.recall_for_intent(
            intent_codes=intent.intent_codes,
            goal_markers=tuple(),
        )
        memory_hints = tuple(e.content for e in memory_entries if e.confidence >= 0.3)

        task = self._mother.make_clean_task(
            intent,
            task_id="web-task-102",
            allowed_scopes=allowed_scopes,
            required_anchors=required_anchors,
            memory_hints=memory_hints,
        )
        result.task = asdict(task)

        # ── Step 5b: Registry routing (now that we know intent) ───
        # Re-select with actual intent codes and goal markers so the
        # best-matching specialist is chosen.
        if specialist is None and self._registry is not None:
            registry_entry = self._registry.select(
                intent_codes=intent.intent_codes,
                goal_markers=tuple(),  # goal markers are in task.objective, parsed later
            )
            if registry_entry:
                specialist = registry_entry.factory(
                    allowed_scopes=allowed_scopes,
                    required_anchors=tuple(required_anchors),
                )
                if registry_entry.card:
                    result.selected_agent = registry_entry.card

        # Build display values for the dispatch event
        dispatch_agent_id = result.selected_agent.get("agent_id", "web-child-009") if result.selected_agent else ("web-child-live" if use_live_child else "web-child-009")
        dispatch_agent_card = result.selected_agent if result.selected_agent else web_specialist_card(
            child_agent_id="web-child-live" if use_live_child else "web-child-009",
            live=use_live_child,
        ).to_dict()

        result.workflow_events.append(self._dispatch_event(task, dispatch_agent_id, dispatch_agent_card, requested_scopes))

        # ── Step 6: Specialist execution ──────────────────────────
        if specialist is None:
            if use_live_child:
                specialist = LiveSpecialist(
                    provider=provider,
                    api_key=api_key,
                    model=model,
                    allowed_scopes=allowed_scopes,
                )
            else:
                specialist = LocalSimulationSpecialist(
                    allowed_scopes=allowed_scopes,
                    required_anchors=tuple(required_anchors),
                )

        # Demo-only: inject raw text into the local simulator so it can
        # reproduce adversarial scenarios.  Real specialists ignore this.
        if isinstance(specialist, LocalSimulationSpecialist):
            specialist.set_raw_text(raw_text)

        try:
            proposals = self._run_specialist(specialist, task, use_live_child, provider, model, result)
        except Exception as err:
            self._handle_specialist_error(err, intent, task, result)
            return result

        proposal = proposals[0]
        result.proposal = asdict(proposal)

        # ── Step 7: Constraint verdict ────────────────────────────
        self._handle_verdict(proposal, task, allowed_scopes, result)

        # ── Step 8: Memory extraction ────────────────────────────
        # Extract objective observations from the completed task.
        # This does NOT store raw user text, user claims, or proposal
        # content — only sanitized metadata like scopes, intent codes,
        # and violation categories.
        self._extract_and_store_memories(
            intent=intent,
            allowed_scopes=allowed_scopes,
            task_id=task.task_id,
            checked_record=result.checked_record,
        )

        return result

    # ── Event builders ──────────────────────────────────────────────

    def _intent_events(self, intent) -> list[dict[str, Any]]:
        return [
            workflow_event(
                "observe",
                "需求进入",
                "已接收用户原始需求，先作为不可信输入进入 Intent Firewall。",
                title_en="Request received",
                detail_en="Raw user input was received as untrusted text and routed through the Intent Firewall.",
                details={
                    "stage": "observe",
                    "boundary": "raw user text stays outside child agent dispatch",
                    "raw_length": len(intent.raw_text),
                },
            ),
            workflow_event(
                "think",
                "理解任务",
                f"识别到意图代码：{', '.join(intent.intent_codes)}；污染标记：{', '.join(intent.contamination_markers) or 'none'}。",
                title_en="Understand task",
                detail_en=f"Detected intent codes: {', '.join(intent.intent_codes)}; contamination markers: {', '.join(intent.contamination_markers) or 'none'}.",
                details={
                    "stable_goal": intent.stable_goal,
                    "intent_codes": list(intent.intent_codes),
                    "atomic_intents": list(intent.atomic_intents),
                    "user_supplied_claims": list(intent.user_supplied_claims),
                    "contamination_markers": list(intent.contamination_markers),
                    "assumptions": list(intent.assumptions),
                },
            ),
        ]

    def _dispatch_event(self, task, agent_id, agent_card, requested_scopes) -> dict[str, Any]:
        return workflow_event(
            "dispatch",
            "派发子 agent",
            "需求已转成受控 TaskSpec，派发给一次性 child:web-specialist；子 agent 不接触原始用户文本。",
            child_agent=agent_id,
            title_en="Dispatch child agent",
            detail_en="The request became a controlled TaskSpec and was dispatched to a disposable child:web-specialist; the child does not receive raw user text.",
            details={
                "agent_card": agent_card,
                "task_spec": asdict(task),
                "requested_local_scopes": list(requested_scopes),
                "scope_source": "per_task" if requested_scopes else "settings",
            },
            artifacts=(
                workflow_artifact(
                    "task-spec:web-task-102",
                    kind="task_spec",
                    title="Sanitized TaskSpec",
                    payload=asdict(task),
                    last_chunk=True,
                ),
            ),
        )

    # ── Execution handlers ──────────────────────────────────────────

    def _run_specialist(
        self,
        specialist: BaseSpecialist,
        task: TaskSpec,
        use_live: bool,
        provider: str,
        model: str,
        result: PipelineResult,
    ) -> list[AgentProposal]:
        if use_live:
            result.workflow_events.append(
                workflow_event(
                    "act",
                    "调用外部模型",
                    f"准备调用 {provider}/{model or 'default model'}，只发送净化后的 TaskSpec。",
                    tool="live_llm",
                    status="running",
                    title_en="Call external model",
                    detail_en=f"Preparing to call {provider}/{model or 'default model'} with the sanitized TaskSpec only.",
                    details={
                        "tool_call": {
                            "name": "live_llm",
                            "provider": provider,
                            "model": model or "default model",
                            "input": "sanitized_task_spec",
                        },
                        "task_id": task.task_id,
                    },
                )
            )

        proposals = specialist.run(task)

        # Record execution events
        if use_live and isinstance(specialist, LiveSpecialist):
            self._live_events(specialist, proposals[0] if proposals else None, result)
        else:
            self._local_events(proposals[0] if proposals else None, result, result.selected_agent)

        return proposals

    def _live_events(self, specialist: LiveSpecialist, proposal, result: PipelineResult) -> None:
        if specialist.had_repair:
            result.workflow_events.append(
                workflow_event(
                    "repair",
                    "Auto-repair proposal",
                    "The first proposal failed admission precheck; retrying once with the sanitized task and rejection reasons.",
                    status="running",
                    tool="live_llm",
                    title_en="Auto-repair proposal",
                    detail_en="The first proposal failed admission precheck. The mother agent asks for one repair using only the sanitized task and rejection reasons.",
                    details={
                        "attempt": 1,
                        "violations": specialist.last_violations,
                        "previous_output": specialist.last_live_json,
                    },
                )
            )
            if proposal:
                result.workflow_events.append(
                    workflow_event(
                        "repair",
                        "Repair result returned",
                        "The model returned one repaired proposal for the formal mother-agent verdict.",
                        status="done",
                        tool="live_llm",
                        title_en="Repair result returned",
                        detail_en="The model returned one repaired proposal; it now goes through the formal mother-agent verdict.",
                        details={"parse_ok": True, "proposal": asdict(proposal)},
                        artifacts=(
                            workflow_artifact(
                                f"proposal:{proposal.child_agent_id}:{proposal.task_id}:repair",
                                kind="agent_proposal",
                                title="Repaired AgentProposal",
                                payload=asdict(proposal),
                                last_chunk=True,
                            ),
                        ),
                    )
                )
        if proposal:
            result.workflow_events.append(
                workflow_event(
                    "tool_result",
                    "模型返回提案",
                    "外部模型返回 AgentProposal，进入母 agent 约束裁决。",
                    tool="live_llm",
                    title_en="Model returned proposal",
                    detail_en="The external model returned an AgentProposal for mother-agent constraint adjudication.",
                    details={"proposal": asdict(proposal), "parse_ok": True},
                    artifacts=(
                        workflow_artifact(
                            f"proposal:{proposal.child_agent_id}:{proposal.task_id}",
                            kind="agent_proposal",
                            title="AgentProposal",
                            payload=asdict(proposal),
                            last_chunk=True,
                        ),
                    ),
                )
            )

    def _local_events(self, proposal, result: PipelineResult, selected_agent) -> None:
        if not proposal:
            return
        result.workflow_events.append(
            workflow_event(
                "act",
                "子 agent 执行任务",
                "子 agent 基于受控任务生成提案，并声明证据、范围、输出类型和验证命令。",
                tool="local_specialist",
                title_en="Child agent executes task",
                detail_en="The child agent generated a proposal from the controlled task and declared evidence, scope, output type, and verification commands.",
                details={
                    "tool_call": {
                        "name": "local_specialist.run",
                        "child_agent_id": proposal.child_agent_id,
                        "input": "sanitized_task_spec",
                    },
                    "agent_card": selected_agent,
                },
            )
        )
        result.workflow_events.append(
            workflow_event(
                "tool_result",
                "子 agent 返回结果",
                f"提案类型={proposal.proposal_kind}；证据={', '.join(proposal.evidence) or 'none'}；范围={', '.join(proposal.proposed_scopes) or 'none'}。",
                tool="local_specialist",
                title_en="Child agent returned result",
                detail_en=f"proposal_kind={proposal.proposal_kind}; evidence={', '.join(proposal.evidence) or 'none'}; scope={', '.join(proposal.proposed_scopes) or 'none'}.",
                details={
                    "proposal": asdict(proposal),
                    "artifact_update": {"append": False, "last_chunk": True},
                },
                artifacts=(
                    workflow_artifact(
                        f"proposal:{proposal.child_agent_id}:{proposal.task_id}",
                        kind="agent_proposal",
                        title="AgentProposal",
                        payload=asdict(proposal),
                        last_chunk=True,
                    ),
                ),
            )
        )

    def _handle_chat(
        self,
        raw_text,
        chat_history,
        result: PipelineResult,
        provider: str,
        api_key: str,
        model: str,
        use_live_child: bool,
    ) -> None:
        message, message_en, response_source, live_error = _chat_response(
            raw_text,
            chat_history,
            provider=provider,
            api_key=api_key,
            model=model,
            use_live=use_live_child,
        )
        chat_agent = _chat_agent_descriptor()
        result.workflow_events.append(
            workflow_event(
                "respond",
                "普通聊天",
                "识别为非执行任务输入，返回聊天回复，不派发子 agent。",
                title_en="Casual chat",
                detail_en="The input was classified as non-executable conversation, so TGA replied without dispatching a child agent.",
                details={
                    "mode": "chat",
                    "blocked_before_dispatch": False,
                    "task_spec_created": False,
                    "history_turns": len(chat_history),
                    "response_source": response_source,
                    **({"live_error": live_error} if live_error else {}),
                },
                artifacts=(
                    workflow_artifact(
                        "chat-response:tga-chat",
                        kind="assistant_message",
                        title="Assistant message",
                        payload={"message": message, "message_en": message_en},
                    ),
                ),
            )
        )
        result.status = "complete"
        result.mode = "chat"
        result.message = message
        result.message_en = message_en
        result.user_result = message
        result.conversation_history = list(chat_history)
        result.selected_agent = chat_agent
        result.next_action = "complete"

    def _handle_clarification(self, questions, questions_en, result: PipelineResult) -> None:
        result.workflow_events.append(
            workflow_event(
                "ask_user",
                "需要用户确认",
                "当前需求不足以安全派发子 agent。系统暂停执行，等待补充目标、范围或验收标准。",
                status="waiting",
                title_en="Need user clarification",
                detail_en="The request is not clear enough to safely dispatch a child agent. Execution is paused for goal, scope, or acceptance criteria.",
                details={"questions": questions, "questions_en": questions_en, "blocked_before_dispatch": True},
            )
        )
        result.status = "needs_clarification"
        result.needs_clarification = True
        result.clarification_questions = questions
        result.clarification_questions_en = questions_en
        result.next_action = "ask_user"

    def _handle_invalid_scopes(self, invalid_scopes, result: PipelineResult) -> None:
        result.workflow_events.append(
            workflow_event(
                "ask_user",
                "本地文件范围无效",
                "本次任务指定的文件范围包含绝对路径、驱动器前缀或路径穿越。系统暂停派发，等待用户改成工作区内相对路径。",
                status="waiting",
                title_en="Invalid local file scope",
                detail_en="The per-task file scope contains an absolute path, drive prefix, or path traversal. Dispatch is paused until the user provides workspace-relative paths.",
                details={"invalid_scopes": list(invalid_scopes), "blocked_before_dispatch": True},
            )
        )
        result.status = "needs_clarification"
        result.needs_clarification = True
        result.clarification_questions = [
            "请把本次任务文件改成工作区内相对路径，例如 docs/operation_guide.md 或 agent_workspace/tiny_game.html。",
            "不要使用绝对路径、盘符路径或包含 .. 的路径。",
        ]
        result.clarification_questions_en = [
            "Use workspace-relative paths, such as docs/operation_guide.md or agent_workspace/tiny_game.html.",
            "Do not use absolute paths, drive-prefixed paths, or paths containing '..'.",
        ]
        result.next_action = "ask_user"

    def _handle_specialist_error(self, err, intent, task, result: PipelineResult) -> None:
        result.workflow_events.append(
            workflow_event(
                "tool_result",
                "工具调用失败",
                f"外部模型调用失败：{err}",
                status="failed",
                tool="live_llm",
                title_en="Tool call failed",
                detail_en=f"External model call failed: {err}",
                details={"tool_call": "live_llm", "error": str(err)},
            )
        )
        result.status = "error"
        result.error = f"Live LLM call failed: {err}. Please check your API settings."
        result.intent = asdict(intent)
        result.task = asdict(task)

    def _handle_verdict(self, proposal, task, allowed_scopes, result: PipelineResult) -> None:
        specialist = RegisteredSpecialist(
            profile=SpecialistProfile(
                specialist_id=proposal.child_agent_id,
                role=proposal.child_role,
                allowed_scopes=allowed_scopes,
            ),
            run=lambda _task, p=proposal: [p],
        )
        checked, _score = self._mother.dispatch_registered(task, [specialist])
        checked_record = checked[0]
        violations = list(checked_record.violations)
        next_action = "complete" if checked_record.accepted else _rejection_next_step(violations)

        result.workflow_events.append(
            workflow_event(
                "decide",
                "母 agent / 规则层裁决",
                "提案通过准入检查。" if checked_record.accepted else "提案被规则层驳回，等待用户修改需求或补充授权后再继续。",
                status="accepted" if checked_record.accepted else "rejected",
                violations=violations,
                title_en="Mother agent / rule verdict",
                detail_en=(
                    "The proposal passed admission checks."
                    if checked_record.accepted
                    else "The rule layer rejected the proposal; revise the request or add authorization before continuing."
                ),
                details={
                    "checked_record": {
                        "accepted": checked_record.accepted,
                        "violations": violations,
                        "reviewer": checked_record.reviewer,
                    },
                    "next_action": next_action,
                    "status_update": {
                        "state": "completed" if checked_record.accepted else "rejected",
                        "final": True,
                    },
                },
                artifacts=(
                    workflow_artifact(
                        f"checked-record:{proposal.child_agent_id}:{proposal.task_id}",
                        kind="checked_record",
                        title="CheckedRecord",
                        payload={
                            "accepted": checked_record.accepted,
                            "violations": violations,
                            "reviewer": checked_record.reviewer,
                        },
                        last_chunk=True,
                    ),
                ),
            )
        )
        result.status = "complete"
        result.next_action = next_action
        result.checked_record = {
            "accepted": checked_record.accepted,
            "violations": violations,
            "reviewer": checked_record.reviewer,
        }

    def _extract_and_store_memories(
        self,
        intent,
        allowed_scopes: tuple[str, ...],
        task_id: str,
        checked_record: dict[str, Any],
    ) -> None:
        """Extract and persist curated memory from a completed task.

        Only stores objective observations (scopes, intent codes, violation
        categories).  Never stores raw user text, user claims, or proposal
        content.  Memory is untrusted context — it helps the mother agent
        reason but never affects constraint decisions.
        """
        # Extract from task metadata
        candidates = extract_memories_from_task(
            raw_text="",  # deliberately empty — we don't extract from raw text
            intent_codes=intent.intent_codes,
            goal_markers=tuple(),  # goal markers are in the objective, not repeated here
            allowed_scopes=allowed_scopes,
            task_id=task_id,
        )

        # Extract from result
        result_candidates = extract_memories_from_result(
            checked_record=checked_record,
            violations=checked_record.get("violations") if checked_record else None,
            task_id=task_id,
        )
        candidates.extend(result_candidates)

        # Store each candidate
        for category, content, confidence in candidates:
            self._memory.remember(
                category=category,
                content=content,
                source_task_id=task_id,
                confidence=confidence,
            )
