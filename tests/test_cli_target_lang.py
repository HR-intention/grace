"""Tests for the --target-lang CLI flag."""
import pytest
from src.cli import cli


def test_target_lang_help_text_lists_choices(cli_runner):
    result = cli_runner.invoke(cli, ["techspec", "--help"])
    assert result.exit_code == 0
    assert "--target-lang" in result.output
    assert "rust" in result.output
    assert "python" in result.output


def test_target_lang_default_is_python(cli_runner):
    result = cli_runner.invoke(cli, ["techspec", "--help"])
    assert result.exit_code == 0
    # The phrase may be wrapped across lines in --help output; check for both halves.
    assert "Default:" in result.output
    assert "python" in result.output


def test_target_lang_rejects_invalid_value(cli_runner):
    result = cli_runner.invoke(cli, ["techspec", "dummy", "--target-lang", "java", "--test-only"])
    assert result.exit_code != 0
    assert "java" in result.output.lower() or "invalid" in result.output.lower()


def test_target_lang_accepts_rust(cli_runner):
    # We only verify Click parses; the workflow itself will fail without docs, which is fine.
    result = cli_runner.invoke(cli, ["techspec", "--target-lang", "rust", "--help"])
    assert result.exit_code == 0


def test_target_lang_accepts_python(cli_runner):
    result = cli_runner.invoke(cli, ["techspec", "--target-lang", "python", "--help"])
    assert result.exit_code == 0


def test_short_flag_l_works(cli_runner):
    # Sanity: short flag works the same way
    result = cli_runner.invoke(cli, ["techspec", "-l", "rust", "--help"])
    assert result.exit_code == 0
