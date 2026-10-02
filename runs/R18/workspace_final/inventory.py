"""Reserva de estoque (baseline incompleto)."""


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
            if not isinstance(sku, str) or not isinstance(quantity, int) or isinstance(quantity, bool) or quantity < 0:
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
        if not isinstance(reservation_key, str) or not reservation_key.strip():
            raise InvalidRequestError("reservation_key must be a non-empty string")
        if not isinstance(items, dict) or not items:
            raise InvalidRequestError("items must be a non-empty dict")

        key = reservation_key.strip()
        requested = {}
        for sku, quantity in items.items():
            if not isinstance(sku, str) or sku not in self._stock:
                raise InvalidRequestError("unknown SKU")
            if not isinstance(quantity, int) or isinstance(quantity, bool) or quantity <= 0:
                raise InvalidRequestError("quantities must be positive integers")
            requested[sku] = quantity

        previous = self._reservations.get(key)
        if previous is not None:
            if previous != requested:
                raise KeyConflictError(key)
            return {
                "reservation_key": key,
                "items": dict(previous),
                "replayed": True,
            }

        for sku, quantity in requested.items():
            if self._stock[sku] < quantity:
                raise InsufficientStockError(sku)

        for sku, quantity in requested.items():
            self._stock[sku] -= quantity

        self._reservations[key] = dict(requested)
        self._events.append(
            {"type": "reservation_created", "reservation_key": key, "items": dict(requested)}
        )
        return {"reservation_key": key, "items": dict(requested), "replayed": False}
