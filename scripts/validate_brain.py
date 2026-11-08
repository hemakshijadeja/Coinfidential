"""Validate the Second Brain in brain/.

Checks that:
- brain/index.md and brain/log.md exist.
- Every [[wikilink]] in brain/ resolves to a real note or a requirement ID.
  Links inside code spans and code blocks are ignored.
- Every note in a PARA folder has valid YAML frontmatter with the required
  fields: id, title, type, author, stage and related_requirements.

Exits with status 0 if the brain is valid, or 1 if any check fails.
"""

import re
import sys
from collections import Counter
from collections.abc import Iterator
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
BRAIN_DIR = ROOT / "brain"
REQUIRED_FILES = ("index.md", "log.md")
PARA_FOLDERS = ("inbox", "projects", "areas", "resources", "archive")
NOTE_TYPES = ("research", "ai-session", "review", "capture")
FIRST_STAGE = 1
LAST_STAGE = 4

WIKILINK = re.compile(r"\[\[([^\[\]\n]+)\]\]")
INLINE_CODE = re.compile(r"(`+).+?\1")
CODE_FENCE = re.compile(r"\s*(`{3,}|~{3,})")
FRONTMATTER = re.compile(r"\A---[ \t]*\n(.*?)^---[ \t]*$", re.DOTALL | re.MULTILINE)
REQUIREMENT_ID = re.compile(r"FR-[1-5]|SE-[1-7]|(NFR|SK|TQ|SB)-[1-9][0-9]*")


def iter_wikilinks(text: str) -> Iterator[tuple[int, str]]:
    """Yield (line number, target) for each wikilink outside code."""
    open_fence = None
    for line_number, line in enumerate(text.splitlines(), start=1):
        fence = CODE_FENCE.match(line)
        if fence:
            marker = fence.group(1)
            if open_fence is None:
                open_fence = marker
                continue
            if marker[0] == open_fence[0] and len(marker) >= len(open_fence):
                open_fence = None
                continue
        if open_fence is not None:
            continue

        for match in WIKILINK.finditer(INLINE_CODE.sub("", line)):
            yield line_number, match.group(1)


def normalize_target(raw_target: str) -> str:
    """Remove display text, heading, block reference and .md from a link."""
    target = re.split(r"[|#^]", raw_target, maxsplit=1)[0]
    # A pipe inside a Markdown table is written as \| so a backslash may remain.
    target = target.rstrip("\\").strip().replace("\\", "/")
    return target.removesuffix(".md")


def collect_note_names(notes: list[Path]) -> set[str]:
    """Return the names a note can be linked by: filename or path from brain/."""
    names = set()
    for note in notes:
        names.add(note.stem)
        names.add(note.relative_to(BRAIN_DIR).with_suffix("").as_posix())
    return names


def is_para_note(note: Path) -> bool:
    return note.relative_to(BRAIN_DIR).parts[0] in PARA_FOLDERS


def is_non_empty_string(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def validate_links(text: str, note_names: set[str]) -> list[str]:
    errors = []
    for line_number, raw_target in iter_wikilinks(text):
        target = normalize_target(raw_target)
        # An empty target, such as [[#Heading]], points to the current note.
        if (
            target
            and target not in note_names
            and REQUIREMENT_ID.fullmatch(target) is None
        ):
            errors.append(f"line {line_number}: unresolved link [[{raw_target}]]")
    return errors


def validate_frontmatter(text: str, note_stem: str) -> list[str]:
    match = FRONTMATTER.match(text)
    if match is None:
        return ["must start with YAML frontmatter enclosed by --- lines"]

    try:
        frontmatter = yaml.safe_load(match.group(1))
    except yaml.YAMLError as error:
        return [f"frontmatter is not valid YAML: {error}"]

    if not isinstance(frontmatter, dict):
        return ["frontmatter must be a YAML mapping"]

    errors = []
    if frontmatter.get("id") != note_stem:
        errors.append(f"'id' is required and must match the filename ({note_stem!r})")
    for field in ("title", "author"):
        if not is_non_empty_string(frontmatter.get(field)):
            errors.append(f"'{field}' is required and must be a non-empty string")
    if frontmatter.get("type") not in NOTE_TYPES:
        errors.append(f"'type' is required and must be one of: {', '.join(NOTE_TYPES)}")
    errors.extend(validate_stage(frontmatter.get("stage")))
    errors.extend(validate_requirements(frontmatter.get("related_requirements")))
    return errors


def validate_stage(stage: object) -> list[str]:
    # bool is a subclass of int, so `stage: true` must be rejected explicitly.
    if (
        not isinstance(stage, int)
        or isinstance(stage, bool)
        or not FIRST_STAGE <= stage <= LAST_STAGE
    ):
        return [
            f"'stage' is required and must be a number from {FIRST_STAGE} to {LAST_STAGE}"
        ]
    return []


def validate_requirements(requirements: object) -> list[str]:
    if not isinstance(requirements, list):
        return ["'related_requirements' is required and must be a list (use [] if none)"]
    return [
        f"'related_requirements' has an unrecognized ID: {requirement!r}"
        for requirement in requirements
        if not isinstance(requirement, str)
        or REQUIREMENT_ID.fullmatch(requirement) is None
    ]


def validate_note(note: Path, note_names: set[str]) -> list[str]:
    relative_path = note.relative_to(ROOT).as_posix()
    try:
        text = note.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError as error:
        return [f"{relative_path}: not valid UTF-8: {error}"]

    errors = validate_links(text, note_names)
    if is_para_note(note):
        errors.extend(validate_frontmatter(text, note.stem))
    return [f"{relative_path}: {error}" for error in errors]


def main() -> int:
    errors = [
        f"brain/{name} is missing"
        for name in REQUIRED_FILES
        if not (BRAIN_DIR / name).is_file()
    ]

    notes = sorted(BRAIN_DIR.rglob("*.md")) if BRAIN_DIR.is_dir() else []
    note_names = collect_note_names(notes)
    for note in notes:
        errors.extend(validate_note(note, note_names))

    para_notes = [note for note in notes if is_para_note(note)]
    stem_counts = Counter(note.stem for note in para_notes)
    errors.extend(
        f"note id {stem!r} is used by {count} notes"
        for stem, count in stem_counts.items()
        if count > 1
    )

    if errors:
        print(f"FAIL: {len(errors)} problem(s) in brain/")
        for error in errors:
            print(f"  - {error}")
        return 1

    print(
        f"OK: {len(notes)} file(s) checked, all wikilinks resolve, "
        f"{len(para_notes)} note(s) match the frontmatter schema"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
