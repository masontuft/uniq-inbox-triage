# data/

Input files for the triage tool. This folder is intentionally empty in the repo: the challenge packet is
confidential, so its files are gitignored and never committed.

## Populate it

Copy these three files from the UNIQ AI Intern Challenge packet into this folder:

| File | What it is | Required columns |
|---|---|---|
| `inbox.csv` | The emails to triage | `email_id, received_at, from_name, from_email, subject, body` |
| `orders.csv` | Recent order history, used for status, reorders, and returns | `order_id, customer_name, customer_email, order_date, order_type, items, production_path, order_total, status, ship_date, delivered_date, carrier, tracking, notes` |
| `knowledge_base.md` | Pricing, policies, escalation rules, and brand voice | (Markdown) |

Then run from the repo root:

```bash
python3 triage.py --today 2027-03-08
```

To use files somewhere else instead, pass paths: `python3 triage.py path/to/inbox.csv --orders path/to/orders.csv --kb path/to/knowledge_base.md`.
CSV files exported from Excel or Google Sheets with a byte-order mark are fine.
