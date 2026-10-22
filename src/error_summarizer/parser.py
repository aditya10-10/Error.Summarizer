"""Read and group the tab-separated task export."""

from __future__ import annotations

import csv
from collections import OrderedDict
from pathlib import Path

from .models import Attempt, FailureGroup

REQUIRED_COLUMNS = {
    "tasktypeid",
    "title",
    "description",
    "currentretrycount",
    "maxretrycount",
    "agencyid",
    "taskid",
}


def clean(value: object) -> str:
    return "" if value is None else str(value).strip()


def load_groups(input_file: Path) -> list[FailureGroup]:
    if not input_file.exists():
        raise FileNotFoundError(f"File not found: {input_file}")

    with input_file.open("r", encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source, delimiter="\t")
        if not reader.fieldnames:
            raise ValueError("No data rows found.")

        headers = {header.lower(): header for header in reader.fieldnames if header}
        missing = REQUIRED_COLUMNS - headers.keys()
        if missing:
            raise ValueError(f"Required column missing: {sorted(missing)[0]}")

        groups: OrderedDict[tuple[str, str], FailureGroup] = OrderedDict()
        for row_number, row in enumerate(reader, start=2):
            agency_id = clean(row[headers["agencyid"]])
            task_type_id = clean(row[headers["tasktypeid"]])
            task_id = clean(row[headers["taskid"]])
            if not agency_id or not task_type_id or not task_id:
                print(f"Skipping invalid row {row_number}")
                continue

            key = (agency_id, task_type_id)
            group = groups.setdefault(
                key,
                FailureGroup(
                    agency_id=agency_id,
                    task_type_id=task_type_id,
                    title=clean(row[headers["title"]]),
                ),
            )
            group.add_attempt(
                Attempt(
                    task_id=task_id,
                    current_retry_count=clean(row[headers["currentretrycount"]]),
                    max_retry_count=clean(row[headers["maxretrycount"]]),
                ),
                clean(row[headers["description"]]),
            )

    return list(groups.values())
