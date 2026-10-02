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

    def test_r6_express_minimum(self):
        self.assertEqual(calculate_shipping(1, "local", 5000, express=True), 850 + 1000)

    def test_r1_weight_validation_and_started_kg_boundaries(self):
        self.assertEqual(calculate_shipping(1.01, "local", 0), 1050)
        self.assertEqual(calculate_shipping(30, "local", 0), 850 + 29 * 200)
        for weight in (0, -1, 10**1000, 30.1, float("inf"), float("nan"), True, "1"):
            with self.subTest(weight=weight):
                with self.assertRaises(ValueError):
                    calculate_shipping(weight, "local", 0)

    def test_r2_destination_is_normalized_and_validated(self):
        self.assertEqual(calculate_shipping(1, "  ReGiOnAl ", 0), 1550)
        for destination in (None, 1, "mars", ""):
            with self.subTest(destination=destination):
                with self.assertRaises(ValueError):
                    calculate_shipping(1, destination, 0)

    def test_r3_values_and_flag_are_validated(self):
        self.assertEqual(calculate_shipping(1, "local", 0, express=False), 850)
        for subtotal in (-1, True, 1.0, "0"):
            with self.subTest(subtotal=subtotal):
                with self.assertRaises(ValueError):
                    calculate_shipping(1, "local", subtotal)
        with self.assertRaises(ValueError):
            calculate_shipping(1, "local", 0, express=1)

    def test_r5_threshold_is_inclusive(self):
        self.assertEqual(calculate_shipping(1, "national", 20000), 0)

    def test_r6_express_uses_original_fee_and_rounds_half_up(self):
        # 4050 * 25% = 1012.5, rounded upward to 1013.
        self.assertEqual(calculate_shipping(17, "local", 0, express=True), 4050 + 1013)
        self.assertEqual(calculate_shipping(1, "national", 20000, express=True), 1000)


if __name__ == "__main__":
    unittest.main()
