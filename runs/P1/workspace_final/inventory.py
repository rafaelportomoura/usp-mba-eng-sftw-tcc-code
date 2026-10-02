"""Reserva de estoque."""


class InvalidRequestError(ValueError):
    pass


class InsufficientStockError(Exception):
    pass


class KeyConflictError(Exception):
    pass


def _is_int(value):
    """Return whether value is an integer, but not a boolean."""
    return isinstance(value, int) and not isinstance(value, bool)


class InventoryService:
    def __init__(self, stock):
        if not isinstance(stock, dict):
            raise InvalidRequestError("stock must be a dict")
        if any(not isinstance(sku, str) or not _is_int(quantity) or quantity < 0
               for sku, quantity in stock.items()):
            raise InvalidRequestError("stock must map string skus to non-negative integers")

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
            raise InvalidRequestError("unknown sku")
        return self._stock[sku]

    def reserve(self, reservation_key, items):
        # Validate the complete request before looking up an existing key.
        if not isinstance(reservation_key, str) or not reservation_key.strip():
            raise InvalidRequestError("reservation_key must be a non-empty string")
        if not isinstance(items, dict) or not items:
            raise InvalidRequestError("items must be a non-empty dict")

        key = reservation_key.strip()
        requested = {}
        for sku, quantity in items.items():
            if not isinstance(sku, str) or sku not in self._stock:
                raise InvalidRequestError("unknown sku")
            if not _is_int(quantity) or quantity <= 0:
                raise InvalidRequestError("quantity must be a positive integer")
            requested[sku] = quantity

        if key in self._reservations:
            if self._reservations[key] != requested:
                raise KeyConflictError(key)
            return {"reservation_key": key, "items": dict(requested), "replayed": True}

        # Check all items before changing any item: reservation is atomic.
        for sku, quantity in requested.items():
            if self._stock[sku] < quantity:
                raise InsufficientStockError(sku)
        for sku, quantity in requested.items():
            self._stock[sku] -= quantity

        self._reservations[key] = dict(requested)
        self._events.append({
            "type": "reservation_created",
            "reservation_key": key,
            "items": dict(requested),
        })
        return {"reservation_key": key, "items": dict(requested), "replayed": False}
