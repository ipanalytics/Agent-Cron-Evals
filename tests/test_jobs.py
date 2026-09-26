from __future__ import annotations

import json

from agent_cron_evals.jobs import age_seconds, load, parse_ts

NOW = 1_800_000_000.0


def test_a_bare_list_and_a_wrapped_one_read_the_same(tmp_path, jobs_file):
    jobs = [{"id": "a", "name": "first"}]
    assert load(jobs_file(jobs))["a"]["name"] == "first"
    path = tmp_path / "bare.json"
    path.write_text(json.dumps(jobs), encoding="utf-8")
    assert load(path)["a"]["name"] == "first"


def test_junk_entries_are_skipped_not_fatal(jobs_file):
    path = jobs_file([{"id": "a"}, "nonsense", {"name": "no id"}, None, {"job_id": "b"}])
    loaded = load(path)
    assert set(loaded) == {"a", "b"}


def test_iso_timestamps_with_and_without_a_zone_are_understood():
    assert parse_ts("2027-01-15T04:00:00Z") is not None
    assert parse_ts("2027-01-15T04:00:00+00:00") == parse_ts("2027-01-15T04:00:00Z")
    # a naive timestamp is read as UTC rather than guessed
    assert parse_ts("2027-01-15T04:00:00") == parse_ts("2027-01-15T04:00:00Z")


def test_epoch_seconds_are_accepted():
    assert parse_ts(1_800_000_000) == float(NOW)


def test_nonsense_is_none():
    assert parse_ts(None) is None
    assert parse_ts("") is None
    assert parse_ts("last Tuesday") is None


def test_age_prefers_the_run_timestamp_that_exists():
    assert age_seconds({"last_run_at": "2027-01-15T00:00:00Z"}, NOW) is not None
    assert age_seconds({"last_finished_at": "2027-01-15T00:00:00Z"}, NOW) is not None
    assert age_seconds({"name": "no timestamps at all"}, NOW) is None
