from __future__ import annotations

import pytest

from agent_cron_evals import config


def test_defaults_fill_in_the_rest(config_file):
    conf = config.load(config_file([{"job": "a"}]))
    assert conf["streak_limit"] == 3
    assert conf["delivery"] is True
    assert conf["jobs_file"].endswith("jobs.json")
    assert conf["output"].endswith("cron_evals.json")


def test_a_list_instead_of_an_object_is_refused(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("[]", encoding="utf-8")
    with pytest.raises(ValueError, match="JSON object"):
        config.load(path)


def test_a_check_without_a_job_is_refused(config_file):
    with pytest.raises(ValueError, match="job id"):
        config.load(config_file([{"name": "who?"}]))


def test_expand_handles_tilde_and_variables(monkeypatch, tmp_path):
    monkeypatch.setenv("PROBE_DIR", str(tmp_path))
    assert config.expand("~/x.json").startswith(str(__import__("pathlib").Path.home()))
    assert config.expand("$PROBE_DIR/x.json") == f"{tmp_path}/x.json"
