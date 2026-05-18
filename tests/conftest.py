"""Shared pytest fixtures."""
import pytest


@pytest.fixture
def cli_runner():
    """A Click CliRunner for invoking the grace CLI in-process."""
    from click.testing import CliRunner
    return CliRunner()
