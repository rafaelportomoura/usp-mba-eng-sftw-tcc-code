import unittest

from inventory import (
    InsufficientStockError,
    InvalidRequestError,
    InventoryService,
    KeyConflictError,
)


class PublicInventoryTests(unittest.TestCase):
    def setUp(self):
        self.service = InventoryService({"A": 10, "B": 2})

    def test_r3_reserve_deducts_and_returns(self):
        result = self.service.reserve("k1", {"A": 3})
        self.assertEqual(result, {"reservation_key": "k1", "items": {"A": 3}, "replayed": False})
        self.assertEqual(self.service.available("A"), 7)

    def test_r2_insufficient_stock_raises(self):
        with self.assertRaises(InsufficientStockError):
            self.service.reserve("k1", {"B": 5})
        self.assertEqual(self.service.available("B"), 2)

    def test_r1_unknown_sku(self):
        with self.assertRaises(InvalidRequestError):
            self.service.reserve("k1", {"Z": 1})

    def test_r4_idempotent_replay(self):
        self.service.reserve("k1", {"A": 3})
        again = self.service.reserve("k1", {"A": 3})
        self.assertTrue(again["replayed"])
        self.assertEqual(self.service.available("A"), 7)

    def test_r6_event_recorded(self):
        self.service.reserve("k1", {"A": 1})
        self.assertEqual(
            self.service.events,
            [{"type": "reservation_created", "reservation_key": "k1", "items": {"A": 1}}],
        )

    def test_validation_rejects_invalid_values_and_unknown_available(self):
        invalid_reservations = [
            ("", {"A": 1}),
            ("k", {}),
            ("k", {"A": 0}),
            ("k", {"A": True}),
            ("k", {"Z": 1}),
            ("k", {1: 1}),
        ]
        for key, items in invalid_reservations:
            with self.subTest(key=key, items=items):
                with self.assertRaises(InvalidRequestError):
                    self.service.reserve(key, items)
        for sku in ("Z", 1):
            with self.subTest(sku=sku):
                with self.assertRaises(InvalidRequestError):
                    self.service.available(sku)

    def test_constructor_validates_and_copies_stock(self):
        for stock in (None, {"A": -1}, {"A": True}, {1: 2}):
            with self.subTest(stock=stock):
                with self.assertRaises(InvalidRequestError):
                    InventoryService(stock)
        stock = {"A": 4}
        service = InventoryService(stock)
        stock["A"] = 0
        self.assertEqual(service.available("A"), 4)

    def test_reservation_normalizes_key_and_items_are_order_independent(self):
        result = self.service.reserve(" k1 ", {"A": 1, "B": 1})
        replay = self.service.reserve("k1", {"B": 1, "A": 1})
        self.assertEqual(result["reservation_key"], "k1")
        self.assertTrue(replay["replayed"])
        self.assertEqual(self.service.available("A"), 9)
        self.assertEqual(self.service.available("B"), 1)
        self.assertEqual(len(self.service.events), 1)

    def test_conflicting_key_does_not_change_state(self):
        self.service.reserve("k1", {"A": 1})
        before = self.service.events
        with self.assertRaises(KeyConflictError):
            self.service.reserve(" k1 ", {"A": 2})
        self.assertEqual(self.service.available("A"), 9)
        self.assertEqual(self.service.events, before)

    def test_insufficient_reservation_is_atomic(self):
        with self.assertRaises(InsufficientStockError):
            self.service.reserve("k1", {"A": 10, "B": 3})
        self.assertEqual(self.service.available("A"), 10)
        self.assertEqual(self.service.available("B"), 2)
        self.assertEqual(self.service.events, [])
        self.service.reserve("k1", {"A": 1})

    def test_returned_data_and_input_items_are_isolated(self):
        items = {"A": 2}
        result = self.service.reserve("k1", items)
        items["A"] = 99
        result["items"]["A"] = 99
        event = self.service.events
        event.append({})
        event[0]["items"]["A"] = 99
        self.assertEqual(self.service.available("A"), 8)
        self.assertEqual(self.service.events[0]["items"], {"A": 2})

    def test_invalid_repeated_key_is_validated_before_idempotency(self):
        self.service.reserve("k1", {"A": 1})
        with self.assertRaises(InvalidRequestError):
            self.service.reserve("k1", {"Z": 1})


if __name__ == "__main__":
    unittest.main()
