"""Reserva de estoque."""

from copy import deepcopy


class InvalidRequestError(ValueError):
    pass


class InsufficientStockError(Exception):
    pass


class KeyConflictError(Exception):
    pass


class InventoryService:
    def __init__(self, stock):
        self._validate_stock(stock)
        self._stock = dict(stock)
        self._reservations = {}
        self._events = []

    @staticmethod
    def _validate_stock(stock):
        if not isinstance(stock, dict):
            raise InvalidRequestError("stock must be a dict")
        for sku, quantity in stock.items():
            if not isinstance(sku, str):
                raise InvalidRequestError("stock SKUs must be strings")
            if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 0:
                raise InvalidRequestError("stock quantities must be non-negative integers")

    @staticmethod
    def _normalize_key(reservation_key):
        if not isinstance(reservation_key, str):
            raise InvalidRequestError("reservation_key must be a non-empty string")
        key = reservation_key.strip()
        if not key:
            raise InvalidRequestError("reservation_key must be a non-empty string")
        return key

    def _validate_items(self, items):
        if not isinstance(items, dict) or not items:
            raise InvalidRequestError("items must be a non-empty dict")
        normalized = {}
        for sku, quantity in items.items():
            if not isinstance(sku, str) or sku not in self._stock:
                raise InvalidRequestError("unknown SKU")
            if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
                raise InvalidRequestError("quantities must be positive integers")
            normalized[sku] = quantity
        return normalized

    def available(self, sku):
        if not isinstance(sku, str) or sku not in self._stock:
            raise InvalidRequestError("unknown SKU")
        return self._stock[sku]

    @property
    def events(self):
        return deepcopy(self._events)

    def reserve(self, reservation_key, items):
        key = self._normalize_key(reservation_key)
        requested = self._validate_items(items)

        previous = self._reservations.get(key)
        if previous is not None:
            if previous != requested:
                raise KeyConflictError(key)
            return {"reservation_key": key, "items": dict(previous), "replayed": True}

        for sku, qty in requested.items():
            if self._stock[sku] < qty:
                raise InsufficientStockError(sku)
        for sku, qty in requested.items():
            self._stock[sku] -= qty

        stored_items = dict(requested)
        self._reservations[key] = stored_items
        self._events.append(
            {"type": "reservation_created", "reservation_key": key, "items": dict(stored_items)}
        )
        return {"reservation_key": key, "items": dict(stored_items), "replayed": False}
