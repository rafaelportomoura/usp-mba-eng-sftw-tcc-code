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
        if any(
            not isinstance(sku, str)
            or not isinstance(quantity, int)
            or isinstance(quantity, bool)
            or quantity < 0
            for sku, quantity in stock.items()
        ):
            raise InvalidRequestError("stock must contain str keys and non-negative int quantities")

        self._stock = stock.copy()
        self._reservations = {}
        self._event_log = []

    @property
    def events(self):
        return [
            {
                "type": event["type"],
                "reservation_key": event["reservation_key"],
                "items": event["items"].copy(),
            }
            for event in self._event_log
        ]

    def available(self, sku):
        if not isinstance(sku, str) or sku not in self._stock:
            raise InvalidRequestError("unknown sku")
        return self._stock[sku]

    def reserve(self, reservation_key, items):
        if not isinstance(reservation_key, str) or not reservation_key.strip():
            raise InvalidRequestError("reservation_key must be a non-empty string")
        if not isinstance(items, dict) or not items:
            raise InvalidRequestError("items must be a non-empty dict")

        key = reservation_key.strip()
        normalized_items = {}
        for sku, quantity in items.items():
            if (
                not isinstance(sku, str)
                or sku not in self._stock
                or not isinstance(quantity, int)
                or isinstance(quantity, bool)
                or quantity <= 0
            ):
                raise InvalidRequestError("items must contain known skus and positive int quantities")
            normalized_items[sku] = quantity

        previous = self._reservations.get(key)
        if previous is not None:
            if previous != normalized_items:
                raise KeyConflictError(key)
            return {
                "reservation_key": key,
                "items": normalized_items.copy(),
                "replayed": True,
            }

        for sku, quantity in normalized_items.items():
            if self._stock[sku] < quantity:
                raise InsufficientStockError(sku)

        for sku, quantity in normalized_items.items():
            self._stock[sku] -= quantity
        self._reservations[key] = normalized_items.copy()
        self._event_log.append(
            {
                "type": "reservation_created",
                "reservation_key": key,
                "items": normalized_items.copy(),
            }
        )
        return {
            "reservation_key": key,
            "items": normalized_items.copy(),
            "replayed": False,
        }
