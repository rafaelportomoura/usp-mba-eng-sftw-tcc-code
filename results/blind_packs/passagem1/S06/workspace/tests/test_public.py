import unittest
from copy import deepcopy

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

    def test_discounts_are_sequential_and_taxable(self):
        result = calculate_order([item("a", 105, 1)], {"vip": True}, "SAVE10")
        self.assertEqual(result["vip_discount_cents"], 11)
        self.assertEqual(result["coupon_discount_cents"], 9)
        self.assertEqual(result["taxable_cents"], 85)
        self.assertEqual(result["tax_cents"], 9)
        self.assertEqual(result["total_cents"], 94)

    def test_coupon_is_normalized_and_fixed_coupon_is_capped(self):
        result = calculate_order([item("a", 300, 1)], {}, "  fixed500 ")
        self.assertEqual(result["coupon_discount_cents"], 300)
        self.assertEqual(result["taxable_cents"], 0)

    def test_validation_rejects_invalid_values(self):
        invalid_items = [
            [],
            [item("", 1, 1)],
            [item("a", -1, 1)],
            [item("a", 1, 0)],
            [item("a", True, 1)],
            [item("a", 1, True)],
        ]
        for invalid in invalid_items:
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValueError):
                    calculate_order(invalid, {})
        with self.assertRaises(ValueError):
            calculate_order([item("a", 1, 1)], {"vip": 1})
        with self.assertRaises(ValueError):
            calculate_order([item("a", 1, 1)], {}, "unknown")

    def test_inputs_are_not_mutated(self):
        items = [item("b", 10, 1), item("a", 20, 2)]
        customer = {"vip": True}
        original_items = deepcopy(items)
        original_customer = deepcopy(customer)
        calculate_order(items, customer)
        self.assertEqual(items, original_items)
        self.assertEqual(customer, original_customer)


if __name__ == "__main__":
    unittest.main()
