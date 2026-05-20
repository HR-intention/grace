from __future__ import annotations

from pathlib import Path

import pytest

from grace.errors import GraceError, GraceErrorReason
from grace.skills_install import install_skills, list_skills


def test_list_skills_includes_add_connector() -> None:
    """The bundle ships at least the add-connector skill."""
    names = list_skills()
    assert "add-connector" in names
    # `_shared` is not a skill itself.
    assert "_shared" not in names


def test_install_skills_writes_target_skills_dir(tmp_path: Path) -> None:
    result = install_skills(target_root=tmp_path)
    assert result.install_root == tmp_path / ".skills"
    assert result.install_root.is_dir()
    assert (result.install_root / "add-connector" / "SKILL.md").is_file()
    assert (result.install_root / "_shared" / "references" / "flow-patterns" / "create_order.md").is_file()
    assert "add-connector" in result.skills_installed
    assert result.files_written > 0


def test_install_skill_skill_md_is_valid_frontmatter(tmp_path: Path) -> None:
    install_skills(target_root=tmp_path)
    text = (tmp_path / ".skills" / "add-connector" / "SKILL.md").read_text()
    assert text.startswith("---\n")
    assert "name: add-connector" in text
    assert "description:" in text


def test_install_skills_refuses_to_clobber_without_force(tmp_path: Path) -> None:
    install_skills(target_root=tmp_path)
    with pytest.raises(GraceError) as exc:
        install_skills(target_root=tmp_path)
    assert exc.value.reason is GraceErrorReason.CONTEXT_BUNDLE_INVALID
    assert "force" in (exc.value.detail or "")


def test_install_skills_force_replaces(tmp_path: Path) -> None:
    install_skills(target_root=tmp_path)
    # Drop a marker file inside the existing skill to confirm it gets replaced
    poison = tmp_path / ".skills" / "add-connector" / "MARKER_FROM_TEST.txt"
    poison.write_text("should disappear")
    result = install_skills(target_root=tmp_path, force=True)
    assert "add-connector" in result.skills_installed
    assert not poison.exists()
