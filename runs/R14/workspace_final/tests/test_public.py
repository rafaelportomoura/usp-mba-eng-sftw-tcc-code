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

    def test_normalizes_keys_and_replays_regardless_of_item_order(self):
        first = self.service.reserve("  k1 ", {"A": 1, "B": 1})
        replay = self.service.reserve("k1", {"B": 1, "A": 1})
        self.assertEqual(first["reservation_key"], "k1")
        self.assertTrue(replay["replayed"])
        self.assertEqual(self.service.available("A"), 9)
        self.assertEqual(self.service.available("B"), 1)
        self.assertEqual(len(self.service.events), 1)

    def test_conflict_does_not_change_state(self):
        self.service.reserve("k1", {"A": 1})
        with self.assertRaises(KeyConflictError):
            self.service.reserve(" k1 ", {"A": 2})
        self.assertEqual(self.service.available("A"), 9)
        self.assertEqual(len(self.service.events), 1)

    def test_input_and_event_results_are_isolated(self):
        stock = {"A": 4}
        service = InventoryService(stock)
        request = {"A": 2}
        result = service.reserve("k", request)
        stock["A"] = 99
        request["A"] = 99
        result["items"]["A"] = 99
        events = service.events
        events[0]["items"]["A"] = 99
        events.clear()
        self.assertEqual(service.available("A"), 2)
        self.assertEqual(service.events[0]["items"], {"A": 2})

    def test_validation_rejects_bool_empty_and_unknown_values(self):
        for key, items in (("", {"A": 1}), ("k", {}), ("k", {"A": True}),
                           ("k", {"Z": 1}), ("k", {"A": 0})):
            with self.assertRaises(InvalidRequestError):
                self.service.reserve(key, items)
        with self.assertRaises(InvalidRequestError):
            self.service.available("Z")
        with self.assertRaises(InvalidRequestError):
            self.service.available(1)

    def test_insufficient_request_is_atomic(self):
        with self.assertRaises(InsufficientStockError):
            self.service.reserve("k", {"A": 10, "B": 3})
        self.assertEqual(self.service.available("A"), 10)
        self.assertEqual(self.service.available("B"), 2)
        self.assertEqual(self.service.events, [])

    def test_constructor_validates_and_copies_stock(self):
        with self.assertRaises(InvalidRequestError):
            InventoryService({"A": True})
        with self.assertRaises(InvalidRequestError):
            InventoryService({1: 2})
        stock = {"A": 2}
        service = InventoryService(stock)
        stock["A"] = 0
        self.assertEqual(service.available("A"), 2)


if __name__ == "__main__":
    unittest.main()
