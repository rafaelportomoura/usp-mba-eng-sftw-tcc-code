import unittest

from inventory import InsufficientStockError, InvalidRequestError, InventoryService, KeyConflictError


class RequirementsTests(unittest.TestCase):
    def test_constructor_validates_and_copies_stock(self):
        stock = {"A": 4}
        service = InventoryService(stock)
        stock["A"] = 0
        self.assertEqual(service.available("A"), 4)
        for invalid in ({"A": True}, {"A": -1}, {1: 2}, [], None):
            with self.subTest(invalid=invalid):
                with self.assertRaises(InvalidRequestError):
                    InventoryService(invalid)

    def test_request_validation_and_unknown_available(self):
        service = InventoryService({"A": 4})
        invalid_requests = [("", {"A": 1}), ("k", {}), ("k", {"A": 0}), ("k", {"A": True}), ("k", {"Z": 1})]
        for key, items in invalid_requests:
            with self.subTest(key=key, items=items):
                with self.assertRaises(InvalidRequestError):
                    service.reserve(key, items)
        with self.assertRaises(InvalidRequestError):
            service.available("Z")
        with self.assertRaises(InvalidRequestError):
            service.available(1)

    def test_validation_precedes_replay_conflict_lookup(self):
        service = InventoryService({"A": 2})
        service.reserve(" k ", {"A": 1})
        with self.assertRaises(InvalidRequestError):
            service.reserve("k", {"Z": 1})

    def test_atomic_insufficient_does_not_change_stock_or_events(self):
        service = InventoryService({"A": 2, "B": 5})
        with self.assertRaises(InsufficientStockError):
            service.reserve("k", {"A": 1, "B": 6})
        self.assertEqual(service.available("A"), 2)
        self.assertEqual(service.available("B"), 5)
        self.assertEqual(service.events, [])

    def test_normalized_key_replay_and_conflict(self):
        service = InventoryService({"A": 5, "B": 5})
        service.reserve(" k ", {"A": 2, "B": 1})
        result = service.reserve("k", {"B": 1, "A": 2})
        self.assertTrue(result["replayed"])
        self.assertEqual(len(service.events), 1)
        with self.assertRaises(KeyConflictError):
            service.reserve("k", {"A": 1})
        self.assertEqual(service.available("A"), 3)

    def test_events_are_deep_copies_and_input_is_not_retained(self):
        service = InventoryService({"A": 3})
        items = {"A": 1}
        result = service.reserve("k", items)
        items["A"] = 99
        result["items"]["A"] = 99
        events = service.events
        events.append({"type": "fake"})
        events[0]["items"]["A"] = 99
        self.assertEqual(service.events, [{"type": "reservation_created", "reservation_key": "k", "items": {"A": 1}}])


if __name__ == "__main__":
    unittest.main()
