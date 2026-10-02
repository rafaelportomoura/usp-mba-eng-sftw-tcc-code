import unittest

from shipping import calculate_shipping


class PublicShippingTests(unittest.TestCase):
    def test_r4_local_one_kg(self):
        self.assertEqual(calculate_shipping(1, "local", 5000), 850)

    def test_r4_regional_started_kg(self):
        # 2.5 kg = 3 kg iniciados => 2 kg adicionais
        self.assertEqual(calculate_shipping(2.5, "regional", 5000), 1550 + 400)

    def test_r5_free_above_threshold(self):
        self.assertEqual(calculate_shipping(1, "national", 30000), 0)

    def test_r2_invalid_destination(self):
        with self.assertRaises(ValueError):
            calculate_shipping(1, "mars", 5000)

    def test_r2_normalizes_destination(self):
        self.assertEqual(calculate_shipping(1, "  LOCAL ", 5000), 850)

    def test_r1_invalid_weights(self):
        for weight in (True, False, 0, -1, 30.1, float("inf"), float("nan"), "2"):
            with self.subTest(weight=weight):
                with self.assertRaises(ValueError):
                    calculate_shipping(weight, "local", 5000)

    def test_r3_invalid_values(self):
        for subtotal in (True, -1, 1.5, "5000"):
            with self.subTest(subtotal=subtotal):
                with self.assertRaises(ValueError):
                    calculate_shipping(1, "local", subtotal)
        with self.assertRaises(ValueError):
            calculate_shipping(1, "local", 5000, express=1)

    def test_r5_threshold_is_inclusive(self):
        self.assertEqual(calculate_shipping(1, "local", 20000), 0)

    def test_r6_uses_pre_free_shipping_fee_and_rounds_half_up(self):
        # 25% of 4250 is 1062.5, rounded to 1063.
        self.assertEqual(calculate_shipping(18, "local", 20000, express=True), 1063)

    def test_r6_express_minimum(self):
        self.assertEqual(calculate_shipping(1, "local", 5000, express=True), 850 + 1000)


if __name__ == "__main__":
    unittest.main()
