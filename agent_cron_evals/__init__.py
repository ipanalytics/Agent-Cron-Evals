"""agent-cron-evals — deterministic checks for scheduled agent jobs.

The premise: the agent's scheduled work is the part nobody watches. A job that fails loudly is
a nuisance; a job that fails *silently* is a hole in the system, because the one thing that
would have told you about it is the job itself.

So this package asks three questions, without a model anywhere near it:

1. did each job run, recently enough, and did it say it succeeded?
2. did its output actually arrive, and has it stopped failing in a row?
3. are the helper processes that keep it alive still checking in?

Everything else is deliberately absent: no scoring, no severity, no dashboards. A finding is a
line of text a human can act on, and a healthy run prints nothing at all.
"""

from __future__ import annotations

from .checks import Check, Finding, RunResult, check_job, run
from .config import load as load_config
from .jobs import age_seconds, parse_ts
from .jobs import load as load_jobs
from .report import lines, payload, summary_line, write
from .schedule import hours_in_window, weekday_allowed

__version__ = "1.0.0"

__all__ = [
    "Check",
    "Finding",
    "RunResult",
    "__version__",
    "age_seconds",
    "check_job",
    "hours_in_window",
    "lines",
    "load_config",
    "load_jobs",
    "parse_ts",
    "payload",
    "run",
    "summary_line",
    "weekday_allowed",
    "write",
]
