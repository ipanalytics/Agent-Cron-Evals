"""Read the scheduler's job list without trusting its shape.

A bare list, a mapping with a ``jobs`` key, ISO timestamps with or without a zone, epoch
seconds, junk entries: all of it has been seen in the wild, and none of it may crash an eval.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def load(path) -> dict[str, dict]:
    """Return ``{job_id: job}``. Unusable entries are skipped, not raised."""
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(raw, dict):
        raw = raw.get("jobs") or []
    if not isinstance(raw, list):
        return {}
    out: dict[str, dict] = {}
    for item in raw:
        if not isinstance(item, dict):
            continue
        job_id = item.get("id") or item.get("job_id")
        if job_id:
            out[str(job_id)] = item
    return out


def parse_ts(value: Any) -> float | None:
    """ISO with ``Z``, ISO with an offset, epoch seconds — anything else is ``None``."""
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace("Z", "+00:00")
    try:
        stamp = datetime.fromisoformat(text)
    except ValueError:
        return None
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=UTC)
    return stamp.timestamp()


def age_seconds(job: dict, now: float) -> float | None:
    """Seconds since the job last ran, or ``None`` when no timestamp is usable."""
    for key in ("last_run_at", "last_finished_at", "last_fire_at"):
        stamp = parse_ts(job.get(key))
        if stamp is not None:
            return now - stamp
    return None
