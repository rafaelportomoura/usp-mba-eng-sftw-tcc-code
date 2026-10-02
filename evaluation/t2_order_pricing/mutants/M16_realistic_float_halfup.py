# EVALUATION-ONLY: mutante/alternativa de regressao do oraculo; nao fornecer ao agente avaliado.

import math
def calculate_order(items, customer, coupon=None):
    if not isinstance(items,(list,tuple)) or not items: raise ValueError
    if not isinstance(customer,dict): raise ValueError
    if "vip" in customer and not isinstance(customer["vip"],bool): raise ValueError
    sub=0
    for it in items:
        if not isinstance(it,dict): raise ValueError
        s,p,q=it.get("sku"),it.get("unit_price_cents"),it.get("quantity")
        if not isinstance(s,str) or not s: raise ValueError
        if isinstance(p,bool) or not isinstance(p,int) or p<0: raise ValueError
        if isinstance(q,bool) or not isinstance(q,int) or q<=0: raise ValueError
        sub+=p*q
    hu=lambda x: int(math.floor(x+0.5))
    vip=hu(sub*0.10) if customer.get("vip") else 0
    rest=sub-vip
    d=0
    if coupon is not None:
        if not isinstance(coupon,str): raise ValueError
        c=coupon.strip().upper()
        if c=="SAVE10": d=hu(rest*0.10)
        elif c=="FIXED500": d=min(500,rest)
        else: raise ValueError
    tx=sub-vip-d
    tax=hu(tx*0.10)
    return {"subtotal_cents":sub,"vip_discount_cents":vip,"coupon_discount_cents":d,"taxable_cents":tx,"tax_cents":tax,"total_cents":tx+tax}
