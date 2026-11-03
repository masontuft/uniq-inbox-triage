# submission/

What gets sent back for the challenge. This folder is intentionally empty in the repo: the results quote the
challenge emails, so they're gitignored and never committed.

## Populate it

1. Fill `data/` (see `data/README.md`) and `.env` (see `.env.example`).
2. Run the tool: `python3 triage.py --today 2027-03-08`. It writes three files to `out/`.
3. Copy the two deliverables here:

   ```bash
   cp out/results.csv out/report.html submission/
   ```

   - `results.csv`: one row per email with the six required columns (`email_id, category, priority,
     needs_human, quote, draft_reply`).
   - `report.html`: the same results as a priority-sorted page for the owner. Open it in any browser.

4. Read every draft before sending anything. The tool flags what the owner must handle, but a human reviews
   every reply.
