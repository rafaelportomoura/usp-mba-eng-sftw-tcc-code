# EVALUATION-ONLY: mutante/alternativa de regressao do oraculo; nao fornecer ao agente avaliado.

import copy
from fractions import Fraction
import math
class _Order:
    def __init__(self, items, customer, coupon):
        self.items = copy.deepcopy(list(items)) if isinstance(items,(list,tuple)) else None
        self.customer = copy.deepcopy(customer)
        self.coupon = coupon
        self.validate()
    def validate(self):
        if not self.items: raise ValueError
        if not isinstance(self.customer, dict): raise ValueError
        v = self.customer.get("vip", False)
        if v is not True and v is not False: raise ValueError
        for it in self.items:
            if not isinstance(it,dict): raise ValueError
            try:
                s,p,q = it["sku"],it["unit_price_cents"],it["quantity"]
            except KeyError: raise ValueError
            if not (isinstance(s,str) and s): raise ValueError
            for n,lo in ((p,0),(q,1)):
                if type(n) is not int or n<lo: raise ValueError
        if self.coupon is not None and not isinstance(self.coupon,str): raise ValueError
        if self.coupon is not None and self.coupon.strip().upper() not in ("SAVE10","FIXED500"): raise ValueError
    @staticmethod
    def pct(n, num, den): return math.floor(Fraction(n*num, den) + Fraction(1,2))
    def run(self):
        sub = sum(i["unit_price_cents"]*i["quantity"] for i in self.items)
        vip = self.pct(sub,1,10) if self.customer.get("vip") else 0
        rest = sub - vip
        c = (self.coupon or "").strip().upper()
        cd = self.pct(rest,1,10) if c=="SAVE10" else (min(500,rest) if c=="FIXED500" else 0)
        tx = rest - cd
        t = self.pct(tx,1,10)
        return {"subtotal_cents":sub,"vip_discount_cents":vip,"coupon_discount_cents":cd,"taxable_cents":tx,"tax_cents":t,"total_cents":tx+t}
def calculate_order(items, customer, coupon=None):
    return _Order(items, customer, coupon).run()
