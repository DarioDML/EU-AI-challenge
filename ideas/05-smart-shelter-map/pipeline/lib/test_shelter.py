"""Known-answer tests for challenge.shelter (Q3). Each case has an answer worked out by hand."""
import os
import sys
import unittest

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
from challenge import shelter as sh


class CapacityTests(unittest.TestCase):
    def test_capacity_formula(self):
        # 400 m2 footprint x 2 floors x 0.5 usable / 4 m2 per person = 100 persons
        self.assertEqual(sh.capacity_persons([400], [2], 1, 0.5, 4.0)[0], 100)
        # unknown levels fall back to the default floors: 400 x 1 x 0.5 / 4 = 50
        self.assertEqual(sh.capacity_persons([400], [np.nan], 1, 0.5, 4.0)[0], 50)
        # levels ignored on request: 400 x 3 default x 0.5 / 4 = 150 even though levels = 2
        self.assertEqual(sh.capacity_persons([400], [2], 3, 0.5, 4.0, use_levels=False)[0], 150)
        # whole persons only: 10 m2 x 1 x 0.4 / 5 = 0.8 -> 0
        self.assertEqual(sh.capacity_persons([10], [None], 1, 0.4, 5.0)[0], 0)


class FlowTests(unittest.TestCase):
    def test_capacity_limits_sheltered_but_not_within_reach(self):
        r = sh.shelter_flow([[0, 0]], [100], [[500, 0]], [60], 1000)
        self.assertEqual(r["total"], 100)
        self.assertEqual(r["within_reach"], 100)      # someone is in reach...
        self.assertEqual(r["sheltered"], 60)          # ...but only 60 fit

    def test_nothing_in_reach(self):
        r = sh.shelter_flow([[0, 0]], [100], [[5000, 0]], [500], 1000)
        self.assertEqual((r["within_reach"], r["sheltered"]), (0, 0))

    def test_two_demands_share_one_shelter_without_double_counting(self):
        r = sh.shelter_flow([[0, 0], [100, 0]], [80, 80], [[50, 0]], [100], 500)
        self.assertEqual(r["within_reach"], 160)
        self.assertEqual(r["sheltered"], 100)         # the shelter is full, nobody counted twice
        self.assertAlmostEqual(r["per_demand_sheltered"].sum(), 100)

    def test_flow_routes_around_a_blocked_choice(self):
        # demand A can only reach shelter 1 (cap 50); demand B can reach shelters 1 and 2 (cap 50 each). A max flow places 50 + 50 = 100, a greedy "nearest first" could strand A.
        r = sh.shelter_flow([[0, 0], [1000, 0]], [50, 50], [[0, 10], [1000, 10]], [50, 50], 300)
        self.assertEqual(r["sheltered"], 100)
        r2 = sh.shelter_flow([[0, 0], [400, 0]], [50, 50], [[0, 10], [200, 0]], [50, 50], 250)     # A reaches s1 and s2? A(0,0): s1 dist 10, s2 dist 200; B(400,0): s2 dist 200 only
        self.assertEqual(r2["sheltered"], 100)

    def test_reach_boundary_is_inclusive(self):
        self.assertEqual(sh.shelter_flow([[0, 0]], [10], [[1000, 0]], [10], 1000)["sheltered"], 10)
        self.assertEqual(sh.shelter_flow([[0, 0]], [10], [[1000.5, 0]], [10], 1000)["sheltered"], 0)

    def test_invariants_on_random_data(self):
        rng = np.random.default_rng(7)
        d = rng.uniform(0, 5000, (60, 2))
        p = rng.uniform(5, 200, 60)
        s = rng.uniform(0, 5000, (25, 2))
        c = np.floor(rng.uniform(0, 300, 25))
        for reach in (300, 800, 3000):
            r = sh.shelter_flow(d, p, s, c, reach)
            self.assertLessEqual(r["sheltered"], r["within_reach"] + 1e-6)
            self.assertLessEqual(r["within_reach"], r["total"] + 1e-6)
            self.assertLessEqual(r["sheltered"], r["capacity_in_reach"] + 1e-6)
            self.assertTrue((r["per_demand_sheltered"] <= p + 0.06).all())
            self.assertAlmostEqual(r["per_demand_sheltered"].sum(), r["sheltered"], places=6)

    def test_empty_inputs(self):
        r = sh.shelter_flow(np.zeros((0, 2)), [], [[0, 0]], [10], 100)
        self.assertEqual((r["total"], r["within_reach"], r["sheltered"]), (0, 0, 0))
        r = sh.shelter_flow([[0, 0]], [10], np.zeros((0, 2)), [], 100)
        self.assertEqual((r["within_reach"], r["sheltered"]), (0, 0))


if __name__ == "__main__":
    unittest.main()
