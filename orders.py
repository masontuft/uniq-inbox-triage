"""Order-history lookup so replies can cite real orders instead of guessing."""
from __future__ import annotations

import csv
from pathlib import Path


def load_orders(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def orders_for(sender_email: str, orders: list[dict]) -> list[dict]:
    """Exact email match first; fall back to same company domain."""
    email = sender_email.strip().lower()
    exact = [o for o in orders if o["customer_email"].lower() == email]
    if exact:
        return exact
    domain = email.rsplit("@", 1)[-1]
    free_mail = {"gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "icloud.com", "aol.com"}
    if domain in free_mail:
        return []
    return [o for o in orders if o["customer_email"].lower().endswith("@" + domain)]


def format_orders(rows: list[dict]) -> str:
    if not rows:
        return "No order history on file for this sender."
    keys = ["order_id", "order_date", "order_type", "items", "production_path", "order_total",
            "status", "ship_date", "delivered_date", "carrier", "tracking", "notes"]
    return "\n".join("; ".join(f"{k}={r[k]}" for k in keys if r.get(k)) for r in rows)
