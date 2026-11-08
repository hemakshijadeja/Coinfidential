"""Validate the YAML frontmatter of every .claude/skills/*/SKILL.md file.

Exits with status 0 if all skills are valid, or 1 if any check fails.
"""

import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = ROOT / ".claude" / "skills"

FRONTMATTER = re.compile(r"\A---[ \t]*\n(.*?)^---[ \t]*$", re.DOTALL | re.MULTILINE)
SKILL_NAME = re.compile(r"[a-z0-9]+(-[a-z0-9]+)*")
MAX_NAME_LENGTH = 64
MAX_DESCRIPTION_LENGTH = 1024


def validate_skill(skill_dir: Path) -> list[str]:
    """Return the problems found in one skill folder."""
    skill_file = skill_dir / "SKILL.md"
    if not skill_file.is_file():
        return ["SKILL.md is missing"]

    try:
        text = skill_file.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError as error:
        return [f"SKILL.md is not valid UTF-8: {error}"]

    match = FRONTMATTER.match(text)
    if match is None:
        return ["SKILL.md must start with YAML frontmatter enclosed by --- lines"]

    try:
        frontmatter = yaml.safe_load(match.group(1))
    except yaml.YAMLError as error:
        return [f"frontmatter is not valid YAML: {error}"]

    if not isinstance(frontmatter, dict):
        return ["frontmatter must be a YAML mapping"]

    return [
        *validate_name(frontmatter.get("name"), skill_dir.name),
        *validate_description(frontmatter.get("description")),
    ]


def validate_name(name: object, folder_name: str) -> list[str]:
    if not isinstance(name, str) or not name:
        return ["'name' is required and must be a non-empty string"]

    errors = []
    if len(name) > MAX_NAME_LENGTH:
        errors.append(f"'name' must be at most {MAX_NAME_LENGTH} characters")
    if SKILL_NAME.fullmatch(name) is None:
        errors.append(
            f"'name' ({name!r}) must use lowercase letters, numbers and single "
            "hyphens, with no hyphen at the start or end"
        )
    if name != folder_name:
        errors.append(f"'name' ({name!r}) must match its folder name ({folder_name!r})")
    return errors


def validate_description(description: object) -> list[str]:
    if not isinstance(description, str) or not description.strip():
        return ["'description' is required and must be a non-empty string"]
    if len(description) > MAX_DESCRIPTION_LENGTH:
        return [f"'description' must be at most {MAX_DESCRIPTION_LENGTH} characters"]
    return []


def main() -> int:
    skill_dirs = (
        sorted(path for path in SKILLS_DIR.iterdir() if path.is_dir())
        if SKILLS_DIR.is_dir()
        else []
    )
    if not skill_dirs:
        print(f"FAIL: no skills found in {SKILLS_DIR}")
        return 1

    failed = False
    for skill_dir in skill_dirs:
        errors = validate_skill(skill_dir)
        if errors:
            failed = True
            print(f"FAIL: {skill_dir.name}")
            for error in errors:
                print(f"  - {error}")
        else:
            print(f"OK: {skill_dir.name}")

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
