import unittest
from billing import round_amount


class BillingTests(unittest.TestCase):
    def test_fractional_cent(self):
        self.assertEqual(str(round_amount(2.675)), "2.68")
