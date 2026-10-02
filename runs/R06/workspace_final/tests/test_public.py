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

    def test_keys_are_normalized_and_conflicts_are_detected(self):
        result = self.service.reserve("  k1 ", {"A": 1, "B": 1})
        self.assertEqual(result["reservation_key"], "k1")
        replay = self.service.reserve("k1", {"B": 1, "A": 1})
        self.assertTrue(replay["replayed"])
        with self.assertRaises(KeyConflictError):
            self.service.reserve(" k1 ", {"A": 2})

    def test_event_and_input_data_are_isolated(self):
        stock = {"A": 4}
        items = {"A": 2}
        service = InventoryService(stock)
        service.reserve("k", items)
        stock["A"] = 0
        items["A"] = 99
        events = service.events
        events[0]["items"]["A"] = 99
        events.append({"type": "fake"})
        self.assertEqual(service.available("A"), 2)
        self.assertEqual(service.events[0]["items"], {"A": 2})
        self.assertEqual(len(service.events), 1)

    def test_validation_rejects_invalid_types_and_precedes_replay_lookup(self):
        service = InventoryService({"A": 2})
        service.reserve("k", {"A": 1})
        with self.assertRaises(InvalidRequestError):
            service.reserve("k", {"A": True})
        with self.assertRaises(InvalidRequestError):
            service.available("missing")
        with self.assertRaises(InvalidRequestError):
            InventoryService({"A": True})

    def test_insufficient_multi_item_reservation_is_atomic(self):
        with self.assertRaises(InsufficientStockError):
            self.service.reserve("k", {"A": 10, "B": 3})
        self.assertEqual(self.service.available("A"), 10)
        self.assertEqual(self.service.available("B"), 2)
        self.assertEqual(self.service.events, [])


if __name__ == "__main__":
    unittest.main()
