"""Keep docs/SRS.md consistent with its outline, requirement IDs and the brain."""

import re
from pathlib import Path

import pytest

from scripts.generate_srs_pdf import build_pdf

ROOT = Path(__file__).resolve().parent.parent
SRS = ROOT / "docs" / "SRS.md"
REQUIRED_IDS = (
    [f"FR-{n}" for n in range(1, 6)]
    + [f"NFR-{n}" for n in range(1, 9)]
    + [f"SK-{n}" for n in range(1, 6)]
    + [f"TQ-{n}" for n in range(1, 9)]
    + [f"SE-{n}" for n in range(1, 8)]
    + [f"SB-{n}" for n in range(1, 7)]
)
SERIES_LIMITS = {"FR": 5, "NFR": 8, "SK": 5, "TQ": 8, "SE": 7, "SB": 6}
# The team's IEEE outline.
OUTLINE = [
    "## 1. Introduction",
    "### 1.1 Purpose",
    "### 1.2 Document Conventions",
    "### 1.3 Intended Audience",
    "### 1.4 Product Scope",
    "### 1.5 References",
    "## 2. Overall Description",
    "### 2.1 Product Perspective",
    "### 2.2 Product Functions",
    "### 2.3 User Classes and Characteristics",
    "### 2.4 Operating Environment",
    "### 2.5 Design and Implementation Constraints",
    "### 2.6 User Documentation",
    "### 2.7 Assumptions and Dependencies",
    "## 3. External Interface Requirements",
    "### 3.1 User Interfaces",
    "### 3.2 Hardware Interfaces",
    "### 3.3 Software Interfaces",
    "### 3.4 Communications Interfaces",
    "## 4. System Features",
    "### 4.1 FR-1: Wallet Initialization",
    "### 4.2 FR-2: Idempotent Transfers",
    "### 4.3 FR-3: Concurrent Balance Mutability and Race Prevention",
    "### 4.4 FR-4: Immutable Audit Trail and Reversal Transactions",
    "### 4.5 FR-5: Ledger Reconciliation Endpoint",
    "## 5. Other Nonfunctional Requirements",
    "### 5.1 Performance Requirements",
    "### 5.2 Safety Requirements",
    "### 5.3 Security Requirements",
    "### 5.4 Software Quality Attributes",
    "## 6. Other Requirements (Course Specifics)",
    "### 6.1 Agent Skill Requirements (SK-1 to SK-5)",
    "### 6.2 Testing and Quality (TQ-1 to TQ-8)",
    "### 6.3 Stage 1 Skill Evaluation (TQ-7)",
    "### 6.4 Traceability Matrix and Task Breakdown (SE-4, SE-5)",
]


@pytest.fixture(scope="module")
def srs_text() -> str:
    return SRS.read_text(encoding="utf-8")


def section_between(text: str, start: str, end: str) -> str:
    return text.split(start, 1)[1].split(end, 1)[0]


def matrix_rows(text: str) -> dict[str, list[str]]:
    matrix = section_between(text, "#### 6.4.3", "#### 6.4.4")
    rows = [line for line in matrix.splitlines() if line.startswith("| ")]
    return {
        cells[0]: cells
        for cells in ([cell.strip() for cell in row.strip("|").split("|")] for row in rows[1:])
    }


def test_outline_matches_the_ieee_structure(srs_text: str) -> None:
    headings = re.findall(r"^#{2,3} .+$", srs_text, re.MULTILINE)

    assert headings == OUTLINE


def test_cover_page_has_title_version_and_authors(srs_text: str) -> None:
    cover = srs_text.split("## 1. Introduction", 1)[0]

    assert cover.startswith("# Coinfidential: Software Requirements Specification")
    assert "Version 1.0 approved" in cover
    for author in (
        "Aditya Bhat (BT2024035)",
        "Subhadeep Das (BT2024219)",
        "Hemakshi Jadeja (BT2024002)",
        "Hardh Kava (BT2024041)",
    ):
        assert author in cover


def test_references_link_the_repository(srs_text: str) -> None:
    references = section_between(srs_text, "### 1.5 References", "## 2. Overall Description")

    assert "https://github.com/hemakshijadeja/Coinfidential" in references


def test_wikilinks_resolve_to_brain_notes(srs_text: str) -> None:
    notes = {path.stem for path in (ROOT / "brain").rglob("*.md")}
    without_code = re.sub(r"`[^`\n]+`", "", srs_text)
    links = set(re.findall(r"\[\[([^\]|#]+)", without_code))

    assert links, "The SRS should cite brain notes"
    assert links <= notes, f"Unresolved links: {sorted(links - notes)}"


def test_requirement_ids_exist_in_their_series(srs_text: str) -> None:
    # The fault injection section names out-of-range IDs on purpose.
    before, after = srs_text.split("#### 6.3.3", 1)
    checked = before + after.split("#### 6.3.4", 1)[1]
    for series, number in re.findall(r"\b(FR|NFR|SK|TQ|SE|SB)-(\d+)\b", checked):
        assert 1 <= int(number) <= SERIES_LIMITS[series], f"{series}-{number} is out of range"


def test_traceability_matrix_covers_every_requirement(srs_text: str) -> None:
    rows = matrix_rows(srs_text)

    for requirement in [*REQUIRED_IDS, "Security Testing"]:
        assert requirement in rows, f"{requirement} is missing from the matrix"
        assert len(rows[requirement]) == 6, f"{requirement} needs 6 columns"
        assert "[[" in rows[requirement][5], f"{requirement} needs a brain note link"


def test_every_feature_uses_only_the_three_ieee_subheaders(srs_text: str) -> None:
    for number in range(1, 6):
        section = re.search(rf"^### 4\.{number} FR-{number}:.*?(?=^### |^## )", srs_text, re.DOTALL | re.MULTILINE)
        assert section, f"FR-{number} has no section"
        assert re.findall(r"^#### (.+)$", section.group(0), re.MULTILINE) == [
            f"4.{number}.1 Description and Priority",
            f"4.{number}.2 Stimulus/Response Sequences",
            f"4.{number}.3 Functional Requirements",
        ]
        for label in ("**Priority:**", "**Pre-conditions", "**Post-conditions", "**Error cases:**", "**Acceptance criteria:**"):
            assert label in section.group(0), f"FR-{number} is missing {label}"
        assert "Invariants" in section.group(0), f"FR-{number} is missing invariants"


def test_every_nonfunctional_requirement_is_in_section_five(srs_text: str) -> None:
    section = section_between(srs_text, "## 5. Other Nonfunctional Requirements", "## 6. Other Requirements")

    for number in range(1, 9):
        assert f"| NFR-{number} |" in section, f"NFR-{number} is missing from Section 5"


def test_every_endpoint_contract_requires_a_bearer_token(srs_text: str) -> None:
    contracts = section_between(srs_text, "#### 3.3.3", "#### 3.3.9")
    method_rows = re.findall(r"^\| Method and URL \| `.*$", contracts, re.MULTILINE)
    header_rows = re.findall(r"^\| Request headers \| `Authorization: Bearer <token>`.*$", contracts, re.MULTILINE)

    assert method_rows
    assert len(header_rows) == len(method_rows)
    assert "X-Admin-Key" not in srs_text


def test_amount_limit_is_adopted(srs_text: str) -> None:
    assert re.search(r"OD-5 \|.*10\^12.*\*\*Closed\*\*", srs_text)
    assert "`amount_minor` (strict integer, 1 to 10^12)" in srs_text


def test_pdf_generates(tmp_path: Path) -> None:
    output = build_pdf(SRS, tmp_path / "srs.pdf")

    assert output.read_bytes().startswith(b"%PDF")
