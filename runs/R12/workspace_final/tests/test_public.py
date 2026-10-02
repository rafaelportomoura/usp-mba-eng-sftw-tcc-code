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

    def test_normalizes_destination(self):
        self.assertEqual(calculate_shipping(1, "  ReGiOnAl  ", 5000), 1550)

    def test_weight_uses_started_kilos(self):
        self.assertEqual(calculate_shipping(1.01, "local", 5000), 1050)

    def test_free_shipping_threshold_is_inclusive(self):
        self.assertEqual(calculate_shipping(1, "local", 20000), 0)

    def test_express_is_based_on_pre_free_shipping_fee(self):
        self.assertEqual(calculate_shipping(1, "local", 20000, express=True), 1000)

    def test_express_rounds_half_up(self):
        # 7350 * 25% = 1837.5, which rounds to 1838.
        self.assertEqual(calculate_shipping(30, "regional", 5000, express=True), 7350 + 1838)

    def test_invalid_inputs(self):
        invalid = [
            (True, "local", 0), (0, "local", 0), (31, "local", 0),
            (10**1000, "local", 0), (float("inf"), "local", 0), (1, "mars", 0),
            (1, "local", -1), (1, "local", 0, 1),
        ]
        for args in invalid:
            with self.subTest(args=args):
                with self.assertRaises(ValueError):
                    calculate_shipping(*args)


if __name__ == "__main__":
    unittest.main()
