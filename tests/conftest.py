"""Test isolation autouse fixtures.

These run before every test and prevent the test suite from touching the
developer's real `~/` — specifically the `~/.grace/` config + last_run
state that the CLI persists between runs.

Without this, tests that exercise `grace generate` via Click's CliRunner
would write to the real `~/.grace/last_run.json` (because `_save_last_run`
fires before the pipeline runs, regardless of whether the pipeline is
mocked) and pollute the developer's environment. We've seen this cause
a `grace regenerate` outside the test suite to replay a tmp pytest path
that no longer exists.
"""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _isolate_home_for_grace(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Point Path.home() at a per-test tmp directory.

    Any code that builds paths off `Path.home()` (notably
    `grace.cli._last_run_path` and `grace.config.load_config`'s default
    `~/.grace/config.yaml` lookup) will land inside this test's tmp_path
    sandbox instead of the developer's real home.
    """
    fake_home = tmp_path / "_grace_test_home"
    fake_home.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(Path, "home", lambda: fake_home)
