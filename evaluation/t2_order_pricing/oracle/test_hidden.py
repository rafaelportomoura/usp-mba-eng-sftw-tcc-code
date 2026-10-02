# EVALUATION-ONLY: testes-oraculo ocultos; nao fornecer ao agente avaliado.
import copy
import unittest

from pricing import calculate_order as calc


def item(sku, price, qty):
    return {"sku": sku, "unit_price_cents": price, "quantity": qty}


class HiddenPricingTests(unittest.TestCase):
    # R1
    def test_r1_empty_items(self):
        for bad in ([], (), None, "abc"):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    calc(bad, {})

    def test_r1_invalid_item_fields(self):
        bad_items = [
            item("", 100, 1), item(None, 100, 1), item("a", -1, 1), item("a", 1.5, 1),
            item("a", True, 1), item("a", 100, 0), item("a", 100, -2), item("a", 100, True),
            item("a", 100, 1.0), {"sku": "a", "quantity": 1}, "not-a-dict",
            item(5, 100, 1), item(["a"], 100, 1), {"unit_price_cents": 100, "quantity": 1},
        ]
        for bad in bad_items:
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    calc([bad], {})

    def test_r1_customer_invalid(self):
        for bad in (None, [], "vip"):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    calc([item("a", 100, 1)], bad)
        for bad_vip in ("yes", 1, 0, None):
            with self.subTest(vip=bad_vip):
                with self.assertRaises(ValueError):
                    calc([item("a", 100, 1)], {"vip": bad_vip})

    def test_r1_zero_price_allowed(self):
        self.assertEqual(calc([item("a", 0, 3)], {})["total_cents"], 0)

    # R2
    def test_r2_subtotal(self):
        self.assertEqual(calc([item("a", 333, 3), item("b", 1, 7)], {})["subtotal_cents"], 1006)

    def test_r2_accepts_tuple(self):
        self.assertEqual(calc((item("a", 100, 1),), {})["subtotal_cents"], 100)

    # R3
    def test_r3_vip_rounding_half_up(self):
        # 10% de 1005 = 100.5 -> 101
        r = calc([item("a", 1005, 1)], {"vip": True})
        self.assertEqual(r["vip_discount_cents"], 101)

    def test_r3_vip_false_no_discount(self):
        self.assertEqual(calc([item("a", 1000, 1)], {"vip": False})["vip_discount_cents"], 0)

    # R4
    def test_r4_coupon_after_vip(self):
        r = calc([item("a", 10000, 1)], {"vip": True}, "SAVE10")
        self.assertEqual(r["vip_discount_cents"], 1000)
        self.assertEqual(r["coupon_discount_cents"], 900)

    def test_r4_fixed_capped(self):
        r = calc([item("a", 300, 1)], {}, "FIXED500")
        self.assertEqual(r["coupon_discount_cents"], 300)
        self.assertEqual(r["taxable_cents"], 0)
        self.assertEqual(r["total_cents"], 0)

    def test_r4_fixed_capped_to_remaining_after_vip(self):
        # 500 com VIP: vip 50, restante 450, FIXED500 limitado a 450 (não ao subtotal)
        r = calc([item("a", 500, 1)], {"vip": True}, "FIXED500")
        self.assertEqual((r["vip_discount_cents"], r["coupon_discount_cents"]), (50, 450))
        self.assertEqual((r["taxable_cents"], r["tax_cents"], r["total_cents"]), (0, 0, 0))
        r = calc([item("a", 300, 1)], {"vip": True}, "FIXED500")
        self.assertEqual((r["vip_discount_cents"], r["coupon_discount_cents"], r["taxable_cents"]), (30, 270, 0))

    def test_r4_fixed_with_zero_remaining(self):
        # valor restante 0: desconto limitado a 0 (nunca 500), taxable nunca negativo
        r = calc([item("a", 0, 3)], {}, "FIXED500")
        self.assertEqual(r["coupon_discount_cents"], 0)
        self.assertEqual((r["taxable_cents"], r["tax_cents"], r["total_cents"]), (0, 0, 0))

    def test_r4_save10_half_up_on_remaining(self):
        # 10% de 1005 = 100.5 -> 101 (truncar daria 100; round() bancário daria 100)
        r = calc([item("a", 1005, 1)], {}, "SAVE10")
        self.assertEqual((r["coupon_discount_cents"], r["taxable_cents"]), (101, 904))
        # 10% de 905 = 90.5 -> 91 (round() bancário daria 90)
        r = calc([item("a", 905, 1)], {}, "SAVE10")
        self.assertEqual((r["coupon_discount_cents"], r["taxable_cents"]), (91, 814))

    def test_r4_fixed_normal(self):
        self.assertEqual(calc([item("a", 2000, 1)], {}, "FIXED500")["coupon_discount_cents"], 500)

    def test_r4_coupon_normalized(self):
        r = calc([item("a", 10000, 1)], {}, "  save10 ")
        self.assertEqual(r["coupon_discount_cents"], 1000)

    def test_r4_unknown_or_invalid_coupon(self):
        for bad in ("FREE", "", 10):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    calc([item("a", 1000, 1)], {}, bad)

    # R5
    def test_r5_tax_after_discounts(self):
        r = calc([item("a", 10000, 1)], {"vip": True}, "SAVE10")
        self.assertEqual(r["taxable_cents"], 8100)
        self.assertEqual(r["tax_cents"], 810)
        self.assertEqual(r["total_cents"], 8910)

    def test_r5_tax_with_fixed_coupon(self):
        r = calc([item("a", 2000, 1)], {}, "FIXED500")
        self.assertEqual(r["taxable_cents"], 1500)
        self.assertEqual(r["tax_cents"], 150)
        self.assertEqual(r["total_cents"], 1650)

    # R6
    def test_r6_half_up_tax_not_bankers(self):
        # 10% de 25 = 2.5 -> 3 (round() bancário daria 2)
        self.assertEqual(calc([item("a", 25, 1)], {})["tax_cents"], 3)
        # 10% de 35 = 3.5 -> 4
        self.assertEqual(calc([item("a", 35, 1)], {})["tax_cents"], 4)

    def test_r6_large_values_exact(self):
        # valores grandes onde float perderia precisão (sem desconto)
        price = 9_007_199_254_740_993  # 2**53 + 1
        r = calc([item("a", price, 1)], {})
        self.assertEqual(r["tax_cents"], (price * 1000 + 5000) // 10000)
        self.assertEqual(r["total_cents"], price + r["tax_cents"])

    def test_r6_large_values_exact_with_vip_and_coupon(self):
        # R6 proíbe ponto flutuante: confere as seis chaves contra aritmética inteira exata
        for price in (9_007_199_254_740_993, 10**17 + 5, 10**17 + 4, 10**18 + 15):
            for vip in (False, True):
                for coupon in (None, "SAVE10", "FIXED500"):
                    with self.subTest(price=price, vip=vip, coupon=coupon):
                        sub = price
                        vd = (sub * 1000 + 5000) // 10000 if vip else 0
                        rem = sub - vd
                        cd = {None: 0, "SAVE10": (rem * 1000 + 5000) // 10000, "FIXED500": min(500, rem)}[coupon]
                        taxable = sub - vd - cd
                        tax = (taxable * 1000 + 5000) // 10000
                        r = calc([item("a", price, 1)], {"vip": vip}, coupon)
                        self.assertEqual(
                            r,
                            {"subtotal_cents": sub, "vip_discount_cents": vd, "coupon_discount_cents": cd,
                             "taxable_cents": taxable, "tax_cents": tax, "total_cents": taxable + tax},
                        )

    def test_r6_large_quantity_times_price_exact(self):
        price, qty = 10**15 + 1, 123_457
        r = calc([item("a", price, qty)], {"vip": True}, "SAVE10")
        sub = price * qty
        vd = (sub * 1000 + 5000) // 10000
        cd = ((sub - vd) * 1000 + 5000) // 10000
        taxable = sub - vd - cd
        self.assertEqual(r["subtotal_cents"], sub)
        self.assertEqual(r["total_cents"], taxable + (taxable * 1000 + 5000) // 10000)

    def test_r6_all_ints(self):
        r = calc([item("a", 1005, 1)], {"vip": True}, "SAVE10")
        for key, value in r.items():
            with self.subTest(key=key):
                self.assertIs(type(value), int)

    def test_r6_components_rounded_individually(self):
        # subtotal 1005, vip 101 (100.5), restante 904, save10 90 (90.4), taxable 814, tax 81 (81.4)
        r = calc([item("a", 1005, 1)], {"vip": True}, "SAVE10")
        self.assertEqual(
            (r["vip_discount_cents"], r["coupon_discount_cents"], r["taxable_cents"],
             r["tax_cents"], r["total_cents"]),
            (101, 90, 814, 81, 895),
        )

    # R7
    def test_r7_inputs_not_mutated(self):
        items = [item("z", 100, 1), item("a", 200, 2)]
        customer = {"vip": True}
        items_copy, customer_copy = copy.deepcopy(items), copy.deepcopy(customer)
        calc(items, customer, "SAVE10")
        self.assertEqual(items, items_copy)
        self.assertEqual(customer, customer_copy)

    def test_r7_customer_without_vip_key_not_mutated(self):
        for customer in ({}, {"name": "x"}):
            with self.subTest(customer=customer):
                items = [item("b", 200, 2), item("a", 100, 1)]
                customer_copy, items_copy = copy.deepcopy(customer), copy.deepcopy(items)
                r = calc(items, customer, "FIXED500")
                self.assertEqual(customer, customer_copy)
                self.assertEqual(items, items_copy)
                self.assertNotIn("vip", customer)
                self.assertEqual(r["vip_discount_cents"], 0)
        # tupla de itens e item único com tupla também não são alterados
        items = (item("a", 100, 1),)
        items_copy = copy.deepcopy(items)
        calc(items, {"vip": False}, "SAVE10")
        self.assertEqual(items, items_copy)

    # R8
    def test_r8_keys_and_default_coupon(self):
        r = calc([item("a", 100, 1)], {})
        self.assertEqual(
            list(sorted(r)),
            sorted(["subtotal_cents", "vip_discount_cents", "coupon_discount_cents",
                    "taxable_cents", "tax_cents", "total_cents"]),
        )
        self.assertEqual(r, calc([item("a", 100, 1)], {}, coupon=None))


if __name__ == "__main__":
    unittest.main()
