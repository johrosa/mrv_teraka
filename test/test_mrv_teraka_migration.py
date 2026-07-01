# -*- coding: utf-8 -*-
import os
import sys
import unittest

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import Utils


class TestMrvTerakaMigration(unittest.TestCase):
    def test_non_spatial_layer_does_not_resolve_geom_field(self):
        self.assertIsNone(Utils.resolve_postgrest_geom_field(None, False))
        self.assertIsNone(Utils.resolve_postgrest_geom_field('geom', False))

    def test_spatial_layer_uses_mapping_or_defaults_to_geom(self):
        self.assertEqual(Utils.resolve_postgrest_geom_field('geometry', True), 'geometry')
        self.assertEqual(Utils.resolve_postgrest_geom_field(None, True), 'geom')


if __name__ == '__main__':
    unittest.main()
