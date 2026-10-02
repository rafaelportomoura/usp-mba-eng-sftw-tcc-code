# EVALUATION-ONLY: variante de avaliacao; nao fornecer ao agente avaliado.

import threading
from copy import deepcopy
class InvalidRequestError(ValueError): pass
class InsufficientStockError(Exception): pass
class KeyConflictError(Exception): pass
def _int(v): return type(v) is int
class InventoryService:
    def __init__(self, stock):
        if not isinstance(stock, dict): raise InvalidRequestError('stock')
        for k, v in stock.items():
            if not isinstance(k, str) or not _int(v) or v < 0: raise InvalidRequestError('stock')
        self._lock = threading.RLock()
        self._s = {k: v for k, v in stock.items()}
        self._r = {}
        self._e = []
    def available(self, sku):
        with self._lock:
            if not isinstance(sku, str) or sku not in self._s: raise InvalidRequestError('sku')
            return self._s[sku]
    @property
    def events(self):
        with self._lock:
            return [{'type': e['type'], 'reservation_key': e['reservation_key'], 'items': dict(e['items'])} for e in self._e]
    def reserve(self, reservation_key, items):
        with self._lock:
            if not isinstance(reservation_key, str) or reservation_key.strip() == '': raise InvalidRequestError('key')
            if not isinstance(items, dict) or len(items) == 0: raise InvalidRequestError('items')
            req = {}
            for k, v in items.items():
                if not isinstance(k, str) or k not in self._s or not _int(v) or v <= 0: raise InvalidRequestError('item')
                req[k] = v
            key = reservation_key.strip()
            if key in self._r:
                if self._r[key] != req: raise KeyConflictError(key)
                return {'reservation_key': key, 'items': dict(self._r[key]), 'replayed': True}
            short = [k for k, v in req.items() if self._s[k] < v]
            if short: raise InsufficientStockError(short[0])
            new = dict(self._s)
            for k, v in req.items(): new[k] -= v
            self._s = new
            self._r[key] = dict(req)
            self._e.append({'type': 'reservation_created', 'reservation_key': key, 'items': dict(req)})
            return {'reservation_key': key, 'items': dict(req), 'replayed': False}
