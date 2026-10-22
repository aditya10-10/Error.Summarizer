"""Render and write the report."""

from __future__ import annotations

from pathlib import Path

from .models import ErrorSummary, FailureGroup
from .parser import clean

SEPARATOR = "-" * 87


def calculate_status(group: FailureGroup) -> tuple[int, int]:
    permanently_failed: set[str] = set()
    for attempt in group.attempts:
        if clean(attempt.current_retry_count).upper() in {"", "NULL"} or clean(attempt.max_retry_count).upper() in {"", "NULL"}:
            continue
        try:
            if float(attempt.current_retry_count) >= float(attempt.max_retry_count):
                permanently_failed.add(attempt.task_id)
        except ValueError:
            continue
    return len(group.attempts), len(permanently_failed)


def render_group(group: FailureGroup, summary: ErrorSummary) -> str:
    total, final_failures = calculate_status(group)
    lines = [
        f"AgencyId: {group.agency_id}",
        f"TaskTypeId: {group.task_type_id} ({group.title})",
        f"Reason: **{summary.reason}**",
    ]
    if summary.message:
        lines.append(f"Simplified error: {summary.message}")
    lines.extend([f"TaskIds: {', '.join(group.task_ids)}", f"Status: {total}({final_failures})"])
    return "\r\n".join(lines)


def write_report(output_file: Path, blocks: list[str]) -> None:
    output_file.write_text(f"\r\n{SEPARATOR}\r\n".join(blocks) + "\r\n", encoding="utf-8")
