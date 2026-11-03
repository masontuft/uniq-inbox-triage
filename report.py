"""Render out/results.json as a single self-contained HTML page, sorted for the owner.

Usage: python3 report.py [out/results.json] [out/report.html]
"""
from __future__ import annotations

import html
import json
import sys
from pathlib import Path

PRIORITY_LABEL = {"P1": "Owner today", "P2": "Reply today", "P3": "Within 1 day", "P4": "No reply"}


def card(r: dict) -> str:
    f = r.get("facts", {})
    human = r["needs_human"].startswith("Yes")
    quote = f'<div class="quote"><b>Quote</b><p>{html.escape(r["quote"])}</p></div>' if r["quote"] else ""
    err = f'<p class="err">Error: {html.escape(r["error"])}</p>' if r.get("error") else ""
    return f"""<details class="card {r['priority']}" {"open" if r['priority'] == "P1" else ""}>
<summary><span class="pill {r['priority']}">{r['priority']} · {PRIORITY_LABEL.get(r['priority'], '')}</span>
<span class="id">{r['email_id']}</span><span class="cat">{html.escape(f.get('category', ''))}</span>
<span class="sum">{html.escape(f.get('summary', '') or '')}</span>
{'<span class="flag">Owner</span>' if human else ''}</summary>
<p class="human {'yes' if human else 'no'}">{html.escape(r['needs_human'])}</p>{err}{quote}
<div class="draft"><b>Draft reply</b><pre>{html.escape(r['draft_reply'])}</pre></div>
</details>"""


def render(results: list[dict]) -> str:
    results = sorted(results, key=lambda r: (r["priority"], r["email_id"]))
    counts = {p: sum(r["priority"] == p for r in results) for p in PRIORITY_LABEL}
    owner = sum(r["needs_human"].startswith("Yes") for r in results)
    stats = "".join(f'<div class="stat {p}"><b>{counts[p]}</b>{p} · {PRIORITY_LABEL[p]}</div>' for p in PRIORITY_LABEL)
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>UNIQ Inbox Triage</title>
<style>
:root{{--bg:#f7f7f9;--card:#fff;--ink:#1d2433;--muted:#667085;--line:#e4e7ec;--p1:#d92d20;--p2:#dc6803;--p3:#1570ef;--p4:#98a2b3}}
@media (prefers-color-scheme:dark){{:root{{--bg:#0f1218;--card:#181c25;--ink:#e6e9ef;--muted:#98a2b3;--line:#2a303c}}}}
body{{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 system-ui,sans-serif}}
main{{max-width:960px;margin:0 auto;padding:24px 16px}}
h1{{margin:0 0 4px}} .sub{{color:var(--muted);margin:0 0 20px}}
.stats{{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:10px;margin-bottom:20px}}
.stat{{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:10px 12px;color:var(--muted)}}
.stat b{{display:block;font-size:24px;color:var(--ink)}}
.card{{background:var(--card);border:1px solid var(--line);border-left:4px solid var(--p4);border-radius:10px;margin:10px 0;padding:10px 14px}}
.card.P1{{border-left-color:var(--p1)}} .card.P2{{border-left-color:var(--p2)}} .card.P3{{border-left-color:var(--p3)}}
summary{{cursor:pointer;display:flex;flex-wrap:wrap;gap:8px;align-items:center}}
.pill{{font-size:12px;font-weight:600;color:#fff;border-radius:99px;padding:2px 8px;background:var(--p4)}}
.pill.P1{{background:var(--p1)}} .pill.P2{{background:var(--p2)}} .pill.P3{{background:var(--p3)}}
.id{{font-weight:700}} .cat{{color:var(--muted)}} .sum{{flex-basis:100%}}
.flag{{font-size:12px;border:1px solid var(--p1);color:var(--p1);border-radius:99px;padding:1px 8px}}
.human.yes{{color:var(--p1)}} .human.no{{color:var(--muted)}} .err{{color:var(--p1)}}
.quote p{{margin:4px 0 10px}} pre{{white-space:pre-wrap;font:inherit;background:var(--bg);border-radius:8px;padding:10px;margin:4px 0}}
</style></head><body><main>
<h1>UNIQ Supply · Inbox Triage</h1>
<p class="sub">{len(results)} emails · {owner} flagged for the owner · sorted by priority</p>
<div class="stats">{stats}</div>
{''.join(card(r) for r in results)}
</main></body></html>"""


def main() -> None:
    src = Path(sys.argv[1] if len(sys.argv) > 1 else "out/results.json")
    dst = Path(sys.argv[2] if len(sys.argv) > 2 else src.with_name("report.html"))
    dst.write_text(render(json.loads(src.read_text(encoding="utf-8"))), encoding="utf-8")
    print(f"Wrote {dst}")


if __name__ == "__main__":
    main()
