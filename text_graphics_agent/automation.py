"""Rule-driven automation runner for the Text Graphics Agent dashboard.

The runner is intentionally read-only. It can trigger checks and produce run
records, but it never commits facts, edits project files, or calls a live LLM.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Callable

from .benchmark import run_benchmark
from .config import load_config


@dataclass(frozen=True)
class AutomationJob:
    job_id: str
    title: str
    trigger: str
    cadence_seconds: int
    authority: str
    description: str


@dataclass(frozen=True)
class AutomationRun:
    run_id: str
    job_id: str
    status: str
    summary: str
    started_at: str
    finished_at: str
    state_writes: int
    details: dict[str, Any]


AUTOMATION_JOBS: tuple[AutomationJob, ...] = (
    AutomationJob(
        job_id="config_health",
        title="Config health check",
        trigger="startup/manual/scheduled",
        cadence_seconds=30,
        authority="rules",
        description="Check local config shape without exposing API secrets.",
    ),
    AutomationJob(
        job_id="platform_self_check",
        title="Platform self-check",
        trigger="startup/manual/scheduled",
        cadence_seconds=60,
        authority="rules",
        description="Verify the core deterministic invariants used by the dashboard.",
    ),
    AutomationJob(
        job_id="contamination_benchmark",
        title="Contamination benchmark",
        trigger="manual/scheduled",
        cadence_seconds=120,
        authority="rules",
        description="Run the closed-protocol pollution benchmark and summarize drift.",
    ),
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def available_automation_jobs() -> list[dict[str, Any]]:
    return [asdict(job) for job in AUTOMATION_JOBS]


def automation_status_payload() -> dict[str, Any]:
    return {
        "enabled_by_default": False,
        "recommended_interval_seconds": 30,
        "policy": {
            "runner_authority": "schedule_only",
            "decision_authority": "constraint_checker",
            "state_writes_allowed": False,
            "live_llm_calls_allowed": False,
            "approval_required_for": ["state_write", "external_publish", "credential_change"],
        },
        "jobs": available_automation_jobs(),
    }


def _config_health() -> tuple[str, str, dict[str, Any]]:
    config = load_config()
    allowed_scopes = config.get("allowed_scopes") or []
    required_anchors = config.get("required_anchors") or []
    disabled_constraints = config.get("disabled_constraints") or []
    provider = config.get("api_provider") or ""
    model_name = config.get("model_name") or ""
    api_key = config.get("api_key") or ""

    issues: list[str] = []
    warnings: list[str] = []
    if not isinstance(allowed_scopes, list) or not allowed_scopes:
        issues.append("allowed_scopes_missing")
    if not isinstance(required_anchors, list) or not required_anchors:
        issues.append("required_anchors_missing")
    if provider not in {"deepseek", "openai", "gemini", "mock"}:
        issues.append("unknown_api_provider")
    if not model_name.strip():
        warnings.append("model_name_missing")
    if not api_key.strip():
        warnings.append("api_key_missing_live_runs_disabled")
    if disabled_constraints:
        warnings.append("constraints_disabled")

    status = "failed" if issues else ("warning" if warnings else "ok")
    summary = "Config can run deterministic automation."
    if issues:
        summary = "Config has blocking shape issues."
    elif warnings:
        summary = "Config is usable, with non-blocking warnings."

    details = {
        "api_provider": provider,
        "model_configured": bool(model_name.strip()),
        "api_key_present": bool(api_key.strip()),
        "allowed_scope_count": len(allowed_scopes) if isinstance(allowed_scopes, list) else 0,
        "required_anchor_count": len(required_anchors) if isinstance(required_anchors, list) else 0,
        "disabled_constraints": list(disabled_constraints) if isinstance(disabled_constraints, list) else [],
        "issues": issues,
        "warnings": warnings,
    }
    return status, summary, details


def _platform_self_check() -> tuple[str, str, dict[str, Any]]:
    benchmark = run_benchmark()
    checks = {
        "scenario_count_is_6": benchmark.scenario_count == 6,
        "unsafe_scenario_count_is_5": benchmark.unsafe_scenario_count == 5,
        "baseline_accepts_pollution": benchmark.baseline_polluted_accepted == 5,
        "tga_rejects_all_pollution": benchmark.tga_polluted_accepted == 0,
        "unsafe_profile_blocked": benchmark.tga_blocked_before_spawn == 1,
    }
    failed = [name for name, passed in checks.items() if not passed]
    status = "ok" if not failed else "failed"
    summary = "All deterministic platform invariants passed." if not failed else "Self-check found invariant drift."
    return status, summary, {"checks": checks, "failed_checks": failed}


def _contamination_benchmark() -> tuple[str, str, dict[str, Any]]:
    benchmark = run_benchmark()
    accepted_pollution = benchmark.tga_polluted_accepted
    expected_baseline = benchmark.baseline_polluted_accepted == benchmark.unsafe_scenario_count
    ok = accepted_pollution == 0 and expected_baseline
    status = "ok" if ok else "failed"
    summary = (
        "TGA rejected all polluted proposals in the deterministic benchmark."
        if ok
        else "Benchmark drift detected; inspect pollution acceptance counts."
    )
    return status, summary, {"benchmark": asdict(benchmark)}


RUNNERS: dict[str, Callable[[], tuple[str, str, dict[str, Any]]]] = {
    "config_health": _config_health,
    "platform_self_check": _platform_self_check,
    "contamination_benchmark": _contamination_benchmark,
}


def _run_job(job: AutomationJob) -> AutomationRun:
    started_at = _utc_now()
    try:
        status, summary, details = RUNNERS[job.job_id]()
    except Exception as err:  # pragma: no cover - defensive payload for UI visibility
        status = "failed"
        summary = f"Automation job crashed: {err}"
        details = {"error": str(err)}
    finished_at = _utc_now()
    return AutomationRun(
        run_id=f"{job.job_id}:{finished_at}",
        job_id=job.job_id,
        status=status,
        summary=summary,
        started_at=started_at,
        finished_at=finished_at,
        state_writes=0,
        details=details,
    )


def run_automation_once() -> dict[str, Any]:
    runs = [_run_job(job) for job in AUTOMATION_JOBS]
    status_counts = {
        "ok": sum(1 for run in runs if run.status == "ok"),
        "warning": sum(1 for run in runs if run.status == "warning"),
        "failed": sum(1 for run in runs if run.status == "failed"),
    }
    return {
        **automation_status_payload(),
        "generated_at": _utc_now(),
        "summary": {
            "total": len(runs),
            **status_counts,
            "state_writes": sum(run.state_writes for run in runs),
        },
        "runs": [asdict(run) for run in runs],
    }
