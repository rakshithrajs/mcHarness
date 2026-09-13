from pathlib import Path

import yaml

SKILL_DIRs: list[Path] = [
    Path.cwd() / ".agents" / "skills",
    Path(r"C:\Users\raksh\.claude\skills"),
    Path(
        r"C:\Users\raksh\.claude\plugins\cache\claude-plugins-official\superpowers\5.0.7\skills"
    ),
]


def find_skills() -> dict[str, dict[str, str | Path]]:
    """Map each skill name to its description and SKILL.md path"""
    skills: dict[str, dict[str, str | Path]] = {}
    for dir in SKILL_DIRs:
        for path in sorted(dir.glob("*/SKILL.md")):
            _, formatter, _ = path.read_text(encoding="utf-8").split("---", 2)
            meta = yaml.safe_load(formatter)
            description = " ".join(meta["description"].split())
            skills[meta["name"]] = {"description": description, "path": path}
    return skills


SKILLS = find_skills()


def skills_prompt():
    return "\n".join(f" - {name}: {s['description']}" for name, s in SKILLS.items())


def read_skill(name: str) -> str:
    """Open a skill and return its full instructions"""
    if name not in SKILLS:
        return f"no skill names {name}"
    return Path(SKILLS[name]["path"]).read_text()


if __name__ == "__main__":
    print(skills_prompt())
