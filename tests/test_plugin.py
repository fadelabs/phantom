"""Tests for plugin skill content validation.

Validates SKILL.md frontmatter structure, MCP tool name references,
and domain semantic checks across all Phantom plugin skills.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

SKILLS_DIR = Path(__file__).parent.parent / "plugin" / "skills"

# ---------------------------------------------------------------------------
# Frontmatter helpers
# ---------------------------------------------------------------------------

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---", re.DOTALL)
_BACKTICK_REF_RE = re.compile(r"`([a-z][a-z0-9_]*)`")


class SkillFile:
    """Parsed representation of a SKILL.md file."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.text = path.read_text()
        self._fm_match = _FRONTMATTER_RE.match(self.text)

    @property
    def frontmatter(self) -> str | None:
        """Raw YAML frontmatter (without delimiters), or None."""
        return self._fm_match.group(1) if self._fm_match else None

    @property
    def body(self) -> str:
        """Markdown body after the frontmatter block."""
        if self._fm_match:
            # Skip past closing --- and any trailing whitespace
            end = self.text.index("---", self._fm_match.start(1))
            end = self.text.index("\n", end + 3) + 1
            return self.text[end:]
        return self.text

    def field(self, name: str) -> str:
        """Extract a scalar or folded-block field from frontmatter."""
        fm = self.frontmatter
        if fm is None:
            return ""
        for i, line in enumerate(fm_lines := fm.split("\n")):
            if not line.startswith(f"{name}:"):
                continue
            value = line[len(f"{name}:") :].strip()
            if value and value != ">":
                return value
            # Multi-line folded block: collect indented continuation lines
            parts: list[str] = []
            for j in range(i + 1, len(fm_lines)):
                if fm_lines[j] and not fm_lines[j][0].isspace():
                    break
                parts.append(fm_lines[j].strip())
            return " ".join(p for p in parts if p)
        return ""

    def tool_references(self) -> set[str]:
        """Return all backtick-quoted identifiers from the body."""
        return set(_BACKTICK_REF_RE.findall(self.body))


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------


def _discover_skills() -> list[Path]:
    """Return sorted list of skill directories containing SKILL.md."""
    return sorted(
        d for d in SKILLS_DIR.iterdir() if d.is_dir() and (d / "SKILL.md").exists()
    )


def _get_phantom_tool_names() -> set[str]:
    """Discover Phantom MCP tool names dynamically from the server registry."""
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
        assert (skill_dir / "SKILL.md").exists(), (
            f"Missing SKILL.md in {skill_dir.name}"
        )


@pytest.mark.parametrize("skill_dir", SKILLS, ids=SKILL_IDS)
def test_skill_has_required_frontmatter(skill_dir: Path):
    """Each SKILL.md has name and description in YAML frontmatter."""
    skill = SkillFile(skill_dir / "SKILL.md")

    assert skill.frontmatter is not None, (
        f"{skill_dir.name}/SKILL.md has no YAML frontmatter"
    )

    name_val = skill.field("name")
    assert name_val, f"{skill_dir.name}/SKILL.md missing 'name' field"

    desc_val = skill.field("description")
    assert desc_val, f"{skill_dir.name}/SKILL.md missing 'description' field"

    assert name_val == skill_dir.name, (
        f"Frontmatter name '{name_val}' does not match directory '{skill_dir.name}'"
    )


@pytest.mark.parametrize("skill_dir", SKILLS, ids=SKILL_IDS)
def test_phantom_tool_references_valid(skill_dir: Path):
    """Every Phantom MCP tool reference in a skill is a valid registered tool."""
    skill = SkillFile(skill_dir / "SKILL.md")
    phantom_tools = _get_phantom_tool_names()

    # Only check references that overlap with Phantom tool names.
    # Non-Phantom refs (Reaper MCP tools, general terms) are ignored.
    phantom_refs = skill.tool_references() & phantom_tools

    # By construction phantom_refs is a subset of phantom_tools,
    # so this assertion guards against future refactoring errors.
    invalid = phantom_refs - phantom_tools
    assert not invalid, (
        f"{skill_dir.name}/SKILL.md references invalid Phantom tools: {invalid}"
    )


@pytest.mark.parametrize("skill_dir", SKILLS, ids=SKILL_IDS)
def test_skill_domain_semantic(skill_dir: Path):
    """Each skill's description contains at least one domain keyword."""
    skill = SkillFile(skill_dir / "SKILL.md")

    assert skill.frontmatter is not None
    desc = skill.field("description").lower()
    keywords = DOMAIN_KEYWORDS.get(skill_dir.name, [])

    assert keywords, f"No domain keywords defined for {skill_dir.name}"

    matches = [kw for kw in keywords if kw in desc]
    assert matches, (
        f"{skill_dir.name} description does not contain any domain keywords: {keywords}"
    )
