"""Serviço de reservas de estoque."""


class InvalidRequestError(ValueError):
    pass


class InsufficientStockError(Exception):
    pass


class KeyConflictError(Exception):
    pass


class InventoryService:
    def __init__(self, stock):
        if not isinstance(stock, dict):
            raise InvalidRequestError("stock deve ser um dict")
        for sku, quantity in stock.items():
            if (
                not isinstance(sku, str)
                or not isinstance(quantity, int)
                or isinstance(quantity, bool)
                or quantity < 0
            ):
                raise InvalidRequestError("estoque inválido")

        self._stock = stock.copy()
        self._reservations = {}
        self._events = []

    @property
    def events(self):
        return [
            {
                "type": event["type"],
                "reservation_key": event["reservation_key"],
                "items": event["items"].copy(),
            }
            for event in self._events
        ]

    def available(self, sku):
        if not isinstance(sku, str) or sku not in self._stock:
            raise InvalidRequestError("sku desconhecido")
        return self._stock[sku]

    def reserve(self, reservation_key, items):
        key = self._validate_request(reservation_key, items)

        existing = self._reservations.get(key)
        if existing is not None:
            if existing == items:
                return {
                    "reservation_key": key,
                    "items": existing.copy(),
                    "replayed": True,
                }
            raise KeyConflictError(key)

        for sku, qty in items.items():
            if self._stock[sku] < qty:
                raise InsufficientStockError(sku)

        for sku, qty in items.items():
            self._stock[sku] -= qty

        stored_items = items.copy()
        self._reservations[key] = stored_items
        self._events.append(
            {"type": "reservation_created", "reservation_key": key, "items": stored_items.copy()}
        )
        return {"reservation_key": key, "items": stored_items.copy(), "replayed": False}

    def _validate_request(self, reservation_key, items):
        if not isinstance(reservation_key, str) or not reservation_key.strip():
            raise InvalidRequestError("reservation_key inválida")
        if not isinstance(items, dict) or not items:
            raise InvalidRequestError("items inválido")

        for sku, quantity in items.items():
            if not isinstance(sku, str) or sku not in self._stock:
                raise InvalidRequestError("sku desconhecido")
            if not isinstance(quantity, int) or isinstance(quantity, bool) or quantity <= 0:
                raise InvalidRequestError("quantidade inválida")
        return reservation_key.strip()
