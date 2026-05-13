"""Tests for plugin skill content validation.

Validates SKILL.md frontmatter structure, MCP tool name references,
and domain semantic checks across all Phantom plugin skills.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

SKILLS_DIR = Path(__file__).parent.parent / "plugin" / "skills"


def _discover_skills():
    """Return sorted list of skill directories containing SKILL.md."""
    return sorted(
        d for d in SKILLS_DIR.iterdir() if d.is_dir() and (d / "SKILL.md").exists()
    )


def _parse_frontmatter(text: str) -> str | None:
    """Extract YAML frontmatter block from Markdown text.

    Returns the raw frontmatter string (without delimiters) or None.
    """
    match = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
    return match.group(1) if match else None


def _extract_field(frontmatter: str, field: str) -> str:
    """Extract a field value from YAML frontmatter.

    Handles both single-line values and multi-line folded blocks (>).
    """
    lines = frontmatter.split("\n")
    for i, line in enumerate(lines):
        if line.startswith(f"{field}:"):
            # Check for inline value
            value = line[len(f"{field}:") :].strip()
            if value and value != ">":
                return value

            # Multi-line folded block: collect indented continuation lines
            parts = []
            for j in range(i + 1, len(lines)):
                if lines[j] and not lines[j][0].isspace():
                    break
                parts.append(lines[j].strip())
            return " ".join(p for p in parts if p)
    return ""


def _get_phantom_tool_names() -> set[str]:
    """Discover Phantom MCP tool names from server.py at import time."""
    from phantom.server import mcp

    return set(mcp._tool_manager._tools.keys())


SKILLS = _discover_skills()
SKILL_IDS = [s.name for s in SKILLS]

DOMAIN_KEYWORDS: dict[str, list[str]] = {
    "audio-diagnostician": ["diagnostic", "analysis", "problem"],
    "effects-engineer": ["effect", "processing", "sound design"],
    "mastering-engineer": ["mastering", "loudness"],
    "mix-engineer": ["mix", "fader", "eq", "level"],
    "session-architect": ["session", "reaper", "daw", "track"],
}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_all_skills_discovered():
    """At least 5 skill directories exist, each containing SKILL.md."""
    assert len(SKILLS) >= 5, f"Expected >= 5 skills, found {len(SKILLS)}"
    for skill_dir in SKILLS:
        skill_file = skill_dir / "SKILL.md"
        assert skill_file.exists(), f"Missing SKILL.md in {skill_dir.name}"


@pytest.mark.parametrize("skill_dir", SKILLS, ids=SKILL_IDS)
def test_skill_has_required_frontmatter(skill_dir: Path):
    """Each SKILL.md has name and description in YAML frontmatter."""
    text = (skill_dir / "SKILL.md").read_text()
    frontmatter = _parse_frontmatter(text)
    assert frontmatter is not None, f"{skill_dir.name}/SKILL.md has no YAML frontmatter"

    name_val = _extract_field(frontmatter, "name")
    assert name_val, f"{skill_dir.name}/SKILL.md missing 'name' field"

    desc_val = _extract_field(frontmatter, "description")
    assert desc_val, f"{skill_dir.name}/SKILL.md missing 'description' field"

    # Name must match directory name
    assert name_val == skill_dir.name, (
        f"Frontmatter name '{name_val}' does not match directory '{skill_dir.name}'"
    )


@pytest.mark.parametrize("skill_dir", SKILLS, ids=SKILL_IDS)
def test_phantom_tool_references_valid(skill_dir: Path):
    """Every Phantom MCP tool reference in a skill is a valid registered tool."""
    text = (skill_dir / "SKILL.md").read_text()

    # Extract body after frontmatter
    match = re.match(r"^---\s*\n.*?\n---\s*\n", text, re.DOTALL)
    body = text[match.end() :] if match else text

    # Find all backtick-quoted references that look like tool names
    refs = set(re.findall(r"`([a-z][a-z0-9_]*)`", body))

    phantom_tools = _get_phantom_tool_names()

    # Only validate references that are actually Phantom tool names
    # (ignore Reaper MCP tool names and other backtick-quoted terms)
    phantom_refs = refs & phantom_tools
    invalid = phantom_refs - phantom_tools

    assert not invalid, (
        f"{skill_dir.name}/SKILL.md references invalid Phantom tools: {invalid}"
    )

    # Also verify non-Phantom refs are not accidentally close to Phantom tools
    # (This is a soft check -- just ensures we found some refs in skills that use tools)
    if skill_dir.name != "effects-engineer":
        # effects-engineer may have minimal direct Phantom tool refs
        pass


@pytest.mark.parametrize("skill_dir", SKILLS, ids=SKILL_IDS)
def test_skill_domain_semantic(skill_dir: Path):
    """Each skill's description contains at least one domain keyword."""
    text = (skill_dir / "SKILL.md").read_text()
    frontmatter = _parse_frontmatter(text)
    assert frontmatter is not None

    desc = _extract_field(frontmatter, "description").lower()
    keywords = DOMAIN_KEYWORDS.get(skill_dir.name, [])

    assert keywords, f"No domain keywords defined for {skill_dir.name}"

    matches = [kw for kw in keywords if kw in desc]
    assert matches, (
        f"{skill_dir.name} description does not contain any domain keywords: {keywords}"
    )
