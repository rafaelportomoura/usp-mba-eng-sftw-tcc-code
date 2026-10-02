# EVALUATION-ONLY: mutante/alternativa de regressao do oraculo; nao fornecer ao agente avaliado.

from fractions import Fraction
import math
class _V(ValueError): pass
def _check(w,d,s,e):
    for ok,msg in ((not isinstance(w,bool) and isinstance(w,(int,float)),"w"),):
        if not ok: raise _V(msg)
    if math.isnan(w) or math.isinf(w) or w<=0 or w>30: raise _V("w")
    if not isinstance(d,str) or d.strip().lower() not in ("local","regional","national"): raise _V("d")
    if isinstance(s,bool) or not isinstance(s,int) or s<0: raise _V("s")
    if not isinstance(e,bool): raise _V("e")
def calculate_shipping(weight_kg, destination, subtotal_cents, express=False):
    _check(weight_kg,destination,subtotal_cents,express)
    rate={"local":850,"regional":1550,"national":2490}[destination.strip().lower()]
    std=rate+200*(math.ceil(weight_kg)-1)
    free = subtotal_cents >= 20000
    surcharge=0
    if express:
        x=Fraction(std,4)
        surcharge=max(1000, math.floor(x+Fraction(1,2)))
    return (0 if free else std)+surcharge
