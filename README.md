# Agent Cron Evals

_Русская версия: [README.ru.md](README.ru.md)_

_Deterministic checks for scheduled agent jobs: did it run, did it succeed, did the output arrive, is the watchdog still alive_

[![License: MIT](https://img.shields.io/github/license/ipanalytics/Agent-Cron-Evals)](LICENSE)
[![Python: >=3.11](https://img.shields.io/badge/python-3.11+-blue.svg)](https://python.org/downloads/)
[![Version](https://img.shields.io/github/v/release/ipanalytics/Agent-Cron-Evals)](https://github.com/ipanalytics/Agent-Cron-Evals/releases)


<div align="center">
  <img src="./site/banner.svg" alt="Agent Cron Evals Banner" width="800">
</div>

---

## Overview

I monitor scheduled agent jobs to detect failures before they become problems. My approach is deterministic: no model, no dashboard, no scoring. I check that jobs ran recently enough, reported success, delivered their output, and that watchdog processes are still alive.

A healthy run prints nothing. Problems appear as one line per issue, with full records always written to disk.

## Architecture

My checks run without a model or network connection. The architecture is simple:

1. **Job freshness**: Did the job run recently enough?
2. **Status verification**: Did it report success?
3. **Delivery confirmation**: Did the output arrive?
4. **Streak tracking**: Are there consecutive failures?
5. **Watchdog monitoring**: Are helper processes still checking in?

This design ensures reliability without external dependencies.

## Features

- **Silent when healthy**: Prints nothing when all checks pass
- **Deterministic checks**: Arithmetic on timestamps, no probabilistic evaluation
- **Configurable limits**: Set age thresholds and failure streaks
- **Delivery error detection**: Flags delivery failures separately from job status
- **State file monitoring**: Tracks external processes via timestamp files
- **Skip logic**: Respects schedule windows and weekdays
- **Self-monitor exclusion**: Prevents monitors from reporting their own failures

## Quick Start

```sh
pip install git+https://github.com/ipanalytics/Agent-Cron-Evals
cp examples/checks.example.json ~/.hermes/cron-evals.json
agent-cron-evals --config ~/.hermes/cron-evals.json
```

When all checks pass, the output is empty. When problems exist:

```
morning digest: last run 31.4 h ago, limit 27.0 h
results watcher: last_status = error (peer closed connection without sending complete message body)
watchlist autofetch: has not checked in for 4.2 h (expected every 3.5 h)
invoices: 3 failures in a row
```

## Installation

Install from PyPI or directly from GitHub:

```sh
pip install agent-cron-evals
# or from source:
pip install git+https://github.com/ipanalytics/Agent-Cron-Evals
# or using uv:
uv pip install git+https://github.com/ipanalytics/Agent-Cron-Evals
```

## Usage

### Command Line Interface

```sh
agent-cron-evals --config evals.json                 # problems only (for cron)
agent-cron-evals --config evals.json --all           # every check plus summary
agent-cron-evals --config evals.json --json          # full record as JSON
agent-cron-evals --config evals.json --quiet         # write record, print nothing
agent-cron-evals --config evals.json --jobs other.json --output /tmp/evals.json
```

### Exit Codes

- `0`: Checks ran successfully (problems reported in output)
- `2`: Config or job list could not be read

### Example Cron Pattern

I'm designed for the no-model cron pattern:

```json
{
  "id": "cron-evals",
  "schedule": "0 * * * *",
  "script": "agent-cron-evals --config ~/.hermes/cron-evals.json",
  "no_agent": true,
  "deliver": "telegram:-1000000000000:42"
}
```

The `no_agent: true` field ensures stdout is delivered verbatim. An empty stdout sends nothing at all.

## Checks Reference

| Check Name | What It Verifies | Triggers When | Result/Skip Meaning |
|------------|------------------|---------------|---------------------|
| Job existence | Job is in schedule file | Job ID not found | FAIL: "missing" |
| Job enabled | Job is enabled | `enabled: false` | SKIP: "disabled" |
| Schedule window | Inside configured hours | Outside `hours` window | SKIP: "outside its window" |
| Weekday check | Today is allowed day | Not in `days` list | SKIP: "not scheduled today" |
| Freshness | Recent run within limit | Age > `max_age_seconds` | FAIL: age exceeded |
| Status check | Success status | `last_status` ≠ `require_status` | FAIL: status mismatch |
| Delivery errors | No delivery problems | `last_delivery_error` exists | FAIL: delivery failed |
| Failure streaks | Not in streak | `failure_streak` ≥ `streak_limit` | FAIL: consecutive failures |
| State files | External processes alive | Timestamp > `max_age_seconds` | FAIL: process stale |

## Configuration

Configuration uses a JSON file with these keys:

| Key | Type | Description | Default |
|-----|------|-------------|---------|
| `jobs_file` | string | Path to job schedule file | `"~/.hermes/cron/jobs.json"` |
| `output` | string | Where to write JSON record | `"~/.hermes/data/cron_evals.json"` |
| `delivery` | boolean | Check for delivery errors | `true` |
| `streak_limit` | integer | Failures in a row to report | `3` |
| `self_monitors` | array | Job IDs to exclude from streak checks | `[]` |
| `checks` | array | Job-specific checks | `[]` |
| `state_files` | array | External state file monitors | `[]` |

Example configuration:

```json
{
  "jobs_file": "~/.hermes/cron/jobs.json",
  "output": "~/.hermes/data/cron_evals.json",
  "delivery": true,
  "streak_limit": 3,
  "self_monitors": ["8eafdf0f26f9"],
  "checks": [
    {"job": "a372f46fdbd6", "name": "oura snapshot", "max_age_seconds": 97200},
    {"job": "e70f41682aea", "name": "midday digest", "max_age_seconds": 97200, "days": [0, 1, 2, 3, 4]}
  ],
  "state_files": [
    {"name": "watchlist autofetch", "path": "~/.hermes/data/watchlist_state.json",
     "key": "last_check", "max_age_seconds": 12600}
  ]
}
```

## Outputs/Artifacts

I write a JSON record to the configured output path with these fields:

- `findings`: Array of individual check results
- `problems`: Array of problem descriptions
- `skipped`: Count of skipped checks
- `failed`: Count of failed checks
- `timestamp`: When the evaluation ran

Each finding contains:
- `job`: Job ID
- `name`: Human-readable name
- `state`: `ok`, `fail`, or `skip`
- `detail`: Additional information for skips
- `age_seconds`: Age of the job's last run
- `problems`: Array of problem strings

## Operational Notes

- **Cron integration**: Designed to run hourly with no agent attached
- **Night checks**: A job scheduled for night may show as unhealthy during day checks - this is expected behavior, not a bug
- **Broken files**: I never raise on missing or unreadable files - a broken state file becomes a finding, not a traceback
- **Silent failures**: I prioritize reporting problems over failing to run

## Project Scope

I verify scheduled job health through deterministic checks. I do not:
- Act as a scheduler
- Modify job files
- Provide a dashboard
- Evaluate job output quality
- Require network connectivity

## Use Cases

- Monitoring scheduled agents in production
- Ensuring delivery of automated reports
- Tracking cron job reliability
- Detecting silent failures
- Verifying watchdog processes

## Limitations

- Only verifies job metadata (timestamps, status), not output quality
- Requires properly formatted job files with timestamps
- Limited to Unix-style cron scheduling
- No built-in visualization beyond text output
- Does not attempt to restart failed jobs

## Repository Layout

```
agent_cron_evals/     # Main package
├── checks.py         # The core checks implementation
├── cli.py            # Command line interface
├── config.py         # Configuration loading
├── jobs.py           # Job file parsing
├── report.py         # Output formatting
└── schedule.py       # Schedule parsing utilities
examples/             # Configuration examples
tests/                # Test suite
site/                 # Assets including banner.svg
```

## Testing

```sh
python -m pytest -q     # 42 passed
python -m ruff check .  # clean
```

Tests cover scheduler-file shapes, hours and weekday arithmetic, every finding state, delivery/streak/state-file paths, and CLI exit codes. No network dependencies.

## Deployment

Deploy via pip or directly from source. I have no external dependencies beyond Python 3.11+.

## License

MIT

## Disclaimer

I report job health based on available metadata. I do not evaluate the quality of job outputs or the business impact of failures.
