# EVALUATION-ONLY: variante de avaliacao; nao fornecer ao agente avaliado.

def _hu(n, num, den):
    q, r = divmod(n*num, den)
    return q + (1 if 2*r >= den else 0)
def calculate_order(items, customer, coupon=None):
    if not isinstance(items,(list,tuple)) or not items: raise ValueError('items')
    sub = 0
    for it in items:
        if not isinstance(it, dict): raise ValueError('it')
        sku = it.get('sku'); pr = it.get('unit_price_cents'); qt = it.get('quantity')
        if not isinstance(sku,str) or sku == '': raise ValueError('sku')
        if isinstance(pr,bool) or not isinstance(pr,int) or pr < 0: raise ValueError('pr')
        if isinstance(qt,bool) or not isinstance(qt,int) or qt < 1: raise ValueError('qt')
        sub += pr*qt
    if not isinstance(customer, dict): raise ValueError('c')
    v = customer['vip'] if 'vip' in customer else False
    if not isinstance(v,bool): raise ValueError('v')
    vd = _hu(sub,1,10) if v else 0
    left = sub - vd
    cd = 0
    if coupon is not None:
        if not isinstance(coupon,str): raise ValueError('cp')
        c = coupon.strip().upper()
        if c == 'SAVE10': cd = _hu(left,1,10)
        elif c == 'FIXED500': cd = 500 if left >= 500 else left
        else: raise ValueError('cp')
    t = left - cd
    x = _hu(t,1,10)
    return {'subtotal_cents':sub,'vip_discount_cents':vd,'coupon_discount_cents':cd,'taxable_cents':t,'tax_cents':x,'total_cents':t+x}
