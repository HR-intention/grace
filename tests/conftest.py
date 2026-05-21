"""Test isolation autouse fixtures.

Two layers of defense to keep the test suite from touching the developer's
real environment:

1. `Path.home()` → tmp_path subdir. Belt for any code that still reads from
   the user-global `~/.grace/` (e.g., `grace.config.load_config`'s default
   `~/.grace/config.yaml` lookup).

2. `os.chdir(tmp_path)` → tmp_path. Suspenders for the per-project state
   that `_last_run_path()` and `_default_docs_dir()` now resolve through
   `Path.cwd()`. Without the chdir, a CLI test that invokes `grace generate`
   would write `.grace/last_run.json` into Grace's own checkout.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _isolate_filesystem_for_grace(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Pin Path.home() and the process cwd to per-test tmp dirs.

    Per-test scope (matches tmp_path) so the isolation rolls back at the
    end of every test, even if the test itself further mutates the cwd.
    """
    fake_home = tmp_path / "_grace_test_home"
    fake_home.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(Path, "home", lambda: fake_home)

    fake_cwd = tmp_path / "_grace_test_cwd"
    fake_cwd.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(fake_cwd)
