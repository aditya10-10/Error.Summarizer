"""Domain models used by the error summariser."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Attempt:
    task_id: str
    current_retry_count: str
    max_retry_count: str


@dataclass
class FailureGroup:
    agency_id: str
    task_type_id: str
    title: str
    attempts: list[Attempt] = field(default_factory=list)
    task_ids: list[str] = field(default_factory=list)
    descriptions: list[str] = field(default_factory=list)

    def add_attempt(self, attempt: Attempt, description: str) -> None:
        self.attempts.append(attempt)
        if attempt.task_id not in self.task_ids:
            self.task_ids.append(attempt.task_id)
        if description:
            self.descriptions.append(description)


@dataclass(frozen=True)
class ErrorSummary:
    reason: str
    message: str
