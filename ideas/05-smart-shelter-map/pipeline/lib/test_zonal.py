"""Known-answer tests for challenge.zonal (synthetic geometry in metres; no data access)."""
import pathlib
import sys
import unittest

import numpy as np
import shapely
from shapely import box

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from challenge import zonal  # noqa: E402

CELL = box(0, 0, 1000, 1000)


class ResidentsByZone(unittest.TestCase):
    def test_hand_computed_split_across_two_zones_and_three_statuses(self):
        # 100 residents in one 1 km2 cell; zones L (x<500) and R (x>=500); flood x<250; AOI x<750
        df, outside = zonal.residents_by_zone([CELL], [100], [box(0, 0, 500, 1000), box(500, 0, 1000, 1000)], ["L", "R"], box(0, 0, 250, 1000), box(0, 0, 750, 1000))
        self.assertAlmostEqual(df.loc["L", "exposed"], 25)
        self.assertAlmostEqual(df.loc["L", "not_mapped_flooded_inside_aoi"], 25)
        self.assertAlmostEqual(df.loc["L", "not_assessed_outside_aoi"], 0)
        self.assertAlmostEqual(df.loc["R", "exposed"], 0)
        self.assertAlmostEqual(df.loc["R", "not_mapped_flooded_inside_aoi"], 25)
        self.assertAlmostEqual(df.loc["R", "not_assessed_outside_aoi"], 25)
        self.assertAlmostEqual(outside, 0)

    def test_people_are_conserved_including_cell_parts_outside_every_zone(self):
        # zones cover only x<800: 20% of the cell lies in no zone
        df, outside = zonal.residents_by_zone([CELL], [100], [box(0, 0, 800, 1000)], ["Z"], box(0, 0, 300, 1000), box(0, 0, 1000, 1000))
        self.assertAlmostEqual(outside, 20)
        self.assertAlmostEqual(df[list(zonal.STATUSES)].to_numpy().sum() + outside, 100)
        self.assertAlmostEqual(df.loc["Z", "exposed"], 30)

    def test_empty_flood_gives_zero_exposed_and_unknown_stays_unknown(self):
        df, outside = zonal.residents_by_zone([CELL], [100], [box(-10, -10, 2000, 2000)], ["Z"], shapely.Polygon(), box(0, 0, 400, 1000))
        self.assertAlmostEqual(df.loc["Z", "exposed"], 0)
        self.assertAlmostEqual(df.loc["Z", "not_mapped_flooded_inside_aoi"], 40)     # inside the AOI, no polygon: NOT dry, NOT flooded
        self.assertAlmostEqual(df.loc["Z", "not_assessed_outside_aoi"], 60)

    def test_flood_outside_the_aoi_is_clipped_not_counted(self):
        df, _ = zonal.residents_by_zone([CELL], [100], [box(-10, -10, 2000, 2000)], ["Z"], box(0, 0, 1000, 1000), box(0, 0, 500, 1000))
        self.assertAlmostEqual(df.loc["Z", "exposed"], 50)                            # only the half of the flood inside the AOI

    def test_several_cells_sum_exactly(self):
        c2 = box(1000, 0, 2000, 1000)
        df, outside = zonal.residents_by_zone([CELL, c2], [100, 40], [box(0, 0, 1500, 1000), box(1500, 0, 2000, 1000)], ["A", "B"],
                                              box(0, 0, 2000, 500), box(0, 0, 2000, 1000))
        self.assertAlmostEqual(df[list(zonal.STATUSES)].to_numpy().sum() + outside, 140)
        self.assertAlmostEqual(df.loc["A", "exposed"], 50 + 10)                      # half of cell 1, half of the left half of cell 2
        self.assertAlmostEqual(df.loc["B", "exposed"], 10)


class Dasymetric(unittest.TestCase):
    class PW:                                   # a 1 x 2 cell window: columns 0 and 1, row 0 (north-up, 0.5 deg cells)
        class tf:
            c, f, a, e = 0.0, 1.0, 0.5, -0.5
        nr, nc = 1, 2

    def test_cell_index_finds_cell_and_flags_outside(self):
        idx = zonal.cell_index([0.1, 0.6, 2.0, 0.1], [0.8, 0.8, 0.8, 5.0], self.PW)
        self.assertEqual(list(idx), [0, 1, -1, -1])

    def test_people_are_shared_by_footprint_area_and_unallocated_is_reported(self):
        # cell 0: 100 people, buildings 100 and 300 m2 -> 25 / 75; cell 1: 50 people, only a use==0 building -> unallocated 50
        cell = np.array([0, 0, 1, 0])
        area = np.array([100.0, 300.0, 400.0, 999.0])
        use = np.array([1, 2, 0, 0])                      # the last building of cell 0 is outside the built-up domain (use 0)
        out, unalloc, alloc = zonal.people_per_building(cell, area, use, np.array([100.0, 50.0]))
        self.assertAlmostEqual(out[0], 25)
        self.assertAlmostEqual(out[1], 75)
        self.assertTrue(np.isnan(out[2]) and np.isnan(out[3]))
        self.assertAlmostEqual(unalloc, 50)
        self.assertAlmostEqual(alloc + unalloc, 150)       # conservation

    def test_cells_not_wanted_are_left_alone(self):
        out, unalloc, alloc = zonal.people_per_building(np.array([0, 1]), np.array([10.0, 10.0]), np.array([1, 1]), np.array([100.0, 50.0]), cells_wanted=np.array([True, False]))
        self.assertAlmostEqual(out[0], 100)
        self.assertTrue(np.isnan(out[1]))
        self.assertAlmostEqual(unalloc, 0)

    def test_invalid_or_missing_area_buildings_get_nothing(self):
        out, unalloc, _ = zonal.people_per_building(np.array([0, 0]), np.array([np.nan, 0.0]), np.array([1, 1]), np.array([80.0]))
        self.assertTrue(np.isnan(out).all())
        self.assertAlmostEqual(unalloc, 80)


class PointsAndTiles(unittest.TestCase):
    def test_point_counts_per_zone_count_each_point_once(self):
        zones = [box(0, 0, 10, 10), box(10, 0, 20, 10)]
        x, y = [5, 10, 15, 25], [5, 5, 5, 5]                                         # the second point sits exactly on the shared border
        mask = [True, True, True, True]
        counts, nowhere = zonal.points_by_zone(x, y, mask, zones, ["A", "B"])
        self.assertEqual(int(counts.sum()) + nowhere, 4)
        self.assertEqual(nowhere, 1)
        self.assertEqual(counts["A"] + counts["B"], 3)

    def test_mask_selects_points(self):
        counts, nowhere = zonal.points_by_zone([5, 15], [5, 5], [True, False], [box(0, 0, 10, 10), box(10, 0, 20, 10)], ["A", "B"])
        self.assertEqual((counts["A"], counts["B"], nowhere), (1, 0, 0))

    def test_tiles_cover_every_part_plus_buffer_and_group_near_parts(self):
        flood = shapely.union_all([box(0, 0, 100, 100), box(300, 0, 400, 100), box(50000, 0, 50100, 100)])
        tiles = zonal.tile_bboxes(flood, buffer_m=50, cell_m=5000)
        self.assertEqual(len(tiles), 2)                                              # two near parts share a tile, the far one has its own
        for part in shapely.get_parts(flood):
            self.assertTrue(any(t[0] <= part.bounds[0] - 50 and t[1] <= part.bounds[1] - 50 and t[2] >= part.bounds[2] + 50 and t[3] >= part.bounds[3] + 50 for t in tiles))

    def test_no_flood_no_tiles(self):
        self.assertEqual(zonal.tile_bboxes(shapely.Polygon()), [])


if __name__ == "__main__":
    unittest.main()
