"""The checks themselves: freshness, status, delivery errors, streaks, stale state files.

Every finding is either silence (fine) or one line a human can act on. There is no scoring, no
severity ladder and no model: a scheduled job is healthy or it is not.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import jobs as jobs_mod
from .schedule import hours_in_window, weekday_allowed

OK, FAIL, SKIP = "ok", "fail", "skip"


@dataclass
class Check:
    """One expectation about one job."""

    job: str
    name: str = ""
    max_age_seconds: int = 27 * 3600
    days: list = field(default_factory=list)
    require_status: str = "ok"


@dataclass
class Finding:
    job: str
    name: str
    state: str
    detail: str = ""
    age_seconds: float | None = None
    problems: list = field(default_factory=list)


def check_job(check: Check, job: dict | None, now: float, hour: int, weekday: int) -> Finding:
    """Judge one job. ``hour`` and ``weekday`` are passed in so a test can pick the moment."""
    name = check.name or (job or {}).get("name") or check.job
    if job is None:
        return Finding(
            check.job,
            name,
            FAIL,
            "missing",
            problems=[f"{name}: job {check.job} is not in the schedule file any more"],
        )
    if not job.get("enabled", True):
        return Finding(check.job, name, SKIP, "disabled")
    if not weekday_allowed(check.days, weekday):
        return Finding(check.job, name, SKIP, "not scheduled today")
    expr = (job.get("schedule") or {}).get("expr") or ""
    if expr and not hours_in_window(expr, hour):
        return Finding(check.job, name, SKIP, "outside its window")

    age = jobs_mod.age_seconds(job, now)
    status = job.get("last_status")
    problems: list[str] = []
    if age is None:
        problems.append(f"{name}: has never run — no run timestamp in the job file")
    elif age > check.max_age_seconds:
        problems.append(
            f"{name}: last run {age / 3600:.1f} h ago, limit {check.max_age_seconds / 3600:.1f} h"
        )
    if status and status != check.require_status:
        detail = job.get("last_error") or job.get("last_fire_error") or "no error text"
        problems.append(f"{name}: last_status = {status} ({detail})")
    return Finding(check.job, name, OK if not problems else FAIL, "", age, problems)


@dataclass
class RunResult:
    findings: list = field(default_factory=list)
    problems: list = field(default_factory=list)
    skipped: int = 0

    @property
    def failed(self) -> int:
        return sum(1 for f in self.findings if f.state == FAIL)


def _state_file_age(entry: dict, now: float) -> tuple[str, float | None, str]:
    """(name, age_hours, note) for a JSON file whose values carry a 'last seen' stamp."""
    import json

    name = entry.get("name") or entry.get("path", "state")
    path = entry.get("path")
    key = entry.get("key", "last_check")
    if not path:
        return name, None, "no path configured"
    try:
        with open(path, encoding="utf-8") as handle:
            payload = json.loads(handle.read())
    except FileNotFoundError:
        return name, None, "file not found"
    except (ValueError, OSError) as exc:
        return name, None, f"unreadable ({type(exc).__name__})"
    stamps = []
    for item in payload.values() if isinstance(payload, dict) else payload:
        if not isinstance(item, dict):
            continue
        value = item.get(key)
        if isinstance(value, (int, float)):
            stamps.append(float(value))
    if not stamps:
        return name, None, "no timestamps inside"
    return name, (now - max(stamps)) / 3600, ""


def run(config: dict, jobs_map: dict, now: float, hour: int, weekday: int) -> RunResult:
    """Run every configured check plus the three global ones. Never raises on missing files."""
    result = RunResult()
    for raw in config.get("checks") or []:
        check = Check(
            job=str(raw.get("job")),
            name=raw.get("name", ""),
            max_age_seconds=int(raw.get("max_age_seconds", 27 * 3600)),
            days=raw.get("days") or [],
            require_status=raw.get("require_status", "ok"),
        )
        finding = check_job(check, jobs_map.get(check.job), now, hour, weekday)
        result.findings.append(finding)
        result.problems.extend(finding.problems)
        if finding.state == SKIP:
            result.skipped += 1

    if config.get("delivery", True):
        for job in jobs_map.values():
            if not job.get("enabled", True):
                continue
            error = job.get("last_delivery_error")
            if error:
                result.problems.append(
                    f"{job.get('name') or job.get('id')}: delivery failed — {error}"
                )

    streak_limit = int(config.get("streak_limit", 3))
    self_monitors = {str(job_id) for job_id in (config.get("self_monitors") or [])}
    for job_id, job in jobs_map.items():
        streak = job.get("failure_streak") or 0
        if streak >= streak_limit and job_id not in self_monitors:
            result.problems.append(f"{job.get('name') or job_id}: {streak} failures in a row")

    for entry in config.get("state_files") or []:
        name, age_hours, note = _state_file_age(entry, now)
        limit = float(entry.get("max_age_seconds", 3.5 * 3600)) / 3600
        if note:
            result.problems.append(f"{name}: {note}")
            continue
        if age_hours is not None and age_hours > limit:
            result.problems.append(
                f"{name}: has not checked in for {age_hours:.1f} h (expected every {limit:.1f} h)"
            )
    return result
