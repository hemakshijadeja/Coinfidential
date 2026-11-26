---
name: local-check
description: Runs a quick local check before a pull request. Compiles the code, runs pytest, starts the server with uvicorn, calls GET /health, stops the server and prints PASS or FAIL for each step. Use when asked to check, smoke test or verify the project locally. Works on Windows.
---

# Local Check

Run these steps from the repo root in PowerShell. Run every step even if an earlier one fails, then print the results.

Keeping the server check separate from the tests follows the idea in [[provider-interface-isolation]]: tests use their own isolated setup, and this skill checks that the real app also starts.

## Steps

1. Compile:

   ```powershell
   python -m compileall -q app scripts tests
   ```

   PASS if the exit code is 0.

2. Tests:

   ```powershell
   python -m pytest
   ```

   PASS if the exit code is 0. Use `python -m pytest`, not `pytest`, because `pytest` is often not on PATH on Windows.

3. Start the server in the background and wait for it:

   ```powershell
   $server = Start-Process python -ArgumentList "-m uvicorn app.main:app --port 8000" -PassThru -WindowStyle Hidden
   Start-Sleep -Seconds 3
   ```

   PASS if `$server.HasExited` is `False`.

4. Call the health endpoint:

   ```powershell
   Invoke-RestMethod http://127.0.0.1:8000/health
   ```

   PASS if it returns `status` equal to `ok`. If port 8000 is busy, use another port in steps 3 and 4.

5. Stop the server:

   ```powershell
   Stop-Process -Id $server.Id -Force
   ```

   PASS if the process is gone afterwards.

## Report

Print one line per step, for example:

```
compile  PASS
pytest   PASS
server   PASS
health   PASS
stop     PASS
```

If a step fails, show the error under its line. Do not fix code, commit or push. Only report.
