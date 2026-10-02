"""Reserva de estoque (baseline incompleto)."""


class InvalidRequestError(ValueError):
    pass


class InsufficientStockError(Exception):
    pass


class KeyConflictError(Exception):
    pass


class InventoryService:
    def __init__(self, stock):
        self._stock = stock
        self.events = []

    def available(self, sku):
        return self._stock.get(sku, 0)

    def reserve(self, reservation_key, items):
        for sku, qty in items.items():
            if self._stock.get(sku, 0) < qty:
                raise InsufficientStockError(sku)
            self._stock[sku] -= qty
        self.events.append(
            {"type": "reservation_created", "reservation_key": reservation_key, "items": items}
        )
        return {"reservation_key": reservation_key, "items": items, "replayed": False}
