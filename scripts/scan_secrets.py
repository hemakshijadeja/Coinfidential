"""Scan the repository for committed secrets.

Scans tracked files, plus untracked files that Git does not ignore, so a secret
is caught before it is staged. It reports the file, line and rule, but never
prints the matched value. It checks the current files only, not Git history.

Exits with status 0 if nothing is found, or 1 if a secret is found or the scan
cannot run.
"""

import re
import subprocess
import sys
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parent.parent

SECRET_PATTERNS = {
    "AWS access key": re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"),
    "GitHub token": re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{22,})\b"),
    "Anthropic API key": re.compile(r"\bsk-ant-[A-Za-z0-9_-]{20,}"),
    "OpenAI API key": re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{32,}"),
    "Google API key": re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b"),
    "Slack token": re.compile(r"\bxox[abeoprs]-[A-Za-z0-9-]{10,}"),
    "Stripe live key": re.compile(r"\b[rs]k_live_[A-Za-z0-9]{16,}"),
    "Private key": re.compile(r"-----BEGIN (?:[A-Z0-9]+ )*PRIVATE KEY-----"),
    "JSON Web Token": re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"),
}

# Matches assignments such as API_KEY="abc..." or client_secret: abc...
# The value must end the line or expression, which skips code like
# `token = load_the_token_from_settings(path)`.
SECRET_ASSIGNMENT = re.compile(
    r"""[\w-]*(?:api[_-]?key|secret|token|password|passwd|access[_-]?key)[\w-]*["']?"""
    r"""\s*[:=]\s*["']?(?P<value>[A-Za-z0-9_/+=-]{16,})["']?\s*(?:[,;#)}]|$)""",
    re.IGNORECASE,
)
PLACEHOLDER_WORDS = ("example", "placeholder", "changeme", "your", "dummy", "xxxx")

# Filename rules for files that should never be in the repository.
SECRET_FILENAME = re.compile(r"\.env(\..+)?|.+\.(pem|key|p12|pfx)|id_(rsa|dsa|ecdsa|ed25519)")
ALLOWED_FILENAMES = (".env.example", ".env.sample", ".env.template")


def list_repository_files() -> list[str]:
    """Return tracked and non-ignored untracked files, relative to the root."""
    result = subprocess.run(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT,
        capture_output=True,
        check=True,
    )
    paths = result.stdout.decode("utf-8").split("\0")
    return sorted({path for path in paths if path})


def is_placeholder(value: str) -> bool:
    lowered = value.lower()
    return any(word in lowered for word in PLACEHOLDER_WORDS)


def find_secrets_in_line(line: str) -> list[str]:
    """Return the names of the rules that match a line."""
    rules = [name for name, pattern in SECRET_PATTERNS.items() if pattern.search(line)]
    assignment = SECRET_ASSIGNMENT.search(line)
    if assignment and not is_placeholder(assignment.group("value")):
        rules.append("Secret assignment")
    return rules


def scan_file(relative_path: str) -> list[str]:
    """Return the findings for one file."""
    findings = []
    filename = PurePosixPath(relative_path).name
    if SECRET_FILENAME.fullmatch(filename) and filename not in ALLOWED_FILENAMES:
        findings.append(f"{relative_path}: this type of file must not be in the repository")

    path = ROOT / relative_path
    # A tracked file can be deleted from disk but not yet from the index.
    if not path.is_file():
        return findings

    data = path.read_bytes()
    if b"\0" in data:  # Binary file.
        return findings

    text = data.decode("utf-8", errors="ignore")
    for line_number, line in enumerate(text.splitlines(), start=1):
        for rule in find_secrets_in_line(line):
            findings.append(f"{relative_path}:{line_number}: {rule}")
    return findings


def main() -> int:
    try:
        files = list_repository_files()
    except (OSError, subprocess.CalledProcessError) as error:
        print(f"FAIL: could not list repository files with Git: {error}")
        return 1

    if not files:
        print("FAIL: Git listed no files to scan")
        return 1

    findings = [finding for path in files for finding in scan_file(path)]
    if findings:
        print(f"FAIL: {len(findings)} possible secret(s) found")
        for finding in findings:
            print(f"  - {finding}")
        return 1

    print(f"OK: {len(files)} file(s) scanned, no secrets found")
    return 0


if __name__ == "__main__":
    sys.exit(main())
