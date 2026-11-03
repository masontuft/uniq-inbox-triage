# UNIQ Supply · Inbox Triage

Sorts, prioritizes, quotes, and drafts replies for the UNIQ Supply inbox, and flags what the owner must handle.
Paste in tomorrow's `inbox.csv` and run it again.

## Run it

```bash
cp .env.example .env        # then fill in LLM_API_KEY (any OpenAI-compatible provider: Groq, xAI, Gemini, OpenAI)
python3 triage.py --list-models          # pick a model id, put it in .env as LLM_MODEL
python3 triage.py data/inbox.csv --today 2027-03-08
```

Outputs in `out/`: `results.csv` (the six required columns), `results.json` (plus extracted facts), and
`report.html` (priority-sorted view for the owner). Python 3.10+ standard library only, no installs.

Useful flags: `--only E05,E16` to rerun specific emails, `--orders` and `--kb` to point at updated files,
`--today` to set the "current" date (defaults to the real date).

## How it works

```
email ─▶ LLM pass 1: extract facts + classify (JSON)
           │
           ├─▶ pricing.py   deterministic quote: picks valid production paths, exact math, lead-time vs deadline
           ├─▶ orders.py    order history for the sender (tracking, prior designs, delivery dates)
           └─▶ decide()     KB section 6 escalation rules + priority floors, enforced in code
                    │
                    ▼
         LLM pass 2: draft reply from the computed facts only ─▶ guard_draft() sanity checks ─▶ CSV / JSON / HTML
```

Design choices:

- **The LLM never does pricing math.** It extracts size, quantity, colors, Pantone needs, and deadline; `pricing.py`
  computes every total and picks the path. Quotes are reproducible and auditable.
- **Escalation rules are code, not prompt.** The model reports facts (sentiment, requests, phishing signals); the
  $5,000 threshold, rush/deadline, terms, lower-48, and custom-complaint rules are `if` statements it can't talk
  its way around.
- **Email bodies are untrusted.** Both prompts wrap the email in `<email>` tags as data. A regex backstop catches
  "note to the AI" style injections even if the model misses them; injected requests (e.g. a fake 40% discount)
  are dropped, never honored or acknowledged.
- **Fails safe.** If one email errors, it's marked P2 "handle manually" and the batch continues. A bad API key
  stops the run once with a clear message.

## Files

| File | Purpose |
|---|---|
| `triage.py` | CLI, prompts, escalation rules, output |
| `pricing.py` | Custom-cup pricing engine (KB section 1) |
| `orders.py` | Order-history lookup by sender |
| `llm.py` | Stdlib OpenAI-compatible client, `.env` loader |
| `report.py` | HTML report |
| `data/` | Knowledge base, orders, inbox |
