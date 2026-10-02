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

    def test_percentages_round_half_up_individually_and_coupon_is_after_vip(self):
        result = calculate_order([item("a", 15, 1)], {"vip": True}, "SAVE10")
        self.assertEqual(result, {
            "subtotal_cents": 15,
            "vip_discount_cents": 2,
            "coupon_discount_cents": 1,
            "taxable_cents": 12,
            "tax_cents": 1,
            "total_cents": 13,
        })

    def test_fixed_coupon_is_capped(self):
        result = calculate_order([item("a", 100, 1)], {}, " fixed500 ")
        self.assertEqual(result["coupon_discount_cents"], 100)
        self.assertEqual(result["taxable_cents"], 0)

    def test_validation_rejects_invalid_values(self):
        invalid_orders = [
            ([], {}),
            ([item("", 1, 1)], {}),
            ([item("a", True, 1)], {}),
            ([item("a", 1, False)], {}),
            ([item("a", -1, 1)], {}),
            ([item("a", 1, 0)], {}),
            ([item("a", 1, 1)], {"vip": 1}),
        ]
        for args in invalid_orders:
            with self.subTest(args=args):
                with self.assertRaises(ValueError):
                    calculate_order(*args)
        with self.assertRaises(ValueError):
            calculate_order([item("a", 1, 1)], {}, "unknown")
        with self.assertRaises(ValueError):
            calculate_order([item("a", 1, 1)], {}, 10)

    def test_invalid_containers_raise_value_error(self):
        for items, customer in ((None, {}), ([None], {}), ([item("a", 1, 1)], None)):
            with self.subTest(items=items, customer=customer):
                with self.assertRaises(ValueError):
                    calculate_order(items, customer)

    def test_does_not_mutate_inputs(self):
        items = [item("b", 100, 1), item("a", 200, 2)]
        original_items = [dict(entry) for entry in items]
        customer = {"vip": True}
        original_customer = dict(customer)
        calculate_order(items, customer, "SAVE10")
        self.assertEqual(items, original_items)
        self.assertEqual(customer, original_customer)


if __name__ == "__main__":
    unittest.main()
