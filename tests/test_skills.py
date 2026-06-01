"""Test skill front-matter parsing and tag-based injection."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from cohub.core import skills as sk_mod


SKILL_A = """---
name: stata-style
tags: [stata, economics]
when: writing Stata code
---

# Stata Style
- three-line tables
- sort before merge
"""

SKILL_B = """---
name: python-cleanup
tags: [python]
---

# Python Cleanup
- read CSV with utf-8-sig
"""


def test_parse_skill_front_matter() -> None:
    s = sk_mod.parse_skill_text(SKILL_A, name_fallback="x")
    assert s.name == "stata-style"
    assert "stata" in s.tags
    assert s.when.startswith("writing Stata")
    assert "three-line tables" in s.body


def test_parse_skill_without_front_matter() -> None:
    s = sk_mod.parse_skill_text("just body", name_fallback="raw")
    assert s.name == "raw"
    assert s.tags == []
    assert s.body == "just body"


def test_collect_skills_by_tag_intersection(tmp_path: Path) -> None:
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    (skills_dir / "stata-style.md").write_text(SKILL_A, encoding="utf-8")
    (skills_dir / "python-cleanup.md").write_text(SKILL_B, encoding="utf-8")

    with patch.object(sk_mod.paths, "skills_dir", return_value=skills_dir):
        chosen = sk_mod.collect_skills(project_tags=["stata"], forced_names=[])
        names = [s.name for s in chosen]
        assert "stata-style" in names
        assert "python-cleanup" not in names


def test_collect_skills_forced_overrides_tags(tmp_path: Path) -> None:
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    (skills_dir / "stata-style.md").write_text(SKILL_A, encoding="utf-8")
    (skills_dir / "python-cleanup.md").write_text(SKILL_B, encoding="utf-8")

    with patch.object(sk_mod.paths, "skills_dir", return_value=skills_dir):
        chosen = sk_mod.collect_skills(project_tags=[], forced_names=["python-cleanup"])
        names = [s.name for s in chosen]
        assert names == ["python-cleanup"]


def test_render_skills_block_empty() -> None:
    assert sk_mod.render_skills_block([]) == ""


def test_render_skills_block_has_marker(tmp_path: Path) -> None:
    s = sk_mod.parse_skill_text(SKILL_A)
    rendered = sk_mod.render_skills_block([s])
    assert "# Applicable Skills" in rendered
    assert "stata-style" in rendered
    assert "three-line tables" in rendered
