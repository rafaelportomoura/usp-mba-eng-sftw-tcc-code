import unittest

from pricing import calculate_order


def item(sku, price, qty):
    return {"sku": sku, "unit_price_cents": price, "quantity": qty}


class PublicPricingTests(unittest.TestCase):
    def test_r8_result_keys(self):
        result = calculate_order([item("a", 1000, 1)], {})
        self.assertEqual(
            set(result),
            {"subtotal_cents", "vip_discount_cents", "coupon_discount_cents",
             "taxable_cents", "tax_cents", "total_cents"},
        )

    def test_r2_r5_plain_order(self):
        result = calculate_order([item("a", 1000, 2), item("b", 500, 1)], {})
        self.assertEqual(result["subtotal_cents"], 2500)
        self.assertEqual(result["tax_cents"], 250)
        self.assertEqual(result["total_cents"], 2750)

    def test_r3_vip_discount(self):
        result = calculate_order([item("a", 10000, 1)], {"vip": True})
        self.assertEqual(result["vip_discount_cents"], 1000)
        self.assertEqual(result["taxable_cents"], 9000)

    def test_r4_save10_discount_amount(self):
        result = calculate_order([item("a", 10000, 1)], {}, "SAVE10")
        self.assertEqual(result["coupon_discount_cents"], 1000)

    def test_r1_rejects_invalid_inputs(self):
        invalid_orders = [[], [item("", 100, 1)], [item("a", -1, 1)],
                          [item("a", True, 1)], [item("a", 100, 0)],
                          [item("a", 100, True)]]
        for invalid_items in invalid_orders:
            with self.subTest(items=invalid_items):
                with self.assertRaises(ValueError):
                    calculate_order(invalid_items, {})
        with self.assertRaises(ValueError):
            calculate_order([item("a", 100, 1)], [])
        with self.assertRaises(ValueError):
            calculate_order([item("a", 100, 1)], {"vip": 1})
        with self.assertRaises(ValueError):
            calculate_order([item("a", 100, 1)], {}, 10)

    def test_r4_coupon_is_normalized_and_applied_after_vip(self):
        result = calculate_order([item("a", 10000, 1)], {"vip": True}, " save10 ")
        self.assertEqual(result["coupon_discount_cents"], 900)
        self.assertEqual(result["taxable_cents"], 8100)

    def test_r4_fixed_coupon_is_capped(self):
        result = calculate_order([item("a", 100, 1)], {}, "FIXED500")
        self.assertEqual(result["coupon_discount_cents"], 100)
        self.assertEqual(result["taxable_cents"], 0)
        with self.assertRaises(ValueError):
            calculate_order([item("a", 100, 1)], {}, "NOPE")

    def test_r6_rounds_each_percentage_without_floating_point(self):
        result = calculate_order([item("a", 5, 1)], {"vip": True})
        self.assertEqual(result["vip_discount_cents"], 1)
        self.assertEqual(result["taxable_cents"], 4)
        self.assertEqual(result["tax_cents"], 0)
        self.assertEqual(calculate_order([item("a", 5, 1)], {})["tax_cents"], 1)

    def test_r7_does_not_mutate_inputs(self):
        items = [item("b", 500, 1), item("a", 1000, 2)]
        original_items = [dict(value) for value in items]
        customer = {"vip": True}
        calculate_order(items, customer, "FIXED500")
        self.assertEqual(items, original_items)
        self.assertEqual(customer, {"vip": True})


if __name__ == "__main__":
    unittest.main()
