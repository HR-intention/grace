"""Tests for the language-aware next-step printing in output_node."""
import pytest

from src.workflows.techspec.nodes.output_node import LANG_NEXT_STEPS, _print_next_step


def test_lang_next_steps_has_both_languages():
    assert "rust" in LANG_NEXT_STEPS
    assert "python" in LANG_NEXT_STEPS


def test_lang_next_steps_rust_points_to_codegen_rust():
    assert LANG_NEXT_STEPS["rust"]["target_repo"] == "connector-service/"
    assert "codegen-rust" in LANG_NEXT_STEPS["rust"]["rulesbook_path"]


def test_lang_next_steps_python_points_to_codegen_python():
    assert LANG_NEXT_STEPS["python"]["target_repo"] == "connector-service-python/"
    assert "codegen-python" in LANG_NEXT_STEPS["python"]["rulesbook_path"]


def test_print_next_step_warns_when_target_repo_missing(capsys):
    # connector-service-python doesn't exist as a sibling of grace/ during testing
    _print_next_step("python", "razorpay")
    captured = capsys.readouterr()
    assert "⚠️" in captured.out or "not found" in captured.out
    assert "connector-service-python" in captured.out


def test_print_next_step_outputs_something_for_rust(capsys):
    # connector-service/ may or may not exist as a sibling. Either way, something should print.
    _print_next_step("rust", "stripe")
    captured = capsys.readouterr()
    assert captured.out  # non-empty


def test_print_next_step_silent_for_unknown_lang(capsys):
    _print_next_step("typescript", "stripe")
    captured = capsys.readouterr()
    assert captured.out == ""  # unknown lang → no output


def test_output_node_invokes_print_next_step(capsys, tmp_path):
    """End-to-end smoke: output_node() should read target_lang from state and print a hint or warning."""
    from src.workflows.techspec.nodes.output_node import output_node

    minimal_state = {
        "target_lang": "python",
        "connector_name": "razorpay",
        "metadata": {"successful_crawls": 0, "failed_crawls": 0},
        "output_dir": tmp_path,
        "errors": [],
        "urls_file": "dummy",  # skip the links-writing branch
    }
    result = output_node(minimal_state)  # noqa: F841
    captured = capsys.readouterr()
    # Either the success-path hint OR the warning should appear — both prove the call wired through.
    assert "razorpay" in captured.out.lower() or "not found" in captured.out.lower() or "target_lang" in captured.out.lower() or "python" in captured.out.lower()
