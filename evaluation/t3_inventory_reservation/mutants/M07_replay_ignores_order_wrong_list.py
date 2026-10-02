# EVALUATION-ONLY: mutante/alternativa de regressao do oraculo; nao fornecer ao agente avaliado.
"""Reserva de estoque (solução de referência)."""

import copy


class InvalidRequestError(ValueError):
    pass


class InsufficientStockError(Exception):
    pass


class KeyConflictError(Exception):
    pass


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


class InventoryService:
    def __init__(self, stock):
        if not isinstance(stock, dict):
            raise InvalidRequestError("stock must be a dict")
        for sku, qty in stock.items():
            if not isinstance(sku, str) or not _is_int(qty) or qty < 0:
                raise InvalidRequestError("invalid stock entry")
        self._stock = dict(stock)
        self._reservations = {}
        self._events = []

    def available(self, sku):
        if not isinstance(sku, str) or sku not in self._stock:
            raise InvalidRequestError("unknown sku")
        return self._stock[sku]

    @property
    def events(self):
        return copy.deepcopy(self._events)

    def _validate(self, reservation_key, items):
        if not isinstance(reservation_key, str) or not reservation_key.strip():
            raise InvalidRequestError("invalid reservation_key")
        if not isinstance(items, dict) or not items:
            raise InvalidRequestError("items must be a non-empty dict")
        for sku, qty in items.items():
            if not isinstance(sku, str) or sku not in self._stock:
                raise InvalidRequestError("unknown sku")
            if not _is_int(qty) or qty <= 0:
                raise InvalidRequestError("invalid quantity")
        return reservation_key.strip(), dict(items)

    def reserve(self, reservation_key, items):
        key, requested = self._validate(reservation_key, items)
        previous = self._reservations.get(key)
        if previous is not None:
            if sorted(previous) != sorted(requested):
                raise KeyConflictError(key)
            return {"reservation_key": key, "items": dict(previous), "replayed": True}
        for sku, qty in requested.items():
            if self._stock[sku] < qty:
                raise InsufficientStockError(sku)
        for sku, qty in requested.items():
            self._stock[sku] -= qty
        self._reservations[key] = dict(requested)
        self._events.append(
            {"type": "reservation_created", "reservation_key": key, "items": dict(requested)}
        )
        return {"reservation_key": key, "items": dict(requested), "replayed": False}
