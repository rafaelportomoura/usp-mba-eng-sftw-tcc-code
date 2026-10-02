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

    def test_r4_replay_ignores_item_order(self):
        self.service.reserve("k1", {"A": 3, "B": 1})
        again = self.service.reserve("k1", {"B": 1, "A": 3})
        self.assertEqual(again["replayed"], True)
        self.assertEqual(len(self.service.events), 1)

    def test_r6_event_recorded(self):
        self.service.reserve("k1", {"A": 1})
        self.assertEqual(
            self.service.events,
            [{"type": "reservation_created", "reservation_key": "k1", "items": {"A": 1}}],
        )

    def test_validation_is_strict_and_precedes_replay(self):
        self.service.reserve(" k1 ", {"A": 1})
        with self.assertRaises(InvalidRequestError):
            self.service.reserve("k1", {"A": True})
        with self.assertRaises(InvalidRequestError):
            self.service.available("Z")

    def test_key_conflict_and_normalization(self):
        self.service.reserve(" k1 ", {"A": 1})
        with self.assertRaises(KeyConflictError):
            self.service.reserve("k1", {"A": 2})
        self.assertEqual(self.service.available("A"), 9)
        self.assertEqual(len(self.service.events), 1)

    def test_atomicity_and_isolation(self):
        stock = {"A": 3, "B": 2}
        items = {"A": 2}
        service = InventoryService(stock)
        service.reserve("k1", items)
        stock["A"] = 0
        items["A"] = 99
        self.assertEqual(service.available("A"), 1)
        returned_events = service.events
        returned_events[0]["items"]["A"] = 99
        returned_events.clear()
        self.assertEqual(service.events[0]["items"], {"A": 2})

        with self.assertRaises(InsufficientStockError):
            service.reserve("k2", {"A": 2, "B": 3})
        self.assertEqual(service.available("A"), 1)
        self.assertEqual(service.available("B"), 2)
        self.assertEqual(len(service.events), 1)

    def test_constructor_rejects_invalid_stock(self):
        with self.assertRaises(InvalidRequestError):
            InventoryService([])
        with self.assertRaises(InvalidRequestError):
            InventoryService({"A": True})
        with self.assertRaises(InvalidRequestError):
            InventoryService({"A": -1})


if __name__ == "__main__":
    unittest.main()
