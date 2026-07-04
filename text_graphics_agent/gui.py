"""Small Windows-friendly Web GUI launcher for the research artifact.

Runs a zero-dependency HTTP server using standard library modules, serving
the dashboard and handling simulation API endpoints.
"""

from __future__ import annotations

import http.server
import json
import socketserver
import sys
import urllib.parse
import webbrowser
from dataclasses import asdict
from typing import Any

from .agent_cards import default_agent_cards, web_specialist_card
from .approval import approval_payload, evaluate_config_change, evaluate_live_model_call
from .benchmark import run_benchmark
from .config import normalize_config_data
from .demo import build_sample_task, polluted_specialist, ui_specialist
from .intent import (
    BYPASS_MARKERS,
    SCOPE_MARKERS,
    USER_CLAIM_MARKERS,
)
from .orchestrator import MotherAgent
from .web_resources import HTML_CONTENT
from .workflow_events import workflow_artifact, workflow_event

LOCAL_HOST = "127.0.0.1"
START_PORT = 8012

_UNDERSTANDING_ACTION_MARKERS = (
    "检查",
    "修改",
    "实现",
    "修",
    "优化",
    "构建",
    "分析",
    "配置",
    "使用",
    "声明",
    "冒用",
    "伪装",
    "穿越",
    "绕审",
    "调整",
    "写",
    "生成",
    "测试",
    "验证",
    "动作",
    "check",
    "review",
    "fix",
    "build",
    "implement",
    "update",
    "change",
    "analyze",
    "configure",
    "test",
)

_VAGUE_REQUESTS = {
    "看看",
    "处理一下",
    "优化一下",
    "帮我弄一下",
    "搞一下",
    "看下",
    "do it",
    "fix it",
    "make it better",
}

_CASUAL_CHAT_MARKERS = (
    "单纯聊天",
    "闲聊",
    "聊天",
    "聊聊",
    "感觉怎么样",
    "觉得怎么样",
    "你觉得",
    "你怎么看",
    "怎么看",
    "怎么样",
    "hello",
    "hi",
    "how are you",
    "what do you think",
    "just chat",
)


def normalize_task_scopes(value: Any) -> tuple[str, ...]:
    """Normalize per-request local file scope input into safe relative strings."""
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


def normalize_conversation_history(value: Any, limit: int = 8) -> tuple[dict[str, str], ...]:
    """Keep a compact browser-supplied chat history for continuity only."""
    if not isinstance(value, list):
        return ()
    normalized: list[dict[str, str]] = []
    for item in value[-limit:]:
        if not isinstance(item, dict):
            continue
        role = str(item.get("role") or "").strip().lower()
        if role not in {"user", "assistant"}:
            continue
        content = " ".join(str(item.get("content") or "").split())
        if not content:
            continue
        normalized.append({"role": role, "content": content[:600]})
    return tuple(normalized)


def invalid_task_scopes(scopes: tuple[str, ...]) -> tuple[str, ...]:
    """Reject local scope strings that could escape the workspace boundary."""
    invalid: list[str] = []
    for scope in scopes:
        parts = [part for part in scope.replace("\\", "/").split("/") if part]
        has_drive = len(scope) > 1 and scope[1] == ":"
        if scope.startswith(("/", "~")) or has_drive or "://" in scope or ".." in parts:
            invalid.append(scope)
    return tuple(invalid)


def has_task_action_marker(raw_text: str) -> bool:
    lowered = str(raw_text or "").lower()
    return any(marker in lowered for marker in _UNDERSTANDING_ACTION_MARKERS)


def is_casual_chat_request(raw_text: str) -> bool:
    text = " ".join(str(raw_text or "").split())
    if not text or text.lower() in _VAGUE_REQUESTS:
        return False
    lowered = text.lower()
    if has_task_action_marker(lowered):
        return False
    return any(marker in lowered for marker in _CASUAL_CHAT_MARKERS)


def should_continue_chat(raw_text: str, conversation_history: tuple[dict[str, str], ...]) -> bool:
    if not conversation_history:
        return False
    text = " ".join(str(raw_text or "").split())
    if not text or text.lower() in _VAGUE_REQUESTS:
        return False
    return not has_task_action_marker(text)


def chat_agent_descriptor() -> dict[str, Any]:
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


def casual_chat_message(raw_text: str, conversation_history: tuple[dict[str, str], ...] = ()) -> tuple[str, str]:
    has_cjk = any("\u4e00" <= char <= "\u9fff" for char in str(raw_text or ""))
    if conversation_history:
        zh = (
            "可以连续聊。我会保留当前浏览器会话里的最近几轮普通聊天，用它来理解你后续的“那怎么办、为什么、继续说”这类追问。"
            "但它仍然不会自动变成执行任务；只有你明确说检查、实现、修复、验证，并给出文件或验收标准时，才会切到 TaskSpec 和子 agent。"
        )
        en = (
            "Yes, this can continue as a conversation. I keep the recent casual-chat turns from this browser session so follow-ups like "
            "'why' or 'go on' stay in context. It still does not become an executable task until you explicitly ask to inspect, implement, fix, or verify with a file or acceptance criterion."
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
            "and failures explain why they were blocked. The weak spot is the entry experience: users need to chat naturally first, "
            "then turn the conversation into a task when they want execution."
        )
    return (zh if has_cjk else en, en)


class TgaHttpServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True


def demo_payload() -> dict:
    mother = MotherAgent()
    checked, score = mother.dispatch(build_sample_task(), [ui_specialist, polluted_specialist])
    return {
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
        },
    }


def self_check_payload() -> dict:
    benchmark = run_benchmark()
    checks = {
        "scenario_count_is_15": benchmark.scenario_count == 15,
        "unsafe_scenario_count_is_10": benchmark.unsafe_scenario_count == 10,
        "clean_scenario_count_is_5": benchmark.clean_scenario_count == 5,
        "baseline_accepts_pollution": benchmark.baseline_polluted_accepted == 10,
        "tga_rejects_all_pollution": benchmark.tga_polluted_accepted == 0,
        "tga_accepts_clean_tasks": benchmark.tga_clean_accepted == 5,
        "tga_clean_false_positive_rate_is_0": benchmark.tga_clean_false_positive_rate == 0.0,
        "unsafe_profile_blocked": benchmark.tga_blocked_before_spawn == 1,
    }
    return {
        "ok": all(checks.values()),
        "checks": checks,
        "benchmark": asdict(benchmark),
    }


def clarification_questions(raw_text: str) -> list[str]:
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


def clarification_questions_en(raw_text: str) -> list[str]:
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


def rejection_next_step(violations: list[str]) -> str:
    if any(v.startswith("goal_drift:") for v in violations):
        return "repair_goal"
    if any(v.startswith(("scope_escape:", "scope_path_traversal:", "evidence_path_traversal:")) for v in violations):
        return "revise_scope"
    if any(v.startswith(("bypass_language:", "dangerous_test_command:", "proposal_kind_expansion:")) for v in violations):
        return "revise_request"
    if any(v.startswith("forbidden_output:") for v in violations):
        return "request_ledger_approval"
    return "clarify_and_retry"


def goal_marker_note(objective: str) -> str:
    marker_prefix = "goal markers:"
    lowered = str(objective or "").lower()
    if marker_prefix not in lowered:
        return ""
    marker_text = lowered.split(marker_prefix, 1)[1].split(";", 1)[0]
    markers = [marker.strip() for marker in marker_text.replace(",", " ").split() if marker.strip()]
    return ", ".join(markers)


def simulate_pipeline_payload(
    raw_text: str,
    run_live: bool = False,
    task_scopes: Any = None,
    task_anchors: Any = None,
    conversation_history: Any = None,
) -> dict:
    """Run *raw_text* through the TGA safety pipeline.

    This function is now a thin delegate to :class:`Pipeline` in
    ``pipeline.py``.  All business logic — intent decomposition, chat
    detection, clarification, task sanitization, specialist dispatch,
    constraint verdict — lives there.
    """
    from .pipeline import Pipeline

    pipeline = Pipeline()
    result = pipeline.submit(
        raw_text=raw_text,
        run_live=run_live,
        task_scopes=task_scopes,
        task_anchors=task_anchors,
        conversation_history=conversation_history,
    )
    return result.to_dict()


def approval_required_response(decision) -> dict:
    return {
        "status": "approval_required",
        "approval_required": True,
        "approval": approval_payload(decision),
    }


def _test_api_connection(provider: str, api_key: str, model: str = "") -> dict:
    """Test API connectivity without running a full pipeline."""
    provider = (provider or "").strip()
    api_key = (api_key or "").strip()
    model = (model or "").strip()

    if not api_key:
        return {"ok": False, "error": "API key is required."}

    if provider == "mock":
        return {"ok": True, "provider": "mock", "model": "mock-model", "latency_ms": 0}

    try:
        from .api_benchmark import call_live_llm, resolve_openai_compatible_endpoint, resolve_openai_compatible_model
        import time

        if provider in ("openai", "deepseek"):
            endpoint = resolve_openai_compatible_endpoint(provider)
            resolved_model = model or resolve_openai_compatible_model(provider)
        else:
            endpoint = None
            resolved_model = model or "default"

        start = time.monotonic()
        # Send a minimal test message — must include 'json' for DeepSeek's response_format
        test_messages = [
            {"role": "system", "content": "Reply with a JSON object: {\"status\": \"ok\"}"},
            {"role": "user", "content": "ping — return json status"},
        ]
        result = call_live_llm(
            provider=provider,
            api_key=api_key,
            model=resolved_model,
            messages=test_messages,
            timeout=10.0,
        )
        latency = int((time.monotonic() - start) * 1000)
        return {
            "ok": True,
            "provider": provider,
            "model": resolved_model,
            "latency_ms": latency,
            "preview": str(result)[:100] if result else "",
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _list_workspace_files(base_dir: str = ".") -> dict:
    """List files in the workspace for the file scope picker."""
    from pathlib import Path

    root = Path(base_dir).resolve()
    if not root.exists() or not root.is_dir():
        return {"files": [], "error": f"Directory not found: {base_dir}"}

    # Collect source-like files only; generated environments make the scope picker noisy.
    ignore_dirs = {
        ".git",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".tox",
        ".venv",
        ".venv-build",
        ".codebuddy",
        "__pycache__",
        "build",
        "dist",
        "htmlcov",
        "node_modules",
        "site-packages",
        "venv",
    }
    ignore_exts = {".pyc", ".pyo", ".so", ".dll", ".exe", ".png", ".jpg", ".jpeg", ".gif", ".ico", ".woff", ".woff2"}

    files = []
    for item in sorted(root.rglob("*")):
        rel = item.relative_to(root)
        parts = rel.parts
        if any(part in ignore_dirs for part in parts):
            continue
        if item.is_file():
            if item.suffix.lower() in ignore_exts:
                continue
            files.append(str(rel).replace("\\", "/"))
        if len(files) >= 200:
            break

    return {"files": files, "base_dir": str(root)}


class TgaRequestHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: Any) -> None:
        # Suppress request logging to keep the console clean
        pass

    def do_GET(self) -> None:
        parsed_url = urllib.parse.urlparse(self.path)
        if self.path == "/" or self.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_CONTENT.encode("utf-8"))
        elif parsed_url.path == "/api/config":
            from .config import load_config
            config_data = load_config()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(config_data, ensure_ascii=False).encode("utf-8"))
        elif parsed_url.path == "/api/automation":
            from .automation import automation_status_payload
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(automation_status_payload(), ensure_ascii=False).encode("utf-8"))
        elif parsed_url.path == "/api/memory":
            from .memory import MemoryStore
            store = MemoryStore()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"memories": store.to_hints()}, ensure_ascii=False).encode("utf-8"))
        else:
            self.send_error(404, "File Not Found")

    def do_POST(self) -> None:
        parsed_url = urllib.parse.urlparse(self.path)
        if parsed_url.path == "/api/run":
            query_params = urllib.parse.parse_qs(parsed_url.query)
            mode = query_params.get("mode", [""])[0]

            response_data = {}
            if mode == "demo":
                response_data = demo_payload()
            elif mode == "benchmark":
                response_data = asdict(run_benchmark())
            elif mode == "self_check":
                response_data = self_check_payload()
            elif mode == "custom":
                content_length = int(self.headers.get("Content-Length") or 0)
                post_data = self.rfile.read(content_length)
                try:
                    payload = json.loads(post_data.decode("utf-8"))
                    raw_text = payload.get("raw_text") or ""
                    run_live = bool(payload.get("run_live"))
                    human_approved = bool(payload.get("human_approved"))
                    task_scopes = payload.get("local_scopes", payload.get("task_scopes"))
                    task_anchors = payload.get("local_anchors", payload.get("task_anchors"))
                    conversation_history = payload.get("conversation_history")
                    live_config = {}
                    if run_live:
                        from .config import load_config
                        live_config = load_config()
                    if (
                        run_live
                        and (live_config.get("api_key") or "").strip()
                        and not human_approved
                        and not is_casual_chat_request(raw_text)
                        and not should_continue_chat(raw_text, normalize_conversation_history(conversation_history))
                    ):
                        response_data = approval_required_response(
                            evaluate_live_model_call(
                                provider=live_config.get("api_provider") or "",
                                model_name=live_config.get("model_name") or "",
                            )
                        )
                    else:
                        response_data = simulate_pipeline_payload(
                            raw_text,
                            run_live=run_live,
                            task_scopes=task_scopes,
                            task_anchors=task_anchors,
                            conversation_history=conversation_history,
                        )
                except Exception as e:
                    self.send_error(400, f"Invalid JSON payload: {e}")
                    return
            else:
                self.send_error(400, f"Unknown mode: {mode}")
                return

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(response_data, ensure_ascii=False).encode("utf-8"))
        elif parsed_url.path == "/api/config":
            from .config import load_config, save_config
            content_length = int(self.headers.get("Content-Length") or 0)
            post_data = self.rfile.read(content_length)
            try:
                payload = json.loads(post_data.decode("utf-8"))
                human_approved = bool(payload.pop("human_approved", False))
                current_config = load_config()
                proposed_config = normalize_config_data(payload)
                approval_decision = evaluate_config_change(current_config, proposed_config)
                if approval_decision.required and not human_approved:
                    response_data = approval_required_response(approval_decision)
                else:
                    success = save_config(proposed_config)
                    response_data = {
                        "status": "ok" if success else "error",
                        "approval": approval_payload(approval_decision),
                    }
            except Exception as e:
                self.send_error(400, f"Invalid JSON payload: {e}")
                return
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(response_data, ensure_ascii=False).encode("utf-8"))
        elif parsed_url.path == "/api/automation":
            from .automation import run_automation_once
            response_data = run_automation_once()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(response_data, ensure_ascii=False).encode("utf-8"))
        elif parsed_url.path == "/api/test-connection":
            content_length = int(self.headers.get("Content-Length") or 0)
            post_data = self.rfile.read(content_length)
            try:
                payload = json.loads(post_data.decode("utf-8"))
                provider = payload.get("provider", "")
                api_key = payload.get("api_key", "")
                model = payload.get("model", "")
                response_data = _test_api_connection(provider, api_key, model)
            except Exception as e:
                response_data = {"ok": False, "error": str(e)}
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(response_data, ensure_ascii=False).encode("utf-8"))
        elif parsed_url.path == "/api/list-files":
            content_length = int(self.headers.get("Content-Length") or 0)
            post_data = self.rfile.read(content_length)
            try:
                payload = json.loads(post_data.decode("utf-8"))
                base_dir = payload.get("base_dir", ".")
                response_data = _list_workspace_files(base_dir)
            except Exception as e:
                response_data = {"files": [], "error": str(e)}
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(response_data, ensure_ascii=False).encode("utf-8"))
        elif parsed_url.path == "/api/memory" and self.command == "POST":
            content_length = int(self.headers.get("Content-Length") or 0)
            post_data = self.rfile.read(content_length)
            try:
                payload = json.loads(post_data.decode("utf-8"))
                action = payload.get("action", "")
                from .memory import MemoryStore
                store = MemoryStore()
                if action == "delete":
                    memory_id = payload.get("id", "")
                    ok = store.forget(memory_id)
                    response_data = {"ok": ok}
                elif action == "clear":
                    for entry in list(store._entries):
                        store.forget(entry.id)
                    response_data = {"ok": True}
                else:
                    response_data = {"ok": False, "error": "Unknown action"}
            except Exception as e:
                response_data = {"ok": False, "error": str(e)}
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(response_data, ensure_ascii=False).encode("utf-8"))
        else:
            self.send_error(404, "API Endpoint Not Found")


def main() -> None:
    port = START_PORT
    smoke = "--smoke" in sys.argv

    server = None
    while port < 9000:
        try:
            server = TgaHttpServer((LOCAL_HOST, port), TgaRequestHandler)
            break
        except OSError:
            port += 1

    if not server:
        print("Error: Could not find an open port.")
        sys.exit(1)

    url = f"http://{LOCAL_HOST}:{port}"
    print(f"Text Graphics Agent Web Dashboard Server started at {url}")

    if smoke:
        print("Server smoke test complete, shutting down.")
        server.server_close()
        return

    # Automatically open the browser
    webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer shutting down.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
