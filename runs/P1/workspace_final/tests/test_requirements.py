import unittest

from inventory import (
    InsufficientStockError,
    InvalidRequestError,
    InventoryService,
    KeyConflictError,
)


class RequirementsInventoryTests(unittest.TestCase):
    def test_constructor_validates_and_copies_stock(self):
        stock = {"A": 3}
        service = InventoryService(stock)
        stock["A"] = 0
        self.assertEqual(service.available("A"), 3)

        for invalid in (None, {"A": True}, {"A": -1}, {1: 2}):
            with self.subTest(invalid=invalid):
                with self.assertRaises(InvalidRequestError):
                    InventoryService(invalid)

    def test_validation_precedes_replay_lookup(self):
        service = InventoryService({"A": 3})
        service.reserve(" key ", {"A": 1})
        with self.assertRaises(InvalidRequestError):
            service.reserve("key", {"A": 0})

    def test_normalized_key_and_conflict(self):
        service = InventoryService({"A": 3})
        first = service.reserve(" key ", {"A": 1})
        replay = service.reserve("key", {"A": 1})
        self.assertEqual(first["reservation_key"], "key")
        self.assertTrue(replay["replayed"])
        with self.assertRaises(KeyConflictError):
            service.reserve(" key ", {"A": 2})
        self.assertEqual(service.available("A"), 2)
        self.assertEqual(len(service.events), 1)

    def test_insufficient_multi_item_reservation_is_atomic(self):
        service = InventoryService({"A": 5, "B": 1})
        with self.assertRaises(InsufficientStockError):
            service.reserve("k", {"A": 2, "B": 2})
        self.assertEqual(service.available("A"), 5)
        self.assertEqual(service.available("B"), 1)
        self.assertEqual(service.events, [])

    def test_events_are_deep_copies(self):
        service = InventoryService({"A": 3})
        service.reserve("k", {"A": 1})
        events = service.events
        events.clear()
        events = service.events
        events[0]["items"]["A"] = 99
        events[0]["reservation_key"] = "changed"
        self.assertEqual(
            service.events,
            [{"type": "reservation_created", "reservation_key": "k", "items": {"A": 1}}],
        )

    def test_available_rejects_unknown_or_non_string_sku(self):
        service = InventoryService({"A": 1})
        for sku in ("Z", 1, None):
            with self.subTest(sku=sku):
                with self.assertRaises(InvalidRequestError):
                    service.available(sku)


if __name__ == "__main__":
    unittest.main()
