# EVALUATION-ONLY: variante de avaliacao; nao fornecer ao agente avaliado.

from decimal import Decimal, ROUND_HALF_UP
from copy import deepcopy
class ValidationError(ValueError): pass
def _pct(v, pct):
    return int((Decimal(v) * Decimal(pct) / Decimal(100)).to_integral_value(rounding=ROUND_HALF_UP))
def _check(items, customer, coupon):
    if not isinstance(items,(list,tuple)) or len(items)==0: raise ValidationError
    for i in items:
        if not isinstance(i,dict): raise ValidationError
        s,p,q=i.get('sku'),i.get('unit_price_cents'),i.get('quantity')
        if not (isinstance(s,str) and s): raise ValidationError
        if type(p) is not int or p<0: raise ValidationError
        if type(q) is not int or q<=0: raise ValidationError
    if not isinstance(customer,dict): raise ValidationError
    if 'vip' in customer and type(customer['vip']) is not bool: raise ValidationError
    if coupon is not None and not isinstance(coupon,str): raise ValidationError
def calculate_order(items, customer, coupon=None):
    _check(items, customer, coupon)
    code = None if coupon is None else coupon.strip().upper()
    if code not in (None,'SAVE10','FIXED500'): raise ValidationError
    sub = sum(i['unit_price_cents']*i['quantity'] for i in items)
    vip = _pct(sub,10) if customer.get('vip') is True else 0
    rem = sub-vip
    cd = _pct(rem,10) if code=='SAVE10' else min(500,rem) if code=='FIXED500' else 0
    tx = rem-cd
    tax=_pct(tx,10)
    return dict(subtotal_cents=sub,vip_discount_cents=vip,coupon_discount_cents=cd,taxable_cents=tx,tax_cents=tax,total_cents=tx+tax)
