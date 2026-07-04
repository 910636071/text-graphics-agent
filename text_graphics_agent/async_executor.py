"""Concurrent task-graph executor with fail-fast safety.

The :class:`AsyncGraphExecutor` runs independent task nodes in parallel
using :mod:`concurrent.futures`, while preserving the fail-fast safety
contract: if any node's proposal is rejected or raises an error, all
remaining pending nodes are cancelled immediately.

This mirrors the synchronous :class:`GraphExecutor` API so you can drop
it in as a replacement when throughput matters::

    executor = AsyncGraphExecutor(mother=mother_agent, specialists=[...])
    updated_graph, checkpoints, score, success = executor.execute(graph, task_map)

Key differences from :class:`GraphExecutor`:

    - Nodes with no dependencies on each other run concurrently.
    - Thread pool size is configurable (default: 4).
    - Fail-fast is preserved — first rejection/error cancels the round.
    - Returns the same tuple shape for drop-in compatibility.
"""

from __future__ import annotations

import dataclasses
from concurrent.futures import ThreadPoolExecutor, Future, as_completed, CancelledError
from dataclasses import dataclass
from typing import Iterable

from .graph import ExecutionCheckpoint, TaskGraph, TaskNode, NodeStatus
from .orchestrator import MotherAgent, ScoreCard
from .profiles import RegisteredSpecialist
from .records import TaskSpec


@dataclass(frozen=True)
class _RoundResult:
    """Internal result from one execution round."""
    checkpoints: tuple[ExecutionCheckpoint, ...]
    failed: bool


class AsyncGraphExecutor:
    """Concurrent topological runner for TaskGraph workflows.

    Like :class:`GraphExecutor` but runs independent nodes in parallel
    using a thread pool.  Fail-fast is preserved: the first failure in
    a round cancels all remaining futures and stops execution.
    """

    def __init__(
        self,
        mother: MotherAgent,
        specialists: Iterable[RegisteredSpecialist],
        max_workers: int = 4,
    ) -> None:
        self.mother = mother
        self.specialists = {s.profile.specialist_id: s for s in specialists}
        self.max_workers = max(1, max_workers)

    def execute(
        self,
        graph: TaskGraph,
        task_map: dict[str, TaskSpec],
    ) -> tuple[TaskGraph, tuple[ExecutionCheckpoint, ...], ScoreCard, bool]:
        """Run the task graph concurrently with fail-fast semantics.

        Returns:
            (updated_graph, checkpoints, cumulative_scorecard, success)
        """
        current_nodes = {node.node_id: node for node in graph.nodes}
        all_checkpoints: list[ExecutionCheckpoint] = []

        total = 0
        accepted = 0
        rejected = 0
        violation_counts: dict[str, int] = {}
        destroyed_child_ids: list[str] = []
        child_sessions = []
        success = True

        while True:
            temp_graph = TaskGraph(nodes=tuple(current_nodes.values()))
            violations = temp_graph.validate()
            if violations:
                success = False
                break

            ready = temp_graph.ready_nodes()
            if not ready:
                break

            # ── Run all ready nodes concurrently ───────────────────
            round_result, round_score = self._execute_round(
                ready_nodes=ready,
                current_nodes=current_nodes,
                task_map=task_map,
            )

            all_checkpoints.extend(round_result.checkpoints)

            # Accumulate scores
            total += round_score.total
            accepted += round_score.accepted
            rejected += round_score.rejected
            for v_code, count in round_score.violation_counts.items():
                violation_counts[v_code] = violation_counts.get(v_code, 0) + count
            destroyed_child_ids.extend(round_score.destroyed_child_ids)
            child_sessions.extend(round_score.child_sessions)

            if round_result.failed:
                success = False
                break

        score = ScoreCard(
            total=total,
            accepted=accepted,
            rejected=rejected,
            violation_counts=violation_counts,
            destroyed_child_ids=tuple(destroyed_child_ids),
            child_sessions=tuple(child_sessions),
        )

        return (
            TaskGraph(nodes=tuple(current_nodes.values())),
            tuple(all_checkpoints),
            score,
            success,
        )

    def _execute_round(
        self,
        ready_nodes: tuple[TaskNode, ...],
        current_nodes: dict[str, TaskNode],
        task_map: dict[str, TaskSpec],
    ) -> tuple[_RoundResult, ScoreCard]:
        """Execute one round of ready nodes concurrently.

        If any node fails, cancel remaining futures and return early.
        """
        checkpoints: list[ExecutionCheckpoint] = []
        failed = False

        round_total = 0
        round_accepted = 0
        round_rejected = 0
        round_violation_counts: dict[str, int] = {}
        round_destroyed: list[str] = []
        round_sessions = []

        # Mark all as running
        for node in ready_nodes:
            current_nodes[node.node_id] = dataclasses.replace(node, status="running")

        # Submit all ready nodes to the pool
        futures: dict[Future, TaskNode] = {}

        with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            for node in ready_nodes:
                task = task_map.get(node.task_id)
                specialist = self.specialists.get(node.specialist_id)

                if not task or not specialist:
                    current_nodes[node.node_id] = dataclasses.replace(node, status="failed")
                    checkpoints.append(
                        ExecutionCheckpoint(
                            node_id=node.node_id,
                            status="failed",
                            accepted=0,
                            rejected=0,
                        )
                    )
                    failed = True
                    continue

                future = pool.submit(self._run_node, task, specialist)
                futures[future] = node

            # Wait for completion, fail-fast on first failure
            for future in as_completed(futures):
                node = futures[future]

                # If already failed, cancel remaining
                if failed:
                    for f in futures:
                        if not f.done():
                            f.cancel()
                    continue

                try:
                    checked_records, score = future.result()
                except CancelledError:
                    current_nodes[node.node_id] = dataclasses.replace(node, status="failed")
                    checkpoints.append(
                        ExecutionCheckpoint(node_id=node.node_id, status="failed")
                    )
                    failed = True
                    continue
                except Exception:
                    # Node raised an exception — treat as failure
                    current_nodes[node.node_id] = dataclasses.replace(node, status="failed")
                    checkpoints.append(
                        ExecutionCheckpoint(
                            node_id=node.node_id,
                            status="failed",
                            accepted=0,
                            rejected=1,
                        )
                    )
                    round_total += 1
                    round_rejected += 1
                    failed = True
                    continue

                round_total += score.total
                round_accepted += score.accepted
                round_rejected += score.rejected
                for v_code, count in score.violation_counts.items():
                    round_violation_counts[v_code] = round_violation_counts.get(v_code, 0) + count
                round_destroyed.extend(score.destroyed_child_ids)
                round_sessions.extend(score.child_sessions)

                if score.rejected > 0 or score.total == 0:
                    current_nodes[node.node_id] = dataclasses.replace(node, status="failed")
                    checkpoints.append(
                        ExecutionCheckpoint(
                            node_id=node.node_id,
                            status="failed",
                            accepted=score.accepted,
                            rejected=score.rejected,
                        )
                    )
                    failed = True
                else:
                    current_nodes[node.node_id] = dataclasses.replace(node, status="completed")
                    checkpoints.append(
                        ExecutionCheckpoint(
                            node_id=node.node_id,
                            status="completed",
                            accepted=score.accepted,
                            rejected=score.rejected,
                        )
                    )

        round_score = ScoreCard(
            total=round_total,
            accepted=round_accepted,
            rejected=round_rejected,
            violation_counts=round_violation_counts,
            destroyed_child_ids=tuple(round_destroyed),
            child_sessions=tuple(round_sessions),
        )

        return _RoundResult(checkpoints=tuple(checkpoints), failed=failed), round_score

    def _run_node(
        self,
        task: TaskSpec,
        specialist: RegisteredSpecialist,
    ) -> tuple[tuple, ScoreCard]:
        """Execute a single node — runs in a worker thread."""
        return self.mother.dispatch_registered(task, [specialist])
