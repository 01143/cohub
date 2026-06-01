"""技能加载和注入。

Skill 文件位于 ~/.cohub/skills/<name>.md,带 YAML front-matter:
    ---
    name: ...
    tags: [...]
    when: ...
    ---
    # 标题
    内容
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

import yaml

from . import paths


_FRONT_RE = re.compile(r"^---\s*\n(?P<fm>.*?)\n---\s*\n(?P<body>.*)$", re.DOTALL)


@dataclass
class Skill:
    name: str
    tags: list[str] = field(default_factory=list)
    when: str = ""
    body: str = ""
    path: Path | None = None


def parse_skill_text(text: str, name_fallback: str = "") -> Skill:
    m = _FRONT_RE.match(text)
    if not m:
        return Skill(name=name_fallback, body=text.strip())
    fm = yaml.safe_load(m.group("fm")) or {}
    body = m.group("body").strip()
    return Skill(
        name=str(fm.get("name") or name_fallback),
        tags=list(fm.get("tags") or []),
        when=str(fm.get("when") or ""),
        body=body,
    )


def load_skill_file(p: Path) -> Skill:
    s = parse_skill_text(p.read_text(encoding="utf-8"), name_fallback=p.stem)
    s.path = p
    return s


def load_all_skills() -> list[Skill]:
    d = paths.skills_dir()
    if not d.exists():
        return []
    out: list[Skill] = []
    for p in sorted(d.glob("*.md")):
        try:
            out.append(load_skill_file(p))
        except Exception:
            # 损坏的文件不致命,跳过
            continue
    return out


def collect_skills(project_tags: Iterable[str], forced_names: Iterable[str]) -> list[Skill]:
    """根据 tags 交集 + force 名称收集要注入的 skill。

    重复(同名)只保留一次,顺序: forced 优先,然后按 tag 命中。
    """
    all_skills = load_all_skills()
    tag_set = set(project_tags or [])
    forced_set = set(forced_names or [])

    chosen: list[Skill] = []
    seen: set[str] = set()

    # forced 优先
    for s in all_skills:
        if s.name in forced_set and s.name not in seen:
            chosen.append(s)
            seen.add(s.name)

    # tag 命中
    for s in all_skills:
        if s.name in seen:
            continue
        if tag_set and (set(s.tags) & tag_set):
            chosen.append(s)
            seen.add(s.name)

    return chosen


def render_skills_block(skills: list[Skill]) -> str:
    if not skills:
        return ""
    parts = ["# 适用技能"]
    for s in skills:
        parts.append(f"\n## {s.name}")
        if s.when:
            parts.append(f"_适用时机:{s.when}_")
        parts.append("")
        parts.append(s.body)
    return "\n".join(parts).strip()
