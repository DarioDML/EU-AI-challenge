"""Known-answer tests for challenge.evac (zone-to-shelter assignment). Every case has an answer worked out by hand."""
import os
import sys
import unittest

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
from challenge import evac, roads as rd


def line_graph(closed=None):
    # vertices 0-1-2-3 in a row, every edge 1 s, edge ids 0 (0-1), 1 (1-2), 2 (2-3)
    return rd.build_digraph([0, 1, 2], [1, 2, 3], [1.0, 1.0, 1.0], [0, 0, 0], 4, closed=closed)


class SnapTests(unittest.TestCase):
    def test_snap_and_limit(self):
        nodes = np.array([[0, 0], [100, 0], [1000, 0]], float)
        self.assertEqual(list(evac.snap([[10, 0], [900, 0], [5000, 0]], nodes, max_m=200)), [0, 2, -1])
        self.assertEqual(list(evac.snap([[10, 0]], nodes, allowed=[False, True, True], max_m=500)), [1])      # island vertex 0 not allowed


class AssignTests(unittest.TestCase):
    def run_case(self, people, cap, d_nodes, s_nodes, closed=None, k=8):
        g, arc = line_graph(closed)
        pairs = evac.nearest_shelters(g, d_nodes, s_nodes, k=k)
        flow, un = evac.assign(people, cap, pairs)
        load, routes = evac.route_loads(g, arc, np.array(d_nodes), np.array(s_nodes), pairs, flow, 3)
        return pairs, flow, un, load, routes

    def test_capacity_forces_split(self):
        # 100 people at vertex 0; shelter A at vertex 1 (cap 60, 1 s), shelter B at vertex 3 (cap 100, 3 s). 60 go to A, 40 to B: cost 60*1 + 40*3 = 180
        pairs, flow, un, load, routes = self.run_case([100], [60, 100], [0], [1, 3])
        by = {int(s): f for s, f in zip(pairs.s.values, flow)}
        self.assertAlmostEqual(by[0], 60.0, places=4)
        self.assertAlmostEqual(by[1], 40.0, places=4)
        self.assertAlmostEqual(float(un.sum()), 0.0, places=6)
        self.assertAlmostEqual(float((flow * pairs.t.values).sum()), 180.0, places=4)
        np.testing.assert_allclose(load, [100.0, 40.0, 40.0], atol=1e-4)       # edge 0-1 carries all 100, edges 1-2 and 2-3 carry the 40

    def test_not_enough_capacity_is_reported_unassigned(self):
        pairs, flow, un, load, routes = self.run_case([100], [40], [0], [2])
        self.assertAlmostEqual(float(flow.sum()), 40.0, places=4)
        self.assertAlmostEqual(float(un.sum()), 60.0, places=4)                  # 60 people are NOT placed and NOT dropped

    def test_conservation_and_capacity_hold(self):
        pairs, flow, un, load, routes = self.run_case([30, 50, 40], [60, 45], [0, 1, 2], [1, 3])
        self.assertAlmostEqual(float(flow.sum() + un.sum()), 120.0, places=4)
        for s, cap in ((0, 60), (1, 45)):
            self.assertLessEqual(float(flow[pairs.s.values == s].sum()), cap + 1e-6)

    def test_closed_road_makes_shelter_unreachable_and_people_unassigned(self):
        pairs, flow, un, load, routes = self.run_case([10], [100], [0], [3], closed=[False, True, False])
        self.assertEqual(len(pairs), 0)
        self.assertAlmostEqual(float(un.sum()), 10.0)

    def test_k_limits_the_choices(self):
        # with k=1 the single nearest shelter (cap 5) is the only option, so 95 of 100 stay unassigned even though a second shelter has room
        pairs, flow, un, load, routes = self.run_case([100], [5, 100], [0], [1, 3], k=1)
        self.assertAlmostEqual(float(un.sum()), 95.0, places=4)

    def test_routes_never_use_a_closed_edge_and_detour_costs_time(self):
        # square 0-1-2 direct (1 s + 1 s) and a detour 0-3-2 (5 s + 5 s); closing edge 1 (1-2) forces the detour of 10 s
        u, v, t = [0, 1, 0, 3], [1, 2, 3, 2], [1.0, 1.0, 5.0, 5.0]
        g, arc = rd.build_digraph(u, v, t, [0] * 4, 4)
        g2, arc2 = rd.build_digraph(u, v, t, [0] * 4, 4, closed=[False, True, False, False])
        p1 = evac.nearest_shelters(g, [0], [2])
        p2 = evac.nearest_shelters(g2, [0], [2])
        self.assertEqual(float(p1.t.iloc[0]), 2.0)
        self.assertEqual(float(p2.t.iloc[0]), 10.0)
        flow, _ = evac.assign([10], [100], p2)
        load, routes = evac.route_loads(g2, arc2, np.array([0]), np.array([2]), p2, flow, 4)
        self.assertEqual(load[1], 0.0)                                         # the closed edge carries nobody
        self.assertEqual(routes[0][1], [2, 3])                                 # route = detour edges 2 then 3


class PairTimeTests(unittest.TestCase):
    def test_baseline_time_and_unreachable(self):
        # same square as above: direct 0-1-2 costs 2 s, detour 0-3-2 costs 10 s; with the direct edge 1 closed the pair time is 10 s, on the open graph 2 s; vertex 4 is isolated
        u, v, t = [0, 1, 0, 3], [1, 2, 3, 2], [1.0, 1.0, 5.0, 5.0]
        g, _ = rd.build_digraph(u, v, t, [0] * 4, 5)
        g2, _ = rd.build_digraph(u, v, t, [0] * 4, 5, closed=[False, True, False, False])
        r = evac.pair_times(g, [0, 0], [2, 4], [0, 0], [0, 1])
        self.assertEqual(float(r[0]), 2.0)
        self.assertTrue(np.isinf(r[1]))
        self.assertEqual(float(evac.pair_times(g2, [0], [2], [0], [0])[0]), 10.0)


if __name__ == "__main__":
    unittest.main()
