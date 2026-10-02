# EVALUATION-ONLY: variante de avaliacao; nao fornecer ao agente avaliado.

class InvalidRequestError(ValueError): pass
class InsufficientStockError(Exception): pass
class KeyConflictError(Exception): pass
class InventoryService:
    def __init__(self, stock):
        ok = isinstance(stock, dict) and all(isinstance(k, str) and isinstance(v, int) and not isinstance(v, bool) and v >= 0 for k, v in stock.items())
        if not ok: raise InvalidRequestError('bad stock')
        self.__stock = dict(stock)
        self.__log = []   # list of (key, tuple(sorted items))
    def available(self, sku):
        try:
            return self.__stock[sku]
        except (KeyError, TypeError):
            raise InvalidRequestError('sku')
    @property
    def events(self):
        return [{'type': 'reservation_created', 'reservation_key': k, 'items': dict(its)} for k, its in self.__log]
    def reserve(self, reservation_key, items):
        if not isinstance(reservation_key, str) or not reservation_key.strip(): raise InvalidRequestError('k')
        if not isinstance(items, dict) or not items: raise InvalidRequestError('i')
        for s, q in items.items():
            if not isinstance(s, str) or s not in self.__stock: raise InvalidRequestError('s')
            if not isinstance(q, int) or isinstance(q, bool) or q <= 0: raise InvalidRequestError('q')
        k = reservation_key.strip()
        norm = tuple(sorted(items.items()))
        for key, its in self.__log:
            if key == k:
                if its != norm: raise KeyConflictError(k)
                return {'reservation_key': k, 'items': dict(its), 'replayed': True}
        for s, q in norm:
            if self.__stock[s] < q: raise InsufficientStockError(s)
        for s, q in norm: self.__stock[s] -= q
        self.__log.append((k, norm))
        return {'reservation_key': k, 'items': dict(norm), 'replayed': False}
