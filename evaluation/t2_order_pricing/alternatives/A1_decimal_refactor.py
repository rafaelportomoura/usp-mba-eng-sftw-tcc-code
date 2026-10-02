# EVALUATION-ONLY: mutante/alternativa de regressao do oraculo; nao fornecer ao agente avaliado.

from decimal import Decimal, ROUND_HALF_UP
from numbers import Integral
def _hu(amount, pct):
    return int((Decimal(amount)*Decimal(pct)/Decimal(100)).quantize(Decimal(1), rounding=ROUND_HALF_UP))
def _is_int(v): return type(v) is int
def _line(it):
    if not isinstance(it, dict): raise ValueError("item")
    if not isinstance(it.get("sku"), str) or it["sku"]=="" : raise ValueError("sku")
    if not _is_int(it.get("unit_price_cents")) or it["unit_price_cents"]<0: raise ValueError("price")
    if not _is_int(it.get("quantity")) or it["quantity"]<=0: raise ValueError("qty")
    return it["unit_price_cents"]*it["quantity"]
def _coupon(coupon, base):
    if coupon is None: return 0
    if not isinstance(coupon,str): raise ValueError
    code=coupon.strip().upper()
    if code=="SAVE10": return _hu(base,10)
    if code=="FIXED500": return min(500, base)
    raise ValueError
def calculate_order(items, customer, coupon=None):
    if not isinstance(customer, dict): raise ValueError
    vip=customer.get("vip", False)
    if not isinstance(vip,bool): raise ValueError
    if not isinstance(items,(list,tuple)) or len(items)==0: raise ValueError
    subtotal=sum(_line(i) for i in items)
    vd=_hu(subtotal,10) if vip else 0
    cd=_coupon(coupon, subtotal-vd)
    taxable=subtotal-vd-cd
    tax=_hu(taxable,10)
    return dict(subtotal_cents=subtotal,vip_discount_cents=vd,coupon_discount_cents=cd,taxable_cents=taxable,tax_cents=tax,total_cents=taxable+tax)
