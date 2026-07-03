"""Small task graph primitives for agent workflow planning."""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from typing import Iterable, Literal

from .orchestrator import MotherAgent, ScoreCard
from .profiles import RegisteredSpecialist
from .records import TaskSpec


NodeStatus = Literal["pending", "running", "completed", "failed"]


@dataclass(frozen=True)
class TaskNode:
    node_id: str
    task_id: str
    specialist_id: str
    depends_on: tuple[str, ...] = ()
    status: NodeStatus = "pending"


@dataclass(frozen=True)
class ExecutionCheckpoint:
    node_id: str
    status: NodeStatus
    accepted: int = 0
    rejected: int = 0


@dataclass(frozen=True)
class TaskGraph:
    nodes: tuple[TaskNode, ...]

    def validate(self) -> tuple[str, ...]:
        ids = [node.node_id for node in self.nodes]
        violations: list[str] = []
        if len(ids) != len(set(ids)):
            violations.append("duplicate_node_id")

        known = set(ids)
        for node in self.nodes:
            if not node.node_id.strip():
                violations.append("missing_node_id")
            if not node.task_id.strip():
                violations.append(f"missing_task_id:{node.node_id}")
            if not node.specialist_id.strip():
                violations.append(f"missing_specialist_id:{node.node_id}")
            for dep in node.depends_on:
                if dep not in known:
                    violations.append(f"missing_dependency:{node.node_id}->{dep}")

        if self._has_cycle():
            violations.append("cycle_detected")
        return tuple(violations)

    def ready_nodes(self) -> tuple[TaskNode, ...]:
        completed = {node.node_id for node in self.nodes if node.status == "completed"}
        return tuple(
            node
            for node in self.nodes
            if node.status == "pending" and all(dep in completed for dep in node.depends_on)
        )

    def _has_cycle(self) -> bool:
        deps = {node.node_id: set(node.depends_on) for node in self.nodes}
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(node_id: str) -> bool:
            if node_id in visiting:
                return True
            if node_id in visited:
                return False
            visiting.add(node_id)
            for dep in deps.get(node_id, set()):
                if visit(dep):
                    return True
            visiting.remove(node_id)
            visited.add(node_id)
            return False

        return any(visit(node_id) for node_id in deps)


class GraphExecutor:
    """Automated topological runner for TaskGraph workflows.

    Enforces security checkpoints and fail-fast constraints: if any node
    specialist yields a rejected proposal or raises an error, execution stops immediately.
    """

    def __init__(self, mother: MotherAgent, specialists: Iterable[RegisteredSpecialist]) -> None:
        self.mother = mother
        self.specialists = {s.profile.specialist_id: s for s in specialists}

    def execute(
        self,
        graph: TaskGraph,
        task_map: dict[str, TaskSpec],
    ) -> tuple[TaskGraph, tuple[ExecutionCheckpoint, ...], ScoreCard, bool]:
        """Runs the task graph topologically.

        Returns:
            (updated_graph, checkpoints, cumulative_scorecard, success)
        """
        current_nodes = {node.node_id: node for node in graph.nodes}
        checkpoints: list[ExecutionCheckpoint] = []

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

            has_failed_in_round = False
            for node in sorted(ready, key=lambda n: n.node_id):
                current_nodes[node.node_id] = dataclasses.replace(node, status="running")

                task = task_map.get(node.task_id)
                specialist = self.specialists.get(node.specialist_id)

                if not task:
                    current_nodes[node.node_id] = dataclasses.replace(node, status="failed")
                    checkpoints.append(
                        ExecutionCheckpoint(node_id=node.node_id, status="failed", accepted=0, rejected=0)
                    )
                    has_failed_in_round = True
                    success = False
                    break

                if not specialist:
                    current_nodes[node.node_id] = dataclasses.replace(node, status="failed")
                    checkpoints.append(
                        ExecutionCheckpoint(node_id=node.node_id, status="failed", accepted=0, rejected=0)
                    )
                    has_failed_in_round = True
                    success = False
                    break

                try:
                    checked_records, score = self.mother.dispatch_registered(task, [specialist])

                    total += score.total
                    accepted += score.accepted
                    rejected += score.rejected
                    for v_code, count in score.violation_counts.items():
                        violation_counts[v_code] = violation_counts.get(v_code, 0) + count
                    destroyed_child_ids.extend(score.destroyed_child_ids)
                    child_sessions.extend(score.child_sessions)

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
                        has_failed_in_round = True
                        success = False
                        break
                    else:
                        current_nodes[node.node_id] = dataclasses.replace(node, status="completed")
                        checkpoints.append(
                            ExecutionCheckpoint(
                                node_id=node.node_id,
                                status="completed",
                                accepted=score.accepted,
                                rejected=0,
                            )
                        )
                except Exception:
                    current_nodes[node.node_id] = dataclasses.replace(node, status="failed")
                    checkpoints.append(
                        ExecutionCheckpoint(node_id=node.node_id, status="failed", accepted=0, rejected=0)
                    )
                    has_failed_in_round = True
                    success = False
                    break

            if has_failed_in_round or not success:
                break

        final_nodes = tuple(current_nodes.values())
        all_completed = all(node.status == "completed" for node in final_nodes)
        if not all_completed:
            success = False

        cumulative_score = ScoreCard(
            total=total,
            accepted=accepted,
            rejected=rejected,
            violation_counts=violation_counts,
            destroyed_child_ids=tuple(sorted(set(destroyed_child_ids))),
            child_sessions=tuple(child_sessions),
        )

        return TaskGraph(nodes=final_nodes), tuple(checkpoints), cumulative_score, success

