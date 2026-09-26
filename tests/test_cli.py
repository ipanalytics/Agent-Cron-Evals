from __future__ import annotations

import json

from agent_cron_evals import cli


def _job(**over):
    job = {
        "id": "a",
        "name": "A",
        "enabled": True,
        "last_status": "ok",
        "last_run_at": "2027-01-15T00:00:00Z",
        "schedule": {},
    }
    job.update(over)
    return job


def test_a_config_without_checks_is_refused(config_file, capsys):
    path = config_file([])
    assert cli.main(["--config", str(path)]) == 2
    assert "no checks configured" in capsys.readouterr().err


def test_a_check_without_a_job_id_is_refused(config_file, capsys):
    path = config_file([{"name": "no id"}])
    assert cli.main(["--config", str(path)]) == 2
    assert "needs a job id" in capsys.readouterr().err


def test_a_missing_job_list_is_reported_plainly(config_file, tmp_path, capsys):
    path = config_file([{"job": "a"}], jobs_file=str(tmp_path / "nope.json"))
    assert cli.main(["--config", str(path)]) == 2
    assert "cannot read the job list" in capsys.readouterr().err


def test_a_healthy_run_prints_nothing(config_file, jobs_file, tmp_path, capsys):
    jobs = jobs_file([_job()])
    path = config_file(
        [{"job": "a", "name": "A", "max_age_seconds": 10**9}],
        jobs_file=str(jobs),
        output=str(tmp_path / "record.json"),
    )
    assert cli.main(["--config", str(path)]) == 0
    assert capsys.readouterr().out == ""
    assert (tmp_path / "record.json").exists()


def test_problems_are_printed_one_line_each(config_file, jobs_file, tmp_path, capsys):
    jobs = jobs_file([_job(last_status="error", last_error="boom")])
    path = config_file(
        [{"job": "a", "name": "A"}], jobs_file=str(jobs), output=str(tmp_path / "record.json")
    )
    assert cli.main(["--config", str(path)]) == 0
    out = capsys.readouterr().out.splitlines()
    assert len(out) == 1 and "boom" in out[0]


def test_json_mode_prints_the_whole_record(config_file, jobs_file, tmp_path, capsys):
    jobs = jobs_file([_job()])
    path = config_file(
        [{"job": "a", "name": "A", "max_age_seconds": 10**9}],
        jobs_file=str(jobs),
        output=str(tmp_path / "record.json"),
    )
    assert cli.main(["--config", str(path), "--json"]) == 0
    record = json.loads(capsys.readouterr().out)
    assert record["summary"] == {"checks": 1, "failed": 0, "skipped": 0, "problems": 0}


def test_all_mode_lists_every_check_and_the_summary(config_file, jobs_file, tmp_path, capsys):
    jobs = jobs_file([_job()])
    path = config_file(
        [{"job": "a", "name": "A", "max_age_seconds": 10**9}],
        jobs_file=str(jobs),
        output=str(tmp_path / "record.json"),
    )
    assert cli.main(["--config", str(path), "--all"]) == 0
    out = capsys.readouterr().out
    assert "ok   A (a)" in out and "cron evals: 1 checks" in out


def test_quiet_writes_the_record_and_says_nothing(config_file, jobs_file, tmp_path, capsys):
    jobs = jobs_file([_job(last_status="error")])
    path = config_file(
        [{"job": "a", "name": "A"}], jobs_file=str(jobs), output=str(tmp_path / "record.json")
    )
    assert cli.main(["--config", str(path), "--quiet"]) == 0
    assert capsys.readouterr().out == ""
    assert json.loads((tmp_path / "record.json").read_text())["summary"]["failed"] == 1
