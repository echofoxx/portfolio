from __future__ import annotations

import math
from collections import defaultdict, deque
from datetime import date
from typing import Iterable

from app.models import Task, TaskRelationship


def task_duration_days(task: Task) -> int:
    if task.task_type == "Milestone":
        return 0
    if task.start_date and task.due_date:
        return max(1, (task.due_date - task.start_date).days + 1)
    return max(1, math.ceil(float(task.estimated_effort or 0) / 8.0))


def wbs_numbers(tasks: Iterable[Task]) -> dict[str, str]:
    """Create deterministic hierarchical WBS numbers from sequence and indent level."""
    counters: list[int] = []
    result: dict[str, str] = {}
    for task in sorted(tasks, key=lambda item: (item.sequence, item.created_at)):
        level = max(0, min(8, int(task.indent_level or 0)))
        while len(counters) <= level:
            counters.append(0)
        counters = counters[: level + 1]
        counters[level] += 1
        for deeper in range(level + 1, len(counters)):
            counters[deeper] = 0
        result[task.id] = ".".join(str(value) for value in counters if value > 0)
    return result


def relationship_graph(tasks: Iterable[Task], relationships: Iterable[TaskRelationship]):
    task_ids = {task.id for task in tasks}
    successors: dict[str, set[str]] = defaultdict(set)
    predecessors: dict[str, set[str]] = defaultdict(set)
    for rel in relationships:
        if rel.relationship_type != "Finish-to-start":
            continue
        if rel.source_task_id not in task_ids or rel.target_task_id not in task_ids:
            continue
        # The source task depends on the target task, so target precedes source.
        predecessors[rel.source_task_id].add(rel.target_task_id)
        successors[rel.target_task_id].add(rel.source_task_id)
    return successors, predecessors


def would_create_cycle(tasks: Iterable[Task], relationships: Iterable[TaskRelationship], source_id: str, target_id: str) -> bool:
    if source_id == target_id:
        return True
    task_ids = {task.id for task in tasks}
    graph: dict[str, set[str]] = defaultdict(set)
    for rel in relationships:
        if rel.source_task_id in task_ids and rel.target_task_id in task_ids:
            graph[rel.source_task_id].add(rel.target_task_id)
    graph[source_id].add(target_id)
    stack = [target_id]
    visited: set[str] = set()
    while stack:
        node = stack.pop()
        if node == source_id:
            return True
        if node in visited:
            continue
        visited.add(node)
        stack.extend(graph.get(node, ()))
    return False


def critical_path(tasks: Iterable[Task], relationships: Iterable[TaskRelationship]) -> dict:
    task_list = list(tasks)
    task_map = {task.id: task for task in task_list}
    successors, predecessors = relationship_graph(task_list, relationships)
    indegree = {task.id: len(predecessors.get(task.id, set())) for task in task_list}
    queue = deque(sorted((task_id for task_id, degree in indegree.items() if degree == 0), key=lambda task_id: task_map[task_id].sequence))
    order: list[str] = []
    while queue:
        task_id = queue.popleft()
        order.append(task_id)
        for successor in successors.get(task_id, set()):
            indegree[successor] -= 1
            if indegree[successor] == 0:
                queue.append(successor)
    if len(order) != len(task_list):
        return {"has_cycle": True, "task_ids": [], "duration_days": 0, "slack": {}}

    earliest_finish: dict[str, int] = {}
    best_predecessor: dict[str, str | None] = {}
    for task_id in order:
        duration = task_duration_days(task_map[task_id])
        candidates = [(earliest_finish.get(pred, 0), pred) for pred in predecessors.get(task_id, set())]
        if candidates:
            start, predecessor = max(candidates)
        else:
            start, predecessor = 0, None
        earliest_finish[task_id] = start + duration
        best_predecessor[task_id] = predecessor

    if not order:
        return {"has_cycle": False, "task_ids": [], "duration_days": 0, "slack": {}}
    end_task = max(order, key=lambda task_id: earliest_finish[task_id])
    duration_days = earliest_finish[end_task]
    path: list[str] = []
    current: str | None = end_task
    while current:
        path.append(current)
        current = best_predecessor.get(current)
    path.reverse()

    # Basic total-float approximation using latest finish from project duration.
    latest_finish = {task_id: duration_days for task_id in order}
    for task_id in reversed(order):
        children = successors.get(task_id, set())
        if children:
            latest_finish[task_id] = min(latest_finish[child] - task_duration_days(task_map[child]) for child in children)
    slack = {task_id: max(0, latest_finish[task_id] - earliest_finish[task_id]) for task_id in order}
    return {"has_cycle": False, "task_ids": path, "duration_days": duration_days, "slack": slack}


def gantt_layout(tasks: Iterable[Task], project_start: date | None, project_end: date | None) -> dict:
    task_list = list(tasks)
    dated = [task for task in task_list if task.start_date or task.due_date]
    starts = [task.start_date or task.due_date for task in dated]
    ends = [task.due_date or task.start_date for task in dated]
    start = project_start or (min(starts) if starts else date.today())
    end = project_end or (max(ends) if ends else start)
    if end < start:
        end = start
    total = max(1, (end - start).days + 1)
    rows = []
    for task in task_list:
        task_start = task.start_date or task.due_date or start
        task_end = task.due_date or task.start_date or task_start
        if task_end < task_start:
            task_end = task_start
        left = max(0.0, min(100.0, ((task_start - start).days / total) * 100))
        width = max(1.2, min(100.0 - left, (((task_end - task_start).days + 1) / total) * 100))
        rows.append({"task": task, "left": left, "width": width, "start": task_start, "end": task_end})
    return {"start": start, "end": end, "total_days": total, "rows": rows}
