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

    def test_r5_free_at_threshold(self):
        self.assertEqual(calculate_shipping(1, "national", 20000), 0)

    def test_r2_invalid_destination(self):
        with self.assertRaises(ValueError):
            calculate_shipping(1, "mars", 5000)

    def test_r2_normalizes_destination(self):
        self.assertEqual(calculate_shipping(1, "  ReGiOnAl ", 5000), 1550)

    def test_r6_express_minimum(self):
        self.assertEqual(calculate_shipping(1, "local", 5000, express=True), 850 + 1000)

    def test_r6_express_is_due_when_standard_shipping_is_free(self):
        self.assertEqual(calculate_shipping(1, "local", 20000, express=True), 1000)

    def test_r6_express_rounds_half_up(self):
        # 25% de 5490 = 1372,5, arredondado para 1373.
        self.assertEqual(calculate_shipping(16, "national", 0, express=True), 5490 + 1373)

    def test_r1_invalid_weights(self):
        for weight in (True, False, 0, -1, 30.1, float("inf"), float("nan"), "1"):
            with self.subTest(weight=weight):
                with self.assertRaises(ValueError):
                    calculate_shipping(weight, "local", 0)

    def test_r3_invalid_subtotal_and_express(self):
        for subtotal in (True, -1, 1.5, "0"):
            with self.subTest(subtotal=subtotal):
                with self.assertRaises(ValueError):
                    calculate_shipping(1, "local", subtotal)
        with self.assertRaises(ValueError):
            calculate_shipping(1, "local", 0, express=1)

    def test_r2_invalid_destination_types(self):
        for destination in (None, 1, " Mars "):
            with self.subTest(destination=destination):
                with self.assertRaises(ValueError):
                    calculate_shipping(1, destination, 0)


if __name__ == "__main__":
    unittest.main()
