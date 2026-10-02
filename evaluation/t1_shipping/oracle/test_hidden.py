# EVALUATION-ONLY: testes-oraculo ocultos; nao fornecer ao agente avaliado.
import unittest

from shipping import calculate_shipping as ship


class HiddenShippingTests(unittest.TestCase):
    # R1
    def test_r1_weight_zero(self):
        with self.assertRaises(ValueError):
            ship(0, "local", 0)

    def test_r1_weight_negative(self):
        with self.assertRaises(ValueError):
            ship(-1, "local", 0)

    def test_r1_weight_over_max(self):
        with self.assertRaises(ValueError):
            ship(30.01, "local", 0)

    def test_r1_weight_max_ok(self):
        self.assertEqual(ship(30, "local", 0), 850 + 29 * 200)

    def test_r1_weight_bool_nan_inf_str(self):
        for bad in (True, float("nan"), float("inf"), "2", None):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    ship(bad, "local", 0)

    # R2
    def test_r2_destination_normalized(self):
        self.assertEqual(ship(1, "  Regional ", 0), 1550)

    def test_r2_destination_invalid(self):
        for bad in ("", "world", None, 3):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    ship(1, bad, 0)

    # R3
    def test_r3_subtotal_invalid(self):
        for bad in (-1, 10.5, True, "100", None):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    ship(1, "local", bad)

    def test_r3_express_not_bool(self):
        for bad in (1, 0, "yes", None):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    ship(1, "local", 0, express=bad)

    # R4
    def test_r4_base_by_destination(self):
        self.assertEqual(ship(1, "local", 0), 850)
        self.assertEqual(ship(1, "regional", 0), 1550)
        self.assertEqual(ship(1, "national", 0), 2490)

    def test_r4_fractional_weights_round_up(self):
        self.assertEqual(ship(0.1, "local", 0), 850)
        self.assertEqual(ship(1.0001, "local", 0), 1050)
        self.assertEqual(ship(2, "local", 0), 1050)
        self.assertEqual(ship(2.01, "local", 0), 1250)

    def test_r4_tiny_excess_still_started_kg(self):
        # kg iniciado: qualquer fração acima do inteiro conta como mais um kg (sem arredondar o peso)
        self.assertEqual(ship(1.0000001, "local", 0), 1050)
        self.assertEqual(ship(2.00000001, "local", 0), 1250)
        self.assertEqual(ship(29.9999999, "national", 0), 2490 + 29 * 200)

    # R5
    def test_r5_threshold_inclusive(self):
        self.assertEqual(ship(5, "national", 20000), 0)
        self.assertEqual(ship(1, "local", 19999), 850)

    # R6
    def test_r6_rounding_half_up(self):
        # 25% de 850 = 212.5 -> mínimo 1000 prevalece; usar frete maior
        # national 30 kg: 2490 + 5800 = 8290; 25% = 2072.5 -> 2073
        self.assertEqual(ship(30, "national", 0, express=True), 8290 + 2073)

    def test_r6_minimum_applies(self):
        self.assertEqual(ship(1, "national", 0, express=True), 2490 + 1000)

    def test_r6_percentage_above_minimum(self):
        # regional 25 kg: 1550 + 24*200 = 6350; 25% = 1587.5 -> 1588
        self.assertEqual(ship(25, "regional", 0, express=True), 6350 + 1588)

    def test_r6_express_due_when_free(self):
        self.assertEqual(ship(1, "local", 20000, express=True), 1000)
        self.assertEqual(ship(30, "national", 50000, express=True), 2073)

    # R7
    def test_r7_returns_int(self):
        for args in ((1, "local", 0), (2.5, "regional", 0, True), (3, "national", 20000, True)):
            with self.subTest(args=args):
                result = ship(*args)
                self.assertIs(type(result), int)


if __name__ == "__main__":
    unittest.main()
