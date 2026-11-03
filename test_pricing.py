"""Pricing engine tests. Expected totals are hand-checked against knowledge_base.md section 1.

Run: python3 -m unittest -v
"""
import unittest
from datetime import date
from decimal import Decimal as D

from pricing import QuoteRequest as Q, quote_custom

TODAY = date(2027, 3, 8)  # scenario Monday; proof assumed approved Tue Mar 9


def rec(req):
    return quote_custom(req, TODAY).recommended


class PathSelection(unittest.TestCase):
    def test_pms_rules_out_digital(self):
        # E01: 20k 8oz, 2 PMS colors -> USA partner, 20,000 x .115 + 2 x $150 = $2,600, free freight.
        r = rec(Q(8, 20_000, 2, needs_pms=True, deadline=date(2027, 4, 15)))
        self.assertEqual(r.path, "USA partner (flexo)")
        self.assertEqual(r.total, D("2600"))
        self.assertEqual(r.shipping, 0)
        self.assertEqual(r.deadline_fit, "yes")

    def test_small_full_color_goes_digital_with_flat_freight(self):
        # E02: 3,000 x 12oz gradient -> digital, 3,000 x .26 = $780 + $95.
        r = rec(Q(12, 3_000, full_color=True, deadline=date(2027, 3, 27)))
        self.assertEqual(r.path, "In-house digital")
        self.assertEqual(r.total, D("875"))

    def test_deadline_beats_cheapest(self):
        # E03: overseas is cheaper ($10,900) but lands after May 1, so USA ($16,650) wins.
        res = quote_custom(Q(16, 150_000, 2, needs_pms=True, deadline=date(2027, 5, 1)), TODAY)
        self.assertEqual(res.recommended.path, "USA partner (flexo)")
        self.assertEqual(res.recommended.total, D("16650"))
        overseas = next(o for o in res.options if o.path.startswith("Overseas"))
        self.assertEqual(overseas.total, D("10900"))
        self.assertEqual(overseas.deadline_fit, "no")

    def test_no_path_offers_nearest_fits(self):
        # E04: 5,000 x 16oz fits nothing; suggest 12oz digital ($1,395) or 10k USA ($1,665).
        res = quote_custom(Q(16, 5_000, 1), TODAY)
        self.assertIsNone(res.recommended)
        joined = " ".join(res.notes)
        self.assertIn("$1,395.00", joined)
        self.assertIn("$1,665.00", joined)


class Extras(unittest.TestCase):
    def test_third_color_and_rush_exclude_setup(self):
        # E05: 60k 8oz 3 colors -> 5,340 + 600 + 450 = $6,390; rush adds 15% of 5,940 = $891.
        r = rec(Q(8, 60_000, 3, deadline=date(2027, 4, 5)))
        self.assertEqual(r.total, D("6390"))
        self.assertEqual(r.deadline_fit, "tight")
        self.assertEqual(r.rush.total, D("7281"))

    def test_unchanged_reorder_waives_setup(self):
        # E18: 2 x 25,000 = 50,000 at the 50k tier, plates on file -> $4,450.
        r = rec(Q(8, 50_000, 2, deadline=date(2027, 4, 15), reorder_design_path="USA partner (flexo)"))
        self.assertEqual(r.total, D("4450"))

    def test_outside_lower48_leaves_shipping_to_owner(self):
        # E12: Canada -> no freight rate, total stays open.
        r = rec(Q(12, 30_000, None, lower48=False))
        self.assertIsNone(r.total)
        self.assertIsNone(r.shipping)

    def test_free_freight_threshold_includes_setup(self):
        # 12k 8oz 1 color = 1,380 + 150 = 1,530 < 2,500 -> $95 freight.
        self.assertEqual(rec(Q(8, 12_000, 1)).total, D("1625"))


if __name__ == "__main__":
    unittest.main()
