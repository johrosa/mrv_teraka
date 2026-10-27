# -*- coding: utf-8 -*-
import unittest
from utils import Utils

class TestUtils(unittest.TestCase):
    def test_flatten_json(self):
        nested = {'a': {'b': 1, 'c': 2}, 'd': 3}
        flattened = Utils.flatten_json(nested)
        self.assertEqual(flattened, {'a_b': 1, 'a_c': 2, 'd': 3})

    def test_is_html_content(self):
        self.assertTrue(Utils.is_html_content("<div>test</div>"))
        self.assertTrue(Utils.is_html_content("<h1>Title</h1>"))
        self.assertFalse(Utils.is_html_content("Plain text string"))
        self.assertFalse(Utils.is_html_content(None))
        self.assertFalse(Utils.is_html_content(123))

    def test_is_geojson(self):
        self.assertTrue(Utils.is_geojson({'type': 'FeatureCollection'}))
        self.assertTrue(Utils.is_geojson({'type': 'Feature'}))
        self.assertFalse(Utils.is_geojson({'type': 'Other'}))
        self.assertFalse(Utils.is_geojson(None))

if __name__ == '__main__':
    unittest.main()
