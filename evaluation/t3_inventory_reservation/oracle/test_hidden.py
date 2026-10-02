# EVALUATION-ONLY: testes-oraculo ocultos; nao fornecer ao agente avaliado.
import unittest

from inventory import (
    InsufficientStockError,
    InvalidRequestError,
    InventoryService,
    KeyConflictError,
)


def make():
    return InventoryService({"A": 10, "B": 2, "C": 0})


class HiddenInventoryTests(unittest.TestCase):
    # R1
    def test_r1_invalid_key(self):
        s = make()
        for bad in ("", "   ", None, 5):
            with self.subTest(bad=bad):
                with self.assertRaises(InvalidRequestError):
                    s.reserve(bad, {"A": 1})

    def test_r1_invalid_items(self):
        s = make()
        for bad in ({}, None, [("A", 1)], "A"):
            with self.subTest(bad=bad):
                with self.assertRaises(InvalidRequestError):
                    s.reserve("k", bad)

    def test_r1_invalid_quantity(self):
        s = make()
        for bad in (0, -1, 1.0, True, "1", None):
            with self.subTest(bad=bad):
                with self.assertRaises(InvalidRequestError):
                    s.reserve("k", {"A": bad})
        self.assertEqual(s.available("A"), 10)

    def test_r1_unknown_sku_and_available(self):
        s = make()
        with self.assertRaises(InvalidRequestError):
            s.reserve("k", {"A": 1, "Z": 1})
        self.assertEqual(s.available("A"), 10)
        with self.assertRaises(InvalidRequestError):
            s.available("Z")

    def test_r1_invalid_error_is_value_error(self):
        self.assertTrue(issubclass(InvalidRequestError, ValueError))

    def test_r1_constructor_validation(self):
        for bad in (None, [], {"A": -1}, {"A": 1.5}, {"A": True}, {1: 1}):
            with self.subTest(bad=bad):
                with self.assertRaises(InvalidRequestError):
                    InventoryService(bad)

    def test_r1_invalid_request_does_not_register_key(self):
        s = make()
        with self.assertRaises(InvalidRequestError):
            s.reserve("k", {"Z": 1})
        self.assertEqual(s.reserve("k", {"A": 1})["replayed"], False)
        self.assertEqual(len(s.events), 1)

    def test_r1_available_non_str_sku(self):
        s = make()
        for bad in (5, None, [], ("A",), 1.5):
            with self.subTest(bad=bad):
                with self.assertRaises(InvalidRequestError):
                    s.available(bad)

    def test_r1_validation_precedes_existing_key_lookup(self):
        s = make()
        s.reserve("k", {"A": 2})
        for bad in ({"Z": 1}, {"A": 0}, {"A": True}, {}, None):
            with self.subTest(bad=bad):
                with self.assertRaises(InvalidRequestError):
                    s.reserve("k", bad)
        self.assertEqual(s.available("A"), 8)
        self.assertEqual(len(s.events), 1)

    # R2
    def test_r2_atomic_multi_item_failure(self):
        s = make()
        with self.assertRaises(InsufficientStockError):
            s.reserve("k", {"A": 5, "B": 3})
        self.assertEqual(s.available("A"), 10)
        self.assertEqual(s.available("B"), 2)
        self.assertEqual(s.events, [])

    def test_r2_failure_failing_item_listed_first(self):
        s = make()
        with self.assertRaises(InsufficientStockError):
            s.reserve("k", {"B": 3, "A": 5})
        self.assertEqual((s.available("A"), s.available("B")), (10, 2))

    def test_r2_failed_key_not_registered(self):
        s = make()
        with self.assertRaises(InsufficientStockError):
            s.reserve("k", {"B": 3})
        # a mesma chave pode ser reutilizada com itens diferentes (sem conflito)
        self.assertEqual(s.reserve("k", {"B": 1})["replayed"], False)
        self.assertEqual(s.available("B"), 1)

    def test_r2_exact_stock_allowed_and_zero_stock_rejected(self):
        s = make()
        s.reserve("k1", {"B": 2})
        self.assertEqual(s.available("B"), 0)
        with self.assertRaises(InsufficientStockError):
            s.reserve("k2", {"C": 1})

    # R3
    def test_r3_result_shape(self):
        s = make()
        self.assertEqual(
            s.reserve("k", {"A": 4, "B": 1}),
            {"reservation_key": "k", "items": {"A": 4, "B": 1}, "replayed": False},
        )
        self.assertEqual((s.available("A"), s.available("B")), (6, 1))

    def test_r3_key_is_normalized_in_result_and_event(self):
        s = make()
        result = s.reserve("  k1 ", {"A": 1})
        self.assertEqual(result["reservation_key"], "k1")
        self.assertEqual(s.events[0]["reservation_key"], "k1")
        again = s.reserve("k1  ", {"A": 1})
        self.assertEqual(again, {"reservation_key": "k1", "items": {"A": 1}, "replayed": True})

    # R4
    def test_r4_replay_same_result_any_order(self):
        s = make()
        first = s.reserve("k", {"A": 2, "B": 1})
        again = s.reserve("k", {"B": 1, "A": 2})
        self.assertEqual(again, {**first, "replayed": True})
        self.assertEqual((s.available("A"), s.available("B")), (8, 1))
        self.assertEqual(len(s.events), 1)

    def test_r4_replay_after_stock_exhausted(self):
        s = make()
        s.reserve("k", {"B": 2})
        self.assertTrue(s.reserve("k", {"B": 2})["replayed"])
        self.assertEqual(s.available("B"), 0)

    # R5
    def test_r5_conflict(self):
        s = make()
        s.reserve("k", {"A": 2})
        for other in ({"A": 3}, {"A": 2, "B": 1}, {"B": 1}):
            with self.subTest(other=other):
                with self.assertRaises(KeyConflictError):
                    s.reserve("k", other)
        self.assertEqual(s.available("A"), 8)
        self.assertEqual(len(s.events), 1)

    def test_r5_conflict_with_subset_or_changed_quantity_of_multi_item_key(self):
        s = make()
        s.reserve("k", {"A": 2, "B": 1})
        for other in ({"A": 2}, {"A": 1, "B": 1}, {"B": 1}):
            with self.subTest(other=other):
                with self.assertRaises(KeyConflictError):
                    s.reserve("k", other)
        self.assertTrue(s.reserve("k", {"B": 1, "A": 2})["replayed"])
        self.assertEqual((s.available("A"), s.available("B")), (8, 1))
        self.assertEqual(len(s.events), 1)

    def test_r5_key_compared_after_strip(self):
        s = make()
        s.reserve("k", {"A": 2})
        self.assertTrue(s.reserve("  k ", {"A": 2})["replayed"])
        with self.assertRaises(KeyConflictError):
            s.reserve(" k", {"A": 1})

    def test_r5_conflict_precedence_over_stock(self):
        s = make()
        s.reserve("k", {"B": 2})
        with self.assertRaises(KeyConflictError):
            s.reserve("k", {"B": 100})

    # R6
    def test_r6_events_chronological(self):
        s = make()
        s.reserve("k1", {"A": 1})
        s.reserve("k2", {"B": 1})
        s.reserve("k1", {"A": 1})
        self.assertEqual(
            s.events,
            [
                {"type": "reservation_created", "reservation_key": "k1", "items": {"A": 1}},
                {"type": "reservation_created", "reservation_key": "k2", "items": {"B": 1}},
            ],
        )

    def test_r6_events_is_copy(self):
        s = make()
        s.reserve("k", {"A": 1})
        evs = s.events
        evs.append({"x": 1})
        evs[0]["items"]["A"] = 99
        evs[0]["type"] = "tampered"
        evs[0]["reservation_key"] = "tampered"
        self.assertEqual(
            s.events, [{"type": "reservation_created", "reservation_key": "k", "items": {"A": 1}}]
        )

    def test_r6_no_events_on_failures(self):
        s = make()
        for call in (lambda: s.reserve("", {"A": 1}), lambda: s.reserve("k", {"A": 99})):
            with self.assertRaises(Exception):
                call()
        self.assertEqual(s.events, [])

    # R7
    def test_r7_stock_not_aliased(self):
        stock = {"A": 5}
        s = InventoryService(stock)
        s.reserve("k", {"A": 2})
        self.assertEqual(stock, {"A": 5})
        stock["A"] = 100
        self.assertEqual(s.available("A"), 3)

    def test_r7_items_not_aliased(self):
        s = make()
        items = {"A": 2}
        s.reserve("k", items)
        items["A"] = 9
        self.assertEqual(s.events[0]["items"], {"A": 2})
        self.assertEqual(s.reserve("k", {"A": 2})["items"], {"A": 2})
        self.assertEqual(items, {"A": 9})


if __name__ == "__main__":
    unittest.main()
