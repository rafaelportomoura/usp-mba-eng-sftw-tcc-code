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

    def test_key_is_stripped_and_conflicts_are_detected(self):
        self.service.reserve(" k1 ", {"A": 1})
        replay = self.service.reserve("k1", {"A": 1})
        self.assertEqual(replay["reservation_key"], "k1")
        self.assertTrue(replay["replayed"])
        with self.assertRaises(KeyConflictError):
            self.service.reserve(" k1", {"A": 2})
        self.assertEqual(self.service.available("A"), 9)
        self.assertEqual(len(self.service.events), 1)

    def test_events_are_fully_isolated(self):
        self.service.reserve("k1", {"A": 1})
        events = self.service.events
        events[0]["items"]["A"] = 99
        events.append({"type": "fake"})
        self.assertEqual(
            self.service.events,
            [{"type": "reservation_created", "reservation_key": "k1", "items": {"A": 1}}],
        )

    def test_inputs_are_copied_and_multi_item_failure_is_atomic(self):
        stock = {"A": 3, "B": 2}
        service = InventoryService(stock)
        items = {"A": 1}
        service.reserve("k1", items)
        stock["A"] = 99
        items["A"] = 99
        self.assertEqual(service.available("A"), 2)
        with self.assertRaises(InsufficientStockError):
            service.reserve("k2", {"A": 2, "B": 3})
        self.assertEqual(service.available("A"), 2)
        self.assertEqual(service.available("B"), 2)
        self.assertEqual(service.events, [{"type": "reservation_created", "reservation_key": "k1", "items": {"A": 1}}])

    def test_validation_rejects_bool_and_invalid_available(self):
        with self.assertRaises(InvalidRequestError):
            InventoryService({"A": True})
        for bad_items in ({}, [], {"A": True}, {"A": 0}, {"Z": 1}):
            with self.subTest(bad_items=bad_items):
                with self.assertRaises(InvalidRequestError):
                    self.service.reserve("k1", bad_items)
        for sku in ("Z", 1):
            with self.assertRaises(InvalidRequestError):
                self.service.available(sku)


if __name__ == "__main__":
    unittest.main()
