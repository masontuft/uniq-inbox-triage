"""Deterministic custom-cup pricing for UNIQ Supply.

Every number here comes from knowledge_base.md section 1. The LLM never does
this math: it extracts the order details, and quote_custom() picks the valid
production paths and computes the totals.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal as D

DIGITAL_PRICE = {8: D("0.22"), 12: D("0.26")}
# Tiers are checked top-down, so list the highest minimum first.
USA_TIERS = [
    (50_000, {8: D("0.089"), 12: D("0.099"), 16: D("0.109")}),
    (25_000, {8: D("0.098"), 12: D("0.110"), 16: D("0.121")}),
    (10_000, {8: D("0.115"), 12: D("0.128"), 16: D("0.142")}),
]
OVERSEAS_TIERS = [
    (100_000, {8: D("0.055"), 12: D("0.063"), 16: D("0.070")}),
    (50_000, {8: D("0.062"), 12: D("0.071"), 16: D("0.079")}),
]
USA_EXTRA_COLOR = D("0.010")
USA_PLATE_PER_COLOR = D("150")
OVERSEAS_SETUP = D("400")
RUSH_UPCHARGE = D("0.15")
FREE_FREIGHT_MIN = D("2500")
FLAT_FREIGHT = D("95")


def money(x: D) -> str:
    return f"${x:,.2f}"


def add_business_days(start: date, n: int) -> date:
    d = start
    while n > 0:
        d += timedelta(days=1)
        if d.weekday() < 5:
            n -= 1
    return d


def next_business_day(d: date) -> date:
    return add_business_days(d, 1)


@dataclass
class PathOption:
    path: str
    eligible: bool
    why_not: list[str] = field(default_factory=list)
    lines: list[tuple[str, D]] = field(default_factory=list)
    subtotal: D = D("0")
    shipping: D | None = None
    total: D | None = None
    lead_time: str = ""
    ready: tuple[date, date] | None = None
    deadline_fit: str = "n/a"  # yes | tight | no | n/a
    rush: "PathOption | None" = None

    def math(self) -> str:
        parts = [f"{label} = {money(amt)}" for label, amt in self.lines]
        ship = "shipping TBD by owner" if self.shipping is None else (
            "free freight" if self.shipping == 0 else f"shipping {money(self.shipping)}")
        total = money(self.total) if self.total is not None else money(self.subtotal) + " + shipping TBD"
        return f"{self.path}: " + "; ".join(parts) + f"; {ship}; total {total}"


@dataclass
class QuoteRequest:
    size_oz: int
    quantity: int
    ink_colors: int | None = None  # spot colors; None = not stated
    full_color: bool = False  # gradients/photos/CMYK
    needs_pms: bool = False
    deadline: date | None = None  # date the customer needs cups in hand
    lower48: bool | None = True  # None = unknown destination
    reorder_design_path: str | None = None  # path of an unchanged prior design on file


@dataclass
class QuoteResult:
    request: QuoteRequest
    options: list[PathOption]
    recommended: PathOption | None
    notes: list[str]
    proof_date: date | None = None

    def summary(self) -> str:
        if not self.recommended:
            return "No production path fits this request. " + " ".join(self.notes)
        rec = self.recommended
        out = [f"Recommended: {rec.math()}. Lead time {rec.lead_time}."]
        if rec.ready:
            out.append(f"Production complete {rec.ready[0]:%b %-d}-{rec.ready[1]:%b %-d} if proof approved "
                       f"{self.proof_date:%b %-d}" + (f"; customer deadline {self.request.deadline:%b %-d}, "
                                                      f"fit: {rec.deadline_fit}." if self.request.deadline else "."))
        if self.recommended.rush:
            out.append(f"Rush option (owner must confirm): {self.recommended.rush.math()}.")
        for o in self.options:
            if o is not self.recommended and o.eligible:
                out.append(f"Alternative: {o.math()} ({o.lead_time}, deadline fit: {o.deadline_fit}).")
        out.extend(self.notes)
        return " ".join(out)


def _tier_price(tiers, qty: int, size: int) -> D | None:
    for minimum, prices in tiers:
        if qty >= minimum:
            return prices.get(size)
    return None


def _fit(ready: tuple[date, date], deadline: date | None) -> str:
    if deadline is None:
        return "n/a"
    earliest, latest = ready
    if latest <= deadline:
        return "yes"
    if earliest <= deadline:
        return "tight"
    return "no"


def _shipping(opt: PathOption, lower48: bool | None) -> None:
    if lower48 is False:
        opt.shipping, opt.total = None, None
        return
    opt.shipping = D("0") if opt.subtotal >= FREE_FREIGHT_MIN else FLAT_FREIGHT
    opt.total = opt.subtotal + opt.shipping


def _digital(r: QuoteRequest, proof: date) -> PathOption:
    o = PathOption("In-house digital", True, lead_time="7-10 business days after proof approval")
    if r.size_oz not in DIGITAL_PRICE:
        o.why_not.append(f"no {r.size_oz} oz (8 and 12 oz only)")
    if not 1_000 <= r.quantity <= 9_999:
        o.why_not.append("quantity must be 1,000-9,999")
    elif r.quantity % 1_000:
        o.why_not.append("quantity must be a multiple of 1,000")
    if r.needs_pms:
        o.why_not.append("no Pantone (PMS) guarantee, close match only")
    if o.why_not:
        o.eligible = False
        return o
    unit = DIGITAL_PRICE[r.size_oz]
    o.lines = [(f"{r.quantity:,} x {money(unit)} ({r.size_oz} oz, full color)", r.quantity * unit)]
    o.subtotal = o.lines[0][1]
    o.ready = (add_business_days(proof, 7), add_business_days(proof, 10))
    return o


def _usa(r: QuoteRequest, proof: date) -> PathOption:
    o = PathOption("USA partner (flexo)", True, lead_time="3-4 weeks after proof approval")
    if r.quantity < 10_000:
        o.why_not.append("minimum 10,000 cups")
    elif r.quantity % 1_000:
        o.why_not.append("quantity must be a multiple of 1,000")
    if r.full_color:
        o.why_not.append("flexo prints spot colors (max 4), not full color/gradients")
    if r.ink_colors is not None and r.ink_colors > 4:
        o.why_not.append("maximum 4 ink colors")
    if o.why_not:
        o.eligible = False
        return o
    colors = r.ink_colors or 2
    unit = _tier_price(USA_TIERS, r.quantity, r.size_oz)
    cups = r.quantity * unit
    o.lines.append((f"{r.quantity:,} x ${unit} ({r.size_oz} oz)", cups))
    extra = max(colors - 2, 0)
    if extra:
        o.lines.append((f"{extra} extra color(s) x $0.010 x {r.quantity:,}", r.quantity * USA_EXTRA_COLOR * extra))
    if r.reorder_design_path == o.path:
        o.lines.append(("setup waived (unchanged reorder, plates on file)", D("0")))
    else:
        o.lines.append((f"setup {colors} color(s) x $150", USA_PLATE_PER_COLOR * colors))
    o.subtotal = sum((amt for _, amt in o.lines), D("0"))
    o.ready = (proof + timedelta(weeks=3), proof + timedelta(weeks=4))
    # Rush: +15% on cup cost (cups + extra-color charge), never on setup. Owner-only.
    cup_cost = sum((amt for label, amt in o.lines if not label.startswith("setup")), D("0"))
    rush = PathOption("USA partner 2-week RUSH", True, lead_time="~2 weeks after proof approval, owner must confirm")
    rush.lines = o.lines + [(f"rush +15% x {money(cup_cost)} cup cost", cup_cost * RUSH_UPCHARGE)]
    rush.subtotal = sum((amt for _, amt in rush.lines), D("0"))
    rush.ready = (proof + timedelta(weeks=2), proof + timedelta(weeks=2))
    o.rush = rush
    return o


def _overseas(r: QuoteRequest, proof: date) -> PathOption:
    o = PathOption("Overseas (offset)", True, lead_time="10-12 weeks after proof approval, incl. ocean freight")
    if r.quantity < 50_000:
        o.why_not.append("minimum 50,000 cups")
        o.eligible = False
        return o
    unit = _tier_price(OVERSEAS_TIERS, r.quantity, r.size_oz)
    o.lines.append((f"{r.quantity:,} x ${unit} ({r.size_oz} oz, full color)", r.quantity * unit))
    waived = r.reorder_design_path == o.path
    o.lines.append(("setup waived (unchanged reorder)" if waived else "setup $400 flat", D("0") if waived else OVERSEAS_SETUP))
    o.subtotal = sum((amt for _, amt in o.lines), D("0"))
    o.ready = (proof + timedelta(weeks=10), proof + timedelta(weeks=12))
    return o


def quote_custom(r: QuoteRequest, today: date) -> QuoteResult:
    proof = next_business_day(today)  # assumption: proof approved next business day
    notes = [f"Dates assume proof approval on {proof:%b %-d}; transit time for digital/USA orders is extra."]
    options = [_digital(r, proof), _usa(r, proof), _overseas(r, proof)]
    for o in options:
        if not o.eligible:
            continue
        _shipping(o, r.lower48)
        o.deadline_fit = _fit(o.ready, r.deadline)
        if o.rush:
            _shipping(o.rush, r.lower48)
            o.rush.deadline_fit = _fit(o.rush.ready, r.deadline)
    eligible = [o for o in options if o.eligible]
    rank = {"yes": 0, "n/a": 0, "tight": 1, "no": 2}
    # Prefer paths that meet the deadline, then the cheapest.
    recommended = min(eligible, key=lambda o: (rank[o.deadline_fit], o.subtotal), default=None)
    # Only surface the rush when standard lead time misses the deadline and rush would make it.
    for o in eligible:
        if o.rush and (o.deadline_fit in ("yes", "n/a") or o.rush.deadline_fit == "no"):
            o.rush = None
    if r.ink_colors is None and any(o.path.startswith("USA") for o in eligible):
        notes.append("Ink color count not stated; USA partner priced at 2 colors.")
    if r.lower48 is False:
        notes.append("Ships outside the lower 48: no standard freight rate, owner must quote shipping.")
    elif r.lower48 is None:
        notes.append("Destination not stated; shipping assumes lower 48.")
    if not eligible:
        notes.extend(f"{o.path}: {', '.join(o.why_not)}." for o in options)
        notes.extend(_nearest_fits(r, today))
    return QuoteResult(r, options, recommended, notes, proof)


def _nearest_fits(r: QuoteRequest, today: date) -> list[str]:
    """When nothing fits, price the closest requests that do: smaller size, or the next minimum."""
    tries = []
    if r.size_oz == 16 and r.quantity < 10_000:
        tries.append(("Closest fit, 12 oz instead of 16 oz", QuoteRequest(**{**r.__dict__, "size_oz": 12})))
    if r.quantity < 10_000:
        tries.append(("Closest fit, raise to the 10,000 minimum", QuoteRequest(**{**r.__dict__, "quantity": 10_000})))
    out = []
    for label, alt in tries:
        res = quote_custom(alt, today)
        if res.recommended:
            out.append(f"{label}: {res.recommended.math()} ({res.recommended.lead_time}).")
    return out
