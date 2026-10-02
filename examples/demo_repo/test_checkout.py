import unittest
from checkout import checkout_total


class CheckoutTests(unittest.TestCase):
    def test_coupon_total(self):
        self.assertEqual(str(checkout_total([{"price": 10, "quantity": 2}], 10)), "18.00")
