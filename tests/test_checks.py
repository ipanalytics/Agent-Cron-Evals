from __future__ import annotations

import json

from agent_cron_evals import checks
from agent_cron_evals.checks import Check, check_job, run

NOW = 1_800_000_000.0
HOUR = 12
WEEKDAY = 2  # Wednesday


def _job(**over):
    job = {
        "id": "a",
        "name": "morning digest",
        "enabled": True,
        "last_run_at": "2027-01-15T00:00:00Z",  # 12 h before NOW
        "last_status": "ok",
        "schedule": {"expr": "0 3 * * *"},
    }
    job.update(over)
    return job


def test_a_fresh_successful_run_is_silent():
    finding = check_job(Check("a"), _job(schedule={}), NOW, HOUR, WEEKDAY)
    assert finding.state == checks.OK and finding.problems == []


def test_a_job_that_vanished_from_the_file_is_a_problem():
    finding = check_job(Check("gone", name="old job"), None, NOW, HOUR, WEEKDAY)
    assert finding.state == checks.FAIL
    assert "not in the schedule file" in finding.problems[0]


def test_a_disabled_job_is_reported_as_skipped_not_broken():
    finding = check_job(Check("a"), _job(enabled=False), NOW, HOUR, WEEKDAY)
    assert finding.state == checks.SKIP and finding.detail == "disabled"


def test_weekend_only_jobs_are_not_nagged_on_a_weekend_break():
    finding = check_job(Check("a", days=[0, 1, 2, 3, 4]), _job(), NOW, HOUR, 5)
    assert finding.state == checks.SKIP


def test_a_job_outside_its_own_window_is_skipped():
    finding = check_job(Check("a"), _job(schedule={"expr": "0 3-5 * * *"}), NOW, HOUR, WEEKDAY)
    assert finding.state == checks.SKIP and "window" in finding.detail


def test_a_stale_run_is_a_problem_with_the_numbers_in_it():
    finding = check_job(Check("a", max_age_seconds=3600), _job(schedule={}), NOW, HOUR, WEEKDAY)
    assert finding.state == checks.FAIL
    assert "last run 8.0 h ago, limit 1.0 h" in finding.problems[0]


def test_a_job_that_never_ran_is_a_problem():
    finding = check_job(Check("a"), _job(last_run_at=None, schedule={}), NOW, HOUR, WEEKDAY)
    assert "has never run" in finding.problems[0]


def test_a_failed_status_carries_the_error_text():
    finding = check_job(
        Check("a"), _job(last_status="error", last_error="boom", schedule={}), NOW, HOUR, WEEKDAY
    )
    assert "last_status = error (boom)" in finding.problems[0]


def test_delivery_errors_are_problems_for_any_enabled_job():
    result = run(
        {"checks": [], "delivery": True},
        {"a": _job(last_delivery_error="chat not found")},
        NOW,
        HOUR,
        WEEKDAY,
    )
    assert "delivery failed — chat not found" in result.problems[0]


def test_a_failure_streak_matters_but_a_self_monitor_is_ignored():
    jobs = {"a": _job(failure_streak=4), "b": _job(failure_streak=9)}
    result = run(
        {"checks": [], "streak_limit": 3, "self_monitors": ["b"]}, jobs, NOW, HOUR, WEEKDAY
    )
    assert len(result.problems) == 1 and "4 failures in a row" in result.problems[0]


def test_a_state_file_that_stopped_checking_in_is_a_problem(tmp_path):
    state = tmp_path / "watch.json"
    state.write_text(json.dumps({"one": {"last_check": NOW - 5 * 3600}}), encoding="utf-8")
    config = {
        "checks": [],
        "state_files": [{"name": "watcher", "path": str(state), "max_age_seconds": 7200}],
    }
    result = run(config, {}, NOW, HOUR, WEEKDAY)
    assert "watcher: has not checked in for 5.0 h" in result.problems[0]


def test_a_state_file_with_fresh_stamps_is_silent(tmp_path):
    state = tmp_path / "watch.json"
    state.write_text(json.dumps({"one": {"last_check": NOW - 60}}), encoding="utf-8")
    config = {
        "checks": [],
        "state_files": [{"name": "watcher", "path": str(state), "max_age_seconds": 7200}],
    }
    assert run(config, {}, NOW, HOUR, WEEKDAY).problems == []


def test_a_missing_state_file_is_reported_by_name_not_by_traceback(tmp_path):
    config = {
        "checks": [],
        "state_files": [{"name": "watcher", "path": str(tmp_path / "nope.json")}],
    }
    result = run(config, {}, NOW, HOUR, WEEKDAY)
    assert result.problems == ["watcher: file not found"]


def test_the_run_counts_what_it_saw():
    config = {"checks": [{"job": "a", "name": "A"}, {"job": "b", "name": "B"}]}
    jobs = {"a": _job(schedule={}), "b": _job(schedule={}, enabled=False)}
    result = run(config, jobs, NOW, HOUR, WEEKDAY)
    assert (result.failed, result.skipped) == (0, 1)
    assert len(result.findings) == 2
