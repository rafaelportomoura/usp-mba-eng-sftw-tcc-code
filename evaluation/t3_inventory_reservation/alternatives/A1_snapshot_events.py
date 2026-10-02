# EVALUATION-ONLY: mutante/alternativa de regressao do oraculo; nao fornecer ao agente avaliado.

from types import MappingProxyType
class InvalidRequestError(ValueError): pass
class InsufficientStockError(Exception): pass
class KeyConflictError(Exception): pass
def _okint(v): return type(v) is int
class InventoryService:
    def __init__(self, stock):
        if not isinstance(stock, dict): raise InvalidRequestError("stock")
        if any(not isinstance(k,str) or not _okint(v) or v<0 for k,v in stock.items()): raise InvalidRequestError("stock")
        self._s = {k:int(v) for k,v in stock.items()}
        self._seen = {}
        self._log = []
    def available(self, sku):
        try: return self._s[sku]
        except (KeyError, TypeError): raise InvalidRequestError("sku")
    @property
    def events(self):
        return [{"type":e[0],"reservation_key":e[1],"items":dict(e[2])} for e in self._log]
    def reserve(self, reservation_key, items):
        if not isinstance(reservation_key,str) or not reservation_key.strip(): raise InvalidRequestError("k")
        if not isinstance(items,dict) or not items: raise InvalidRequestError("i")
        for k,v in items.items():
            if not isinstance(k,str) or k not in self._s or not _okint(v) or v<=0: raise InvalidRequestError("i")
        k = reservation_key.strip()
        snap = tuple(sorted(items.items()))
        if k in self._seen:
            if self._seen[k] != snap: raise KeyConflictError(k)
            return {"reservation_key":k,"items":dict(snap),"replayed":True}
        short = [s for s,q in items.items() if self._s[s] < q]
        if short: raise InsufficientStockError(short)
        for s,q in items.items(): self._s[s] -= q
        self._seen[k] = snap
        self._log.append(("reservation_created", k, snap))
        return {"reservation_key":k,"items":dict(snap),"replayed":False}
