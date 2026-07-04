"""Curated memory for the mother agent.

Memory is **untrusted context** — it helps the mother agent understand the
user better, but it can NEVER:

    1. Enter ``TaskSpec.objective`` (the child agent's instruction)
    2. Bypass or soften any constraint rule
    3. Be treated as verified fact

Memory flows through the same Intent Firewall as raw user text.  The only
difference is that memory enters ``mother_notes`` as ``memory_hint`` entries,
not into the sanitized objective.

Memory categories:
    - ``user_preference``: "I mainly work on frontend" — helps routing
    - ``common_scope``: "usually works in app/static/" — helps scope defaults
    - ``task_pattern``: "asks for layout reviews often" — helps intent detection
    - ``feedback``: "rejected the last 3 bypass attempts" — helps expectations

Memory has a confidence score (0.0–1.0) that decays over time.  Memories
that are never reinforced eventually drop below threshold and are pruned.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


MEMORY_PROVENANCE = "mother_memory_v1"
MEMORY_MIN_CONFIDENCE = 0.15  # below this, memory is pruned
MEMORY_DECAY_PER_DAY = 0.05  # confidence drops 5% per day without reinforcement
MEMORY_REINFORCEMENT_BOOST = 0.15  # each reinforcement adds 15% confidence
MEMORY_MAX_CONFIDENCE = 1.0
MEMORY_MAX_ENTRIES = 50


@dataclass(frozen=True)
class MemoryEntry:
    """A single curated memory unit.

    Attributes:
        id: Unique identifier.
        category: One of user_preference, common_scope, task_pattern, feedback.
        content: The memory text (already sanitized — no raw user text).
        confidence: 0.0–1.0, decays over time, boosted by reinforcement.
        created_at: Unix timestamp.
        last_reinforced: Unix timestamp of last reinforcement.
        source_task_id: The task that created this memory (for audit).
    """
    id: str
    category: str
    content: str
    confidence: float
    created_at: float
    last_reinforced: float
    source_task_id: str = ""


class MemoryStore:
    """Persistent curated memory for the mother agent.

    Memory is stored as JSON in the workspace (``memory.json``) so it
    survives across server restarts.  All memory is treated as untrusted
    context — it helps the mother agent understand intent, but never
    enters the child agent's TaskSpec.objective or affects constraint
    decisions.
    """

    def __init__(self, storage_path: str | Path = "memory.json") -> None:
        self._path = Path(storage_path)
        self._entries: list[MemoryEntry] = []
        self._load()

    # ── Persistence ───────────────────────────────────────────────

    def _load(self) -> None:
        if not self._path.exists():
            self._entries = []
            return
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            self._entries = [MemoryEntry(**item) for item in data.get("entries", [])]
        except Exception:
            self._entries = []

    def _save(self) -> None:
        try:
            self._path.write_text(
                json.dumps(
                    {"entries": [asdict(e) for e in self._entries]},
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
        except Exception:
            pass

    # ── Core operations ───────────────────────────────────────────

    def remember(
        self,
        category: str,
        content: str,
        source_task_id: str = "",
        confidence: float = 0.5,
    ) -> MemoryEntry:
        """Store a new memory or reinforce an existing similar one.

        If a memory with the same category+content already exists, its
        confidence is boosted instead of creating a duplicate.
        """
        # Check for existing similar memory
        for entry in self._entries:
            if entry.category == category and entry.content == content:
                new_confidence = min(
                    MEMORY_MAX_CONFIDENCE,
                    entry.confidence + MEMORY_REINFORCEMENT_BOOST,
                )
                reinforced = MemoryEntry(
                    id=entry.id,
                    category=entry.category,
                    content=entry.content,
                    confidence=new_confidence,
                    created_at=entry.created_at,
                    last_reinforced=time.time(),
                    source_task_id=source_task_id or entry.source_task_id,
                )
                self._entries = [reinforced if e.id == entry.id else e for e in self._entries]
                self._save()
                return reinforced

        # Create new memory
        entry = MemoryEntry(
            id=f"mem-{int(time.time() * 1000)}-{len(self._entries)}",
            category=category,
            content=content,
            confidence=min(MEMORY_MAX_CONFIDENCE, max(0.1, confidence)),
            created_at=time.time(),
            last_reinforced=time.time(),
            source_task_id=source_task_id,
        )
        self._entries.append(entry)
        self._prune()
        self._save()
        return entry

    def forget(self, memory_id: str) -> bool:
        """Remove a memory by ID."""
        before = len(self._entries)
        self._entries = [e for e in self._entries if e.id != memory_id]
        if len(self._entries) < before:
            self._save()
            return True
        return False

    def recall(self, category: str | None = None) -> list[MemoryEntry]:
        """Retrieve memories, optionally filtered by category.

        Applies time-based decay before returning — memories that haven't
        been reinforced recently have reduced confidence.
        """
        self._apply_decay()
        if category:
            return [e for e in self._entries if e.category == category]
        return list(self._entries)

    def recall_for_intent(self, intent_codes: tuple[str, ...] = (), goal_markers: tuple[str, ...] = ()) -> list[MemoryEntry]:
        """Retrieve memories relevant to the current task's intent.

        This is the primary method the mother agent uses to fetch context.
        Returns memories sorted by confidence (highest first).
        """
        self._apply_decay()
        relevant: list[MemoryEntry] = []

        for entry in self._entries:
            if entry.confidence < MEMORY_MIN_CONFIDENCE:
                continue
            # All memories are potentially relevant, but prioritize matches
            relevant.append(entry)

        # Sort by confidence descending
        relevant.sort(key=lambda e: e.confidence, reverse=True)
        return relevant[:10]  # top 10 most relevant

    def to_hints(self) -> list[dict[str, Any]]:
        """Export memories as hint dicts for the frontend."""
        self._apply_decay()
        return [
            {
                "id": e.id,
                "category": e.category,
                "content": e.content,
                "confidence": round(e.confidence, 2),
                "last_reinforced": e.last_reinforced,
            }
            for e in self._entries
            if e.confidence >= MEMORY_MIN_CONFIDENCE
        ]

    # ── Internal maintenance ──────────────────────────────────────

    def _apply_decay(self) -> None:
        """Apply time-based confidence decay to all memories."""
        now = time.time()
        changed = False
        updated: list[MemoryEntry] = []
        for entry in self._entries:
            days_since = (now - entry.last_reinforced) / 86400
            if days_since < 1:
                updated.append(entry)
                continue
            decayed_confidence = entry.confidence - (days_since * MEMORY_DECAY_PER_DAY)
            if decayed_confidence < MEMORY_MIN_CONFIDENCE:
                changed = True
                continue  # prune — don't add to updated
            if decayed_confidence != entry.confidence:
                changed = True
                updated.append(MemoryEntry(
                    id=entry.id,
                    category=entry.category,
                    content=entry.content,
                    confidence=decayed_confidence,
                    created_at=entry.created_at,
                    last_reinforced=entry.last_reinforced,
                    source_task_id=entry.source_task_id,
                ))
            else:
                updated.append(entry)
        if changed:
            self._entries = updated
            self._save()

    def _prune(self) -> None:
        """Keep only the top N memories by confidence."""
        if len(self._entries) <= MEMORY_MAX_ENTRIES:
            return
        self._entries.sort(key=lambda e: e.confidence, reverse=True)
        self._entries = self._entries[:MEMORY_MAX_ENTRIES]


# ── Memory extraction ─────────────────────────────────────────────────


def extract_memories_from_task(
    raw_text: str,
    intent_codes: tuple[str, ...],
    goal_markers: tuple[str, ...],
    allowed_scopes: tuple[str, ...],
    task_id: str = "",
) -> list[tuple[str, str, float]]:
    """Extract memory candidates from a completed task.

    Returns a list of ``(category, content, confidence)`` tuples.
    The caller decides whether to store them via ``MemoryStore.remember()``.

    IMPORTANT: This function only extracts *objective observations* from
    the sanitized task metadata — never from raw user text.  User claims
    and contamination markers are deliberately excluded.
    """
    candidates: list[tuple[str, str, float]] = []

    # Extract common scopes — "this user often works in X"
    for scope in allowed_scopes:
        if scope and not scope.startswith("*"):
            candidates.append(("common_scope", f"frequently works in: {scope}", 0.4))

    # Extract intent patterns — "this user often asks for X"
    for code in intent_codes:
        if code and code != "general_request":
            candidates.append(("task_pattern", f"often requests: {code}", 0.3))

    # Extract goal markers — "this user cares about X"
    for marker in goal_markers:
        candidates.append(("task_pattern", f"works on: {marker}", 0.35))

    return candidates


def extract_memories_from_result(
    checked_record: dict[str, Any] | None,
    violations: list[str] | None,
    task_id: str = "",
) -> list[tuple[str, str, float]]:
    """Extract memory candidates from a task's constraint verdict.

    Records feedback like "user's requests were blocked for X reason"
    without storing any user text or proposal content.
    """
    candidates: list[tuple[str, str, float]] = []

    if not checked_record:
        return candidates

    accepted = checked_record.get("accepted", False)
    violation_list = violations or checked_record.get("violations", [])

    if not accepted and violation_list:
        # Extract violation categories (not the full violation strings)
        categories: set[str] = set()
        for v in violation_list:
            if ":" in v:
                categories.add(v.split(":")[0])
            else:
                categories.add(v)
        for cat in sorted(categories):
            candidates.append(("feedback", f"recent task blocked by: {cat}", 0.5))

    return candidates
