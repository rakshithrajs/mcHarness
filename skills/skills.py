"""Skills management for the harness agent."""

import os
from pathlib import Path

import yaml

_SKILLS_HOME = Path(
    os.environ.get("CLAUDE_SKILLS_DIR", Path.home() / ".claude" / "skills")
)
_PLUGINS_CACHE = Path.home() / ".claude" / "plugins" / "cache"

SKILL_DIRs: list[Path] = [
    Path.cwd() / ".agents" / "skills",
    _SKILLS_HOME,
    # Official superpowers plugin skills, if installed (version-agnostic glob).
    _PLUGINS_CACHE / "claude-plugins-official" / "superpowers" / "5.0.7" / "skills",
]


def _skill_dirs() -> list[Path]:
    """Return the configured skill directories, expanding the superpowers version glob."""
    dirs: list[Path] = []
    for skill_dir in SKILL_DIRs:
        if skill_dir.exists():
            dirs.append(skill_dir)
    # Expand any versioned superpowers cache directories to their `skills` subfolder.
    expanded: list[Path] = []
    for d in dirs:
        if d.name == "superpowers":
            for versioned in sorted(d.glob("*")):
                skills_sub = versioned / "skills"
                if skills_sub.is_dir():
                    expanded.append(skills_sub)
        else:
            expanded.append(d)
    return expanded


def _parse_frontmatter(text: str) -> dict[str, str]:
    """Parse the YAML frontmatter of a SKILL.md file, tolerating missing delimiters.

    SKILL.md files use ``---`` fenced frontmatter. Not every file is guaranteed to
    have it, so we split defensively rather than assuming exactly three parts.
    """
    if not text.startswith("---"):
        return {}
    parts = text.split("---", 2)
    # parts[0] is empty (text starts with ---), parts[1] is the YAML block.
    if len(parts) < 3:
        return {}
    meta = yaml.safe_load(parts[1])
    if not isinstance(meta, dict):
        return {}
    return meta


def find_skills() -> dict[str, dict[str, str | Path]]:
    """Map each skill name to its description and SKILL.md path."""
    skills: dict[str, dict[str, str | Path]] = {}
    for skill_dir in _skill_dirs():
        for path in sorted(skill_dir.glob("*/SKILL.md")):
            meta = _parse_frontmatter(path.read_text(encoding="utf-8"))
            name = meta.get("name")
            description = meta.get("description")
            if not name or not description:
                continue
            skills[name] = {
                "description": " ".join(description.split()),
                "path": path,
            }
    return skills


SKILLS = find_skills()


def skills_prompt() -> str:
    """Return a string representation of the available skills."""
    return "\n".join(f" - {name}: {s['description']}" for name, s in SKILLS.items())


def read_skill(name: str) -> str:
    """Open a skill and return its full instructions."""
    if name not in SKILLS:
        return f"no skill names {name}"
    return Path(SKILLS[name]["path"]).read_text()


if __name__ == "__main__":
    print(skills_prompt())
