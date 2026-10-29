"""Known-answer tests for challenge.roads (road graph for the shelter tool). Every case has an answer worked out by hand."""
import os
import sys
import unittest

import numpy as np
import shapely
from scipy.sparse.csgraph import dijkstra

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
from challenge import roads as rd


def L(*pts):
    return shapely.linestrings(np.array(pts, float))


class SplitTests(unittest.TestCase):
    def test_t_junction_connects(self):
        # through road A (0,0)-(1,0)-(2,0) with a vertex at (1,0); side road B starts at that vertex. A must be split in two, B stays one: 3 edges, and B reaches both ends of A.
        a, b = L((0, 0), (1, 0), (2, 0)), L((1, 0), (1, 1))
        r = rd.split_ways(np.array([a, b], dtype=object), scale=1.0)
        self.assertEqual(len(r["u"]), 3)
        g, _ = rd.build_digraph(r["u"], r["v"], np.ones(3), np.zeros(3, int), len(r["nodes_xy"]))
        d = dijkstra(g, directed=False, indices=[int(r["u"][2])])      # edge 2 = B: from its start (1,0)
        self.assertTrue(np.isfinite(d).sum() >= 4)                     # all four vertices reachable

    def test_endpoint_only_graph_would_miss_it(self):
        # the same A and B as endpoint-only lines share no endpoint: A (0,0)-(2,0), B (1,0)-(1,1)
        a, b = L((0, 0), (2, 0)), L((1, 0), (1, 1))
        r = rd.split_ways(np.array([a, b], dtype=object), scale=1.0)
        self.assertEqual(len(r["u"]), 2)                               # nothing to split: with no shared vertex the two ways are NOT connected
        self.assertEqual(len(set(r["u"]) | set(r["v"])), 4)

    def test_bridge_crossing_is_not_a_junction(self):
        # road C (0,-1)-(0,1) crosses road A (-1,0)-(1,0) at (0,0), but neither has a vertex there: crossing without a shared vertex stays unconnected
        a, c = L((-1, 0), (1, 0)), L((0, -1), (0, 1))
        r = rd.split_ways(np.array([a, c], dtype=object), scale=1.0)
        self.assertEqual(len(r["u"]), 2)
        g, _ = rd.build_digraph(r["u"], r["v"], np.ones(2), np.zeros(2, int), len(r["nodes_xy"]))
        d = dijkstra(g, directed=False, indices=[int(r["u"][0])])
        self.assertEqual(int(np.isfinite(d).sum()), 2)                 # only A's own two vertices

    def test_loop_and_shared_end(self):
        a, b = L((0, 0), (1, 0)), L((1, 0), (2, 0))
        r = rd.split_ways(np.array([a, b], dtype=object), scale=1.0)
        self.assertEqual(len(r["u"]), 2)
        self.assertEqual(r["v"][0], r["u"][1])                         # the shared end is one vertex

    def test_rounding_merges_nearby_vertices(self):
        a, b = L((0, 0), (1.0000001, 0)), L((1.0000002, 0), (2, 0))
        r = rd.split_ways(np.array([a, b], dtype=object), scale=1e6)  # 1e-6 resolution: the two end points are the same vertex
        self.assertEqual(r["v"][0], r["u"][1])


class GraphTests(unittest.TestCase):
    def test_one_way_and_reverse(self):
        g, _ = rd.build_digraph([0], [1], [5.0], [1], 2)
        self.assertEqual(dijkstra(g, indices=0)[1], 5.0)
        self.assertTrue(np.isinf(dijkstra(g, indices=1)[0]))           # forward-only: no way back
        g2, _ = rd.build_digraph([0], [1], [5.0], [-1], 2)
        self.assertEqual(dijkstra(g2, indices=1)[0], 5.0)              # reverse-only: v -> u

    def test_closure_forces_detour(self):
        # nodes 0-1-2 direct (cost 2 + 2) and a detour 0-3-2 (cost 5 + 5). Closing edge 1 (1-2) must give 10.
        u, v, t = [0, 1, 0, 3], [1, 2, 3, 2], [2.0, 2.0, 5.0, 5.0]
        g, _ = rd.build_digraph(u, v, t, [0, 0, 0, 0], 4)
        self.assertEqual(dijkstra(g, indices=0)[2], 4.0)
        g2, _ = rd.build_digraph(u, v, t, [0, 0, 0, 0], 4, closed=[False, True, False, False])
        self.assertEqual(dijkstra(g2, indices=0)[2], 10.0)
        g3, _ = rd.build_digraph(u, v, t, [0, 0, 0, 0], 4, closed=[False, True, True, False])
        self.assertTrue(np.isinf(dijkstra(g3, indices=0)[2]))          # both ways closed: unreachable, not a large finite number

    def test_parallel_edges_keep_fastest_and_path_edges(self):
        g, arc = rd.build_digraph([0, 0, 1], [1, 1, 2], [9.0, 4.0, 3.0], [0, 0, 0], 3)
        d, pred = dijkstra(g, indices=0, return_predecessors=True)
        self.assertEqual(d[2], 7.0)
        self.assertEqual(rd.path_edges(pred, 0, 2, arc), [1, 2])       # edge 1 (cost 4) not edge 0 (cost 9), then edge 2

    def test_path_unreachable_is_empty(self):
        g, arc = rd.build_digraph([0], [1], [1.0], [0], 3)
        _, pred = dijkstra(g, indices=0, return_predecessors=True)
        self.assertEqual(rd.path_edges(pred, 0, 2, arc), [])


class SpeedTests(unittest.TestCase):
    def test_travel_time_and_maxspeed(self):
        # 1000 m at the class default 50 km/h = 72 s; with maxspeed 100 = 36 s
        self.assertAlmostEqual(rd.travel_time_s([1000], ["tertiary"])[0], 72.0)
        self.assertAlmostEqual(rd.travel_time_s([1000], ["tertiary"], [100.0])[0], 36.0)
        self.assertAlmostEqual(rd.travel_time_s([1000], ["tertiary"], [np.nan])[0], 72.0)

    def test_parse_maxspeed(self):
        self.assertEqual(rd.parse_maxspeed("50"), 50.0)
        self.assertTrue(np.isnan(rd.parse_maxspeed("none")))
        self.assertTrue(np.isnan(rd.parse_maxspeed("30 mph")))
        self.assertTrue(np.isnan(rd.parse_maxspeed(None)))


if __name__ == "__main__":
    unittest.main()
