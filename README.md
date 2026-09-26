# Agent Cron Evals

_Русская версия: [README.ru.md](README.ru.md)_

**Say which scheduled jobs are dead — and stay silent when none are.**

An agent's scheduled work is the part nobody watches. A job that fails loudly is a nuisance; a
job that fails *silently* is a hole in the system, because the one thing that would have told
you about it was the job itself.

This package is the replacement for "did my crons run?" — deterministic checks, no model, no
dashboard, no scoring. It answers four questions:

1. **Did each job run, recently enough, and did it say it succeeded?**
2. **Did its output actually arrive?** A delivery error is a failure even when the job "succeeded".
3. **Has any job stopped in the middle of a failure streak?** Three in a row is not a blip.
4. **Are the helper processes still checking in?** A watchdog writes a timestamp; a stale
   timestamp means the watchdog died quietly.

A healthy run prints **nothing**. That is the whole interface: silence means fine, one line per
problem, and the full record always written to disk.

---

## Quick start

```sh
pip install git+https://github.com/ipanalytics/Agent-Cron-Evals   # or: uv pip install -e .
cp examples/checks.example.json ~/.hermes/cron-evals.json         # then edit the job ids
agent-cron-evals --config ~/.hermes/cron-evals.json
```

The run above prints nothing when everything is healthy, and something like this when it is not:

```
morning digest: last run 31.4 h ago, limit 27.0 h
results watcher: last_status = error (peer closed connection without sending complete message body)
watchlist autofetch: has not checked in for 4.2 h (expected every 3.5 h)
invoices: 3 failures in a row
```

## The no-model cron pattern

This tool is built to run from a cron entry with **no agent and no model** attached: the text
goes straight into a message, so a healthy run must produce no message at all. In a Hermes-style
scheduler that is one job with a script and no prompt:

```json
{
  "id": "cron-evals",
  "schedule": "0 * * * *",
  "script": "agent-cron-evals --config ~/.hermes/cron-evals.json",
  "no_agent": true,
  "deliver": "telegram:-1000000000000:42"
}
```

`no_agent: true` is the important field: stdout is delivered verbatim and an empty stdout sends
nothing at all.

Two properties make this safe to run every hour: it never writes to the job file, and it never
raises on a missing or unreadable file — a broken state file is a finding, not a traceback.

## The config file

One JSON object. Everything except `checks` is optional; defaults are shown in the example.

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

| Field | Meaning |
| --- | --- |
| `checks[].job` | The job id as it appears in the schedule file. Required. |
| `checks[].name` | Human name for the message. Falls back to the job's own name. |
| `checks[].max_age_seconds` | How long a gap is still healthy. Default 27 h (a daily job plus slack). |
| `checks[].days` | Only check on these weekdays — Python numbering, Monday=0 … Sunday=6 (a `7` is read as Sunday). Names work too: `["mon","tue"]`. Empty means every day. |
| `checks[].require_status` | The status string that counts as success. Default `ok`. |
| `self_monitors` | Job ids whose own failure streak must be ignored — a monitor that reports "3 failures in a row" about itself never resets. |
| `state_files[].key` | The timestamp field inside the file. Default `last_check`. |
| `streak_limit` | Failures in a row that become a problem. Default 3. |

### Two mistakes the loader refuses

- a config that is not a JSON object;
- any check without a `job` id.

Both exit `2` with a message on stderr, because a config that silently checks nothing is worse
than a config that fails loudly.

## What runs, and when

| Question | Checked every run |
| --- | --- |
| Job exists, is enabled, is inside its own hours window | yes — otherwise the finding is `skip`, not `fail` |
| Last run is recent and `last_status` is `ok` | yes, per configured check |
| `last_delivery_error` on any enabled job | yes, for the whole job list |
| `failure_streak >= streak_limit` | yes, minus `self_monitors` |
| State files still ticking | yes, per configured entry |

The `skip` state carries the reason (`disabled`, `not scheduled today`, `outside its window`).
Skips are never delivered; they only appear in the JSON record and under `--all`.

## Command line

```sh
agent-cron-evals --config evals.json                 # problems only (this is what a cron runs)
agent-cron-evals --config evals.json --all           # every check plus a summary line
agent-cron-evals --config evals.json --json          # the whole record
agent-cron-evals --config evals.json --quiet         # write the record, print nothing
agent-cron-evals --config evals.json --jobs other.json --output /tmp/evals.json
```

Exit codes: `0` the eval ran (problems are the *output*, not the status), `2` the config or the
job list could not be read. That is deliberate — a monitoring job whose own exit code flips on
findings tends to get marked failed by the scheduler and then ignored.

## What this is not

- **Not a scheduler.** It never writes to the job file, never re-arms a job, never fixes anything.
- **Not a model.** No LLM anywhere: the checks are arithmetic on timestamps.
- **Not a dashboard.** The JSON record is there to be queried; the message is the interface.
- **Not coverage of your job's meaning.** It knows the job ran and delivered; whether the digest
  was *any good* is a different problem (see the "task evals" idea in the linked series).

## Tests

```sh
python -m pytest -q     # 42 passed
python -m ruff check .  # clean
```

Tests cover the scheduler-file shapes that exist in the wild (bare list, `{"jobs": [...]}`,
naive and zoned timestamps, epoch seconds, junk entries), the hours and weekday arithmetic, every
finding state, the delivery/streak/state-file paths, and the CLI's exit codes. No network, no
fixtures outside `tmp_path`.

## Related

- [Hermes-Agent-Ops](https://github.com/ipanalytics/Hermes-Agent-Ops) — the practice notes these
  checks come from: module 05 (a cron for the crons), 07 (prompt linting), 20 (task evals),
  28 (delivery health), 30 (schedule audit).
- [Awesome Agent Ops](https://github.com/ipanalytics/Awesome-Agent-Ops) — the wider list.

## License

MIT.
