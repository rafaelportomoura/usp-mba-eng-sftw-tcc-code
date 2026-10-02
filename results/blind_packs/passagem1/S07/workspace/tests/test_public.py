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

    def test_r4_coupon_is_normalized_and_fixed_is_capped(self):
        result = calculate_order([item("a", 300, 1)], {}, "  fixed500 ")
        self.assertEqual(result["coupon_discount_cents"], 300)
        self.assertEqual(result["taxable_cents"], 0)

    def test_r3_and_r4_are_applied_in_order(self):
        result = calculate_order([item("a", 10000, 1)], {"vip": True}, "SAVE10")
        self.assertEqual(result["vip_discount_cents"], 1000)
        self.assertEqual(result["coupon_discount_cents"], 900)
        self.assertEqual(result["taxable_cents"], 8100)

    def test_r6_rounds_each_percentage_half_up(self):
        result = calculate_order([item("a", 5, 1)], {"vip": True}, "SAVE10")
        self.assertEqual(result["vip_discount_cents"], 1)
        self.assertEqual(result["coupon_discount_cents"], 0)
        self.assertEqual(result["taxable_cents"], 4)
        self.assertEqual(result["tax_cents"], 0)

        tax_result = calculate_order((item("a", 5, 1),), {})
        self.assertEqual(tax_result["tax_cents"], 1)

    def test_r1_rejects_invalid_values(self):
        invalid_cases = [
            ([], {}),
            ([item("", 1, 1)], {}),
            ([item("a", -1, 1)], {}),
            ([item("a", True, 1)], {}),
            ([item("a", 1, 0)], {}),
            ([item("a", 1, True)], {}),
            ([item("a", 1, 1)], []),
            ([item("a", 1, 1)], {"vip": 1}),
        ]
        for args in invalid_cases:
            with self.subTest(args=args):
                with self.assertRaises(ValueError):
                    calculate_order(*args)

    def test_r1_rejects_invalid_coupon(self):
        with self.assertRaises(ValueError):
            calculate_order([item("a", 1, 1)], {}, "NOPE")
        with self.assertRaises(ValueError):
            calculate_order([item("a", 1, 1)], {}, 10)

    def test_r7_does_not_mutate_inputs(self):
        items = [item("b", 100, 1), item("a", 200, 2)]
        customer = {"vip": True}
        original_items = [dict(entry) for entry in items]
        original_customer = dict(customer)
        calculate_order(items, customer)
        self.assertEqual(items, original_items)
        self.assertEqual(customer, original_customer)


if __name__ == "__main__":
    unittest.main()
