"""Utility for loading Agent Skills from SKILL.md files."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class SkillInfo:
    """Parsed skill information from a SKILL.md file."""

    name: str
    description: str
    content: str


def load_skills(skills_dir: Path | None = None) -> dict[str, SkillInfo]:
    """Discover and parse all SKILL.md files.

    Args:
        skills_dir: Path to the skills directory. If None, uses the
            skills/ directory relative to the project root.

    Returns:
        Dictionary mapping skill names to SkillInfo instances.
    """
    if skills_dir is None:
        # Find the skills directory relative to the project root
        # The project root is 3 levels up from this file:
        # src/rhoai_mcp/utils/skill_loader.py -> project root
        project_root = Path(__file__).parent.parent.parent.parent
        skills_dir = project_root / "skills"

    if not skills_dir.is_dir():
        logger.warning(f"Skills directory not found: {skills_dir}")
        return {}

    skills: dict[str, SkillInfo] = {}

    for skill_dir in sorted(skills_dir.iterdir()):
        if not skill_dir.is_dir():
            continue

        skill_file = skill_dir / "SKILL.md"
        if not skill_file.exists():
            continue

        try:
            content = skill_file.read_text()
            name, description = _parse_frontmatter(content)

            if name is None:
                name = skill_dir.name

            if description is None:
                description = f"Workflow guide for {name}"

            skills[name] = SkillInfo(
                name=name,
                description=description,
                content=content,
            )
        except Exception as e:
            logger.warning(f"Failed to parse skill {skill_dir.name}: {e}")

    logger.debug(f"Loaded {len(skills)} skills from {skills_dir}")
    return skills


def _parse_frontmatter(content: str) -> tuple[str | None, str | None]:
    """Parse YAML frontmatter from a SKILL.md file.

    Extracts the name and description fields from YAML frontmatter
    delimited by --- markers.

    Args:
        content: Full file content.

    Returns:
        Tuple of (name, description), either may be None if not found.
    """
    if not content.startswith("---"):
        return None, None

    # Find the closing ---
    end_idx = content.index("---", 3)
    frontmatter = content[3:end_idx].strip()

    name = None
    description = None

    for line in frontmatter.split("\n"):
        line = line.strip()
        if line.startswith("name:"):
            name = line[5:].strip().strip("\"'")
        elif line.startswith("description:"):
            description = line[12:].strip().strip("\"'")

    return name, description
