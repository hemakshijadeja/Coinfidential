# Coinfidential

A Financial Ledger & Digital Wallet RESTful API built with FastAPI and SQLite, using strict double-entry bookkeeping.

**Status:** Stage 1 (Requirements). Only the `/health` endpoint exists so far. Ledger and wallet features are not implemented yet.

## Setup

Requires Python 3.12.

```
python -m venv .venv
```

Activate the environment:

- Windows (PowerShell): `.venv\Scripts\Activate.ps1`
- macOS or Linux: `source .venv/bin/activate`

Install the dependencies:

```
pip install -r requirements.txt
```

## Run the API

```
uvicorn app.main:app --reload
```

Then check `http://127.0.0.1:8000/health`, which returns `{"status": "ok"}`.

## Run the checks

CI runs the same checks on every push and pull request:

```
python -m compileall -q app scripts tests
ruff check .
pytest
python scripts/scan_secrets.py
python scripts/validate_skills.py
python scripts/validate_brain.py
```

## Build the SRS PDF

```
python scripts/generate_srs_pdf.py
```

This writes `SRS_Stage1_Submission.pdf` to the repository root. It is ignored by Git, so upload it to the submission portal directly.

## Evaluate the brain-ingest skill

```
python scripts/evaluate_brain_ingest.py
```

The results are recorded in Section 6.3 of the SRS.

Detailed design, such as SQL and exact API schemas, belongs in the Stage 2 design documents. The SRS states the requirements.

## Repository layout

| Path | Contents |
| --- | --- |
| `app/` | FastAPI application |
| `tests/` | Test suite |
| `scripts/` | CI validation scripts |
| `docs/` | Software Requirements Specification (`SRS.md`) |
| `brain/` | Second Brain project notes, organized with PARA |
| `.claude/skills/` | Agent Skills |
| `AGENTS.md` | Project rules for contributors and AI agents |
