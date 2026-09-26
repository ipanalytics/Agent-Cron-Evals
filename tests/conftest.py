from __future__ import annotations

import json

import pytest


@pytest.fixture
def jobs_file(tmp_path):
    """A scheduler file in the shape the checks expect, with room to break one entry."""

    def build(jobs):
        path = tmp_path / "jobs.json"
        path.write_text(json.dumps({"jobs": jobs}), encoding="utf-8")
        return path

    return build


@pytest.fixture
def config_file(tmp_path):
    def build(checks, **extra):
        path = tmp_path / "evals.json"
        payload = {"checks": checks}
        payload.update(extra)
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    return build


@pytest.fixture
def now():
    return 1_800_000_000.0
