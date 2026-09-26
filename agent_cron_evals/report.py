"""Turn findings into the two things a caller needs: a JSON record and the lines to send.

The JSON record is the history (what was checked, when, and what was wrong). The lines are the
message: only problems, one per line, because this runs from a cron with no model attached.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from .checks import FAIL, SKIP, RunResult


def payload(result: RunResult, now: float) -> dict:
    return {
        "checked_at": int(now),
        "checked_at_iso": datetime.fromtimestamp(now, UTC).isoformat(timespec="seconds"),
        "problems": list(result.problems),
        "jobs": [
            {
                "job": finding.job,
                "name": finding.name,
                "state": finding.state,
                "detail": finding.detail,
                "age_minutes": None
                if finding.age_seconds is None
                else round(finding.age_seconds / 60),
            }
            for finding in result.findings
        ],
        "summary": {
            "checks": len(result.findings),
            "failed": result.failed,
            "skipped": result.skipped,
            "problems": len(result.problems),
        },
    }


def write(config: dict, result: RunResult, now: float, output=None) -> Path:
    """Atomic write: a reader never sees half a report."""
    from .config import expand

    target = Path(expand(output or config.get("output") or "~/.hermes/data/cron_evals.json"))
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(target.suffix + ".tmp")
    tmp.write_text(json.dumps(payload(result, now), ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(target)
    return target


def lines(result: RunResult) -> list[str]:
    """Problems only — silence means everything ran. One line each, ready to deliver."""
    return list(result.problems)


def summary_line(result: RunResult) -> str:
    healthy = sum(1 for f in result.findings if f.state not in (FAIL, SKIP))
    return (
        f"cron evals: {len(result.findings)} checks, {healthy} healthy, "
        f"{result.failed} failed, {result.skipped} skipped, {len(result.problems)} problems"
    )
