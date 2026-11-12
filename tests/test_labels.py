import unittest

from solar_system_simulator.rendering.labels import visible_labels


class LabelTests(unittest.TestCase):
    def test_collapsed_system_keeps_only_sun_without_selection(self):
        rectangles = {i: (100+i, 100, 70, 22) for i in range(9)}
        self.assertEqual(visible_labels(rectangles), {0})

    def test_selected_planet_replaces_sun_in_collapsed_system(self):
        rectangles = {i: (100+i, 100, 70, 22) for i in range(9)}
        self.assertEqual(visible_labels(rectangles, selected=3), {3})

    def test_both_overlapping_names_disappear(self):
        rectangles = {0: (0, 0, 30, 22), 1: (100, 100, 60, 22),
                      2: (140, 100, 50, 22), 3: (300, 100, 50, 22)}
        self.assertEqual(visible_labels(rectangles), {0, 3})

    def test_all_names_return_after_zoom_separates_them(self):
        collapsed = {i: (100+i, 100, 70, 22) for i in range(9)}
        expanded = {i: (i*100, 100, 70, 22) for i in range(9)}
        self.assertEqual(visible_labels(collapsed, selected=5), {5})
        self.assertEqual(visible_labels(expanded, selected=5), set(range(9)))

    def test_vertical_separation_and_overlap_chains(self):
        rectangles = {0: (0, 0, 30, 20), 1: (100, 100, 60, 20),
                      2: (150, 100, 60, 20), 3: (200, 100, 60, 20),
                      4: (100, 150, 60, 20)}
        self.assertEqual(visible_labels(rectangles), {0, 4})

    def test_empty_viewport(self):
        self.assertEqual(visible_labels({}, selected=3), set())
