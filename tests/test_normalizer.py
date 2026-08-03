import unittest
from mywa.normalizer import normalize, strip_plus, carrier_for, country_for, is_valid_mobile

class TestNormalizer(unittest.TestCase):
    def test_strip_plus(self):
        self.assertEqual(strip_plus("+233241234567"), "233241234567")
        self.assertEqual(strip_plus("024-123-4567"), "0241234567")

    def test_normalize(self):
        # Ghana (default)
        self.assertEqual(normalize("0241234567"), "+233241234567")
        self.assertEqual(normalize("241234567"), "+233241234567")
        self.assertEqual(normalize("+233241234567"), "+233241234567")
        # Other country
        self.assertEqual(normalize("+12025550123", "1"), "+12025550123")

    def test_carrier_for(self):
        self.assertEqual(carrier_for("+233241234567"), "MTN")
        self.assertEqual(carrier_for("+233201234567"), "Telecel")
        self.assertEqual(carrier_for("+233571234567"), "AirtelTigo")
        self.assertEqual(carrier_for("+12025550123"), "")

    def test_country_for(self):
        self.assertEqual(country_for("+233241234567"), "GH")
        self.assertEqual(country_for("+12025550123"), "US")
        self.assertEqual(country_for("+442071234567"), "GB")
        self.assertEqual(country_for("+919876543210"), "IN")

    def test_is_valid_mobile(self):
        self.assertTrue(is_valid_mobile("+233241234567"))
        self.assertFalse(is_valid_mobile("+12025550123"))
