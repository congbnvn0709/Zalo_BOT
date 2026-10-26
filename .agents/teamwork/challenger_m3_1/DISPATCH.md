## 2026-10-26T09:31:00Z
**Sender**: 9d3ef6c5-77d3-42b3-adab-c1e95bee7211
**Priority**: MESSAGE_PRIORITY_HIGH

You are Web API Adversarial Challenger 1 for Milestone 3.
Your working directory is: /Users/congcm/CODE/Vibe_Code/Zalo_BOT/.agents/teamwork/challenger_m3_1/

MANDATORY FIRST STEPS:
1. Read /Users/congcm/CODE/Vibe_Code/Zalo_BOT/.agents/teamwork/ORIGINAL_REQUEST.md.
2. Read /Users/congcm/CODE/Vibe_Code/Zalo_BOT/PROJECT.md.

Task: Empirically stress-test FastAPI endpoints in main.py and api/routes.py.
1. Write adversarial test scripts in your working directory to challenge:
   - Fuzzing /api/parse: 100,000-character payload, non-UTF8 / corrupt string encodings, malformed JSON structures, empty string {"text": ""}, null values.
   - Concurrency / Race Conditions on /api/export-excel: simulate concurrent export requests, verify each receives unique download token and produces intact non-colliding Excel files in output/.
   - Token Traversal / Security on /api/download/{token}: directory traversal attempts like ../../etc/passwd, non-existent uuid, expired/random strings.
   - Custom Template Upload: upload 0-byte file, upload .exe or .txt renamed to .xlsx, upload corrupt zip file.
2. Assert zero 500 unhandled crashes and appropriate 400/404/422 status codes.
3. Record verdict: APPROVE or REJECT in /Users/congcm/CODE/Vibe_Code/Zalo_BOT/.agents/teamwork/challenger_m3_1/handoff.md.
Send a completion message back to parent.
