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

    def test_validation_and_available_reject_invalid_values(self):
        invalid_reservations = [
            ("", {"A": 1}),
            ("   ", {"A": 1}),
            ("k", {}),
            ("k", {"A": 0}),
            ("k", {"A": True}),
            ("k", {"Z": 1}),
        ]
        for key, items in invalid_reservations:
            with self.subTest(key=key, items=items):
                with self.assertRaises(InvalidRequestError):
                    self.service.reserve(key, items)
        for sku in ("Z", 1, None):
            with self.subTest(sku=sku):
                with self.assertRaises(InvalidRequestError):
                    self.service.available(sku)

    def test_invalid_request_is_checked_before_existing_key(self):
        self.service.reserve("k1", {"A": 1})
        with self.assertRaises(InvalidRequestError):
            self.service.reserve(" k1 ", {"A": 0})

    def test_normalized_key_and_conflict_do_not_change_state(self):
        self.service.reserve(" k1 ", {"A": 1, "B": 1})
        with self.assertRaises(KeyConflictError):
            self.service.reserve("k1", {"A": 2})
        self.assertEqual(self.service.available("A"), 9)
        self.assertEqual(len(self.service.events), 1)

    def test_insufficient_stock_is_atomic(self):
        with self.assertRaises(InsufficientStockError):
            self.service.reserve("k1", {"A": 10, "B": 3})
        self.assertEqual(self.service.available("A"), 10)
        self.assertEqual(self.service.available("B"), 2)
        self.assertEqual(self.service.events, [])

    def test_constructor_and_inputs_are_copied(self):
        stock = {"A": 3}
        service = InventoryService(stock)
        stock["A"] = 0
        self.assertEqual(service.available("A"), 3)

        items = {"A": 1}
        service.reserve("k1", items)
        items["A"] = 99
        self.assertEqual(service.events[0]["items"], {"A": 1})

    def test_events_are_deep_copied(self):
        self.service.reserve("k1", {"A": 1})
        events = self.service.events
        events.clear()
        events = self.service.events
        events[0]["items"]["A"] = 99
        self.assertEqual(
            self.service.events,
            [{"type": "reservation_created", "reservation_key": "k1", "items": {"A": 1}}],
        )

    def test_constructor_rejects_invalid_stock(self):
        for stock in ([], {"A": -1}, {"A": True}, {1: 2}):
            with self.subTest(stock=stock):
                with self.assertRaises(InvalidRequestError):
                    InventoryService(stock)


if __name__ == "__main__":
    unittest.main()
