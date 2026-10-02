"""Reserva de estoque."""


class InvalidRequestError(ValueError):
    pass


class InsufficientStockError(Exception):
    pass


class KeyConflictError(Exception):
    pass


class InventoryService:
    def __init__(self, stock):
        if not isinstance(stock, dict):
            raise InvalidRequestError("stock must be a dict")
        for sku, quantity in stock.items():
            if (not isinstance(sku, str) or not isinstance(quantity, int)
                    or isinstance(quantity, bool) or quantity < 0):
                raise InvalidRequestError("stock must map string SKUs to non-negative integers")
        self._stock = dict(stock)
        self._reservations = {}
        self._events = []

    @property
    def events(self):
        return [
            {
                "type": event["type"],
                "reservation_key": event["reservation_key"],
                "items": dict(event["items"]),
            }
            for event in self._events
        ]

    def available(self, sku):
        if not isinstance(sku, str) or sku not in self._stock:
            raise InvalidRequestError("unknown SKU")
        return self._stock[sku]

    def reserve(self, reservation_key, items):
        key = self._validate_request(reservation_key, items)
        requested = dict(items)

        previous = self._reservations.get(key)
        if previous is not None:
            if previous != requested:
                raise KeyConflictError(key)
            return {"reservation_key": key, "items": dict(previous), "replayed": True}

        # Check all items before changing any quantity (atomic operation).
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

    def _validate_request(self, reservation_key, items):
        if not isinstance(reservation_key, str) or not reservation_key.strip():
            raise InvalidRequestError("reservation_key must be a non-empty string")
        if not isinstance(items, dict) or not items:
            raise InvalidRequestError("items must be a non-empty dict")
        for sku, qty in items.items():
            if not isinstance(sku, str) or sku not in self._stock:
                raise InvalidRequestError("unknown SKU")
            if not isinstance(qty, int) or isinstance(qty, bool) or qty <= 0:
                raise InvalidRequestError("quantities must be positive integers")
        return reservation_key.strip()
