"""Evaluate the brain-ingest skill for TQ-7.

Part A audits every research note in brain/ against the rules in the skill's
SKILL.md. Part B copies the brain to a temporary folder, injects one fault at a
time, and records whether scripts/validate_brain.py catches it.

This checks the notes the skill produced and the validators that guard them. It
does not compare output with and without the skill.

Exits with status 0 if every assertion and expected detection holds, or 1 if not.
"""

import re
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
BRAIN_DIR = ROOT / "brain"

TEMPLATE_HEADINGS = (
    "Summary",
    "Key points",
    "Relevance to Coinfidential",
    "Requirements",
    "Related notes",
    "Open questions",
)
REQUIRED_FIELDS = ("id", "title", "type", "author", "stage", "related_requirements")
REQUIREMENT_LINK = re.compile(r"\[\[((?:FR|NFR|SK|TQ|SB|SE)-\d+)\]\]")
NOTE_LINK = re.compile(r"\[\[([a-z0-9-]+)(?:[|#][^\]]*)?\]\]")
FRONTMATTER = re.compile(r"\A---\n(.*?)^---\n", re.DOTALL | re.MULTILINE)
# The highest ID in each series, from the course documents and docs/SRS.md.
SERIES_LIMITS = {"FR": 5, "NFR": 8, "SK": 5, "TQ": 8, "SB": 6, "SE": 7}
INFERENCE_LABEL = re.compile(r"recommend|inference|my own", re.IGNORECASE)


def section(body: str, heading: str) -> str:
    match = re.search(rf"^## {re.escape(heading)}\n(.*?)(?=^## |\Z)", body, re.DOTALL | re.MULTILINE)
    return match.group(1) if match else ""


def in_range(requirement: str) -> bool:
    series, number = requirement.split("-")
    return 1 <= int(number) <= SERIES_LIMITS[series]


def audit_note(note: Path, index_text: str, log_text: str, note_stems: set[str]) -> dict[str, bool]:
    text = note.read_text(encoding="utf-8")
    match = FRONTMATTER.match(text)
    frontmatter = yaml.safe_load(match.group(1)) if match else {}
    body = text[match.end() :] if match else text
    headings = re.findall(r"^## (.+)$", body, re.MULTILINE)
    linked = set(REQUIREMENT_LINK.findall(body))
    listed = set(frontmatter.get("related_requirements") or [])
    related = {link for link in NOTE_LINK.findall(section(body, "Related notes")) if link != note.stem}
    index_resources = section(index_text, "Resources")
    log_added = "\n".join(line for line in log_text.splitlines() if line.startswith("- Notes added:"))

    return {
        "A1 required frontmatter fields": all(field in frontmatter for field in REQUIRED_FIELDS),
        "A2 id matches filename": frontmatter.get("id") == note.stem,
        "A3 type is research, author set": frontmatter.get("type") == "research"
        and str(frontmatter.get("author", "")).startswith("Member "),
        "A4 source recorded": bool(frontmatter.get("source")),
        "A5 all template headings in order": [h for h in headings if h in TEMPLATE_HEADINGS]
        == list(TEMPLATE_HEADINGS),
        "A6 frontmatter IDs equal linked IDs": linked == listed,
        "A7 all IDs exist in their series": all(in_range(item) for item in linked | listed),
        "A8 links a related note that exists": bool(related) and related <= note_stems,
        "A9 inferences are labelled": bool(INFERENCE_LABEL.search(section(body, "Relevance to Coinfidential"))),
        "A10 filed under brain/resources": note.parent.name == "resources",
        "A11 listed in index under Resources": f"[[{note.stem}]]:" in index_resources,
        "A12 recorded in log as added": f"[[{note.stem}]]" in log_added,
    }


def run_audit() -> bool:
    notes = sorted(
        path
        for path in BRAIN_DIR.rglob("*.md")
        if re.search(r"^type: research$", path.read_text(encoding="utf-8"), re.MULTILINE)
    )
    index_text = (BRAIN_DIR / "index.md").read_text(encoding="utf-8")
    log_text = (BRAIN_DIR / "log.md").read_text(encoding="utf-8")
    note_stems = {path.stem for path in BRAIN_DIR.rglob("*.md")}

    print(f"PART A: {len(notes)} research notes")
    results = {note: audit_note(note, index_text, log_text, note_stems) for note in notes}
    for note, checks in results.items():
        failed = [name for name, passed in checks.items() if not passed]
        print(f"  {'PASS' if not failed else 'FAIL'} {note.stem} ({len(checks) - len(failed)}/{len(checks)})")
        for name in failed:
            print(f"       failed: {name}")

    total = sum(len(checks) for checks in results.values())
    passed = sum(sum(checks.values()) for checks in results.values())
    print(f"  Assertions passed: {passed}/{total}")
    return passed == total


def replace_in_note(root: Path, old: str, new: str) -> None:
    note = root / "brain/resources/integer-minor-units-money-math.md"
    text = note.read_text(encoding="utf-8")
    if old not in text:
        raise ValueError(f"Fault could not be injected: {old!r} not found")
    note.write_text(text.replace(old, new, 1), encoding="utf-8")


def write_note(root: Path, relative_path: str, content: str) -> None:
    (root / relative_path).write_text(content, encoding="utf-8")


CAPTURE = "---\nid: {id}\ntitle: T\ntype: capture\nauthor: M\nstage: 1\nrelated_requirements: []\n---\n"
ID_LINE = "id: integer-minor-units-money-math"
TYPE_LINE = "type: research"
AUTHOR_LINE = "author: Member 1"
REQUIREMENTS_LINE = "related_requirements: [TQ-1, TQ-4, TQ-6, FR-5]"

# (description, fault, whether validate_brain.py should reject the result)
FAULTS: list[tuple[str, Callable[[Path], None], bool]] = [
    ("Link to a note that does not exist", lambda r: replace_in_note(r, "## Summary", "[[no-such-note]]\n## Summary"), True),
    ("Link to out-of-range FR-6", lambda r: replace_in_note(r, "## Summary", "[[FR-6]]\n## Summary"), True),
    ("Link to out-of-range SE-8", lambda r: replace_in_note(r, "## Summary", "[[SE-8]]\n## Summary"), True),
    ("Missing id", lambda r: replace_in_note(r, ID_LINE + "\n", ""), True),
    ("id differs from filename", lambda r: replace_in_note(r, ID_LINE, "id: wrong"), True),
    ("Missing author", lambda r: replace_in_note(r, AUTHOR_LINE + "\n", ""), True),
    ("Unknown type", lambda r: replace_in_note(r, TYPE_LINE, "type: blog"), True),
    ("Stage out of range", lambda r: replace_in_note(r, "stage: 1", "stage: 9"), True),
    ("related_requirements not a list", lambda r: replace_in_note(r, REQUIREMENTS_LINE, "related_requirements: TQ-1"), True),
    ("related_requirements has an unknown ID", lambda r: replace_in_note(r, REQUIREMENTS_LINE, "related_requirements: [FR-9]"), True),
    ("Frontmatter removed", lambda r: replace_in_note(r, "---\n", ""), True),
    ("Invalid YAML", lambda r: replace_in_note(r, TYPE_LINE, "type: [unclosed"), True),
    ("brain/log.md deleted", lambda r: (r / "brain/log.md").unlink(), True),
    ("brain/index.md deleted", lambda r: (r / "brain/index.md").unlink(), True),
    ("Duplicate id in two folders", lambda r: (write_note(r, "brain/areas/dup.md", CAPTURE.format(id="dup")), write_note(r, "brain/archive/dup.md", CAPTURE.format(id="dup")))[0], True),
    ("Control: no fault injected", lambda r: None, False),
    ("Control: broken link inside a code span", lambda r: replace_in_note(r, "## Summary", "`[[no-such-note]]`\n## Summary"), False),
    # Known gaps. These record what the validator does today.
    ("Known gap: out-of-range TQ-99 link", lambda r: replace_in_note(r, "## Summary", "[[TQ-99]]\n## Summary"), False),
    ("Known gap: template heading removed", lambda r: replace_in_note(r, "## Open questions", "## Other"), False),
    ("Known gap: note not listed in the index", lambda r: write_note(r, "brain/areas/orphan.md", CAPTURE.format(id="orphan")), False),
]


def run_fault_injection() -> bool:
    print(f"PART B: {len(FAULTS)} injected cases")
    all_expected = True
    for description, fault, should_reject in FAULTS:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            shutil.copytree(BRAIN_DIR, root / "brain")
            shutil.copytree(ROOT / "scripts", root / "scripts")
            fault(root)
            result = subprocess.run(
                [sys.executable, str(root / "scripts/validate_brain.py")],
                capture_output=True,
                check=False,
            )
        rejected = result.returncode != 0
        expected = rejected == should_reject
        all_expected = all_expected and expected
        outcome = "rejected" if rejected else "accepted"
        print(f"  {'OK ' if expected else 'BAD'} {outcome:8} {description}")
    return all_expected


def main() -> int:
    audit_passed = run_audit()
    faults_as_expected = run_fault_injection()
    return 0 if audit_passed and faults_as_expected else 1


if __name__ == "__main__":
    sys.exit(main())
