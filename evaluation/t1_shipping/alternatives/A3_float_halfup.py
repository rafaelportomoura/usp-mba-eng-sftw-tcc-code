# EVALUATION-ONLY: mutante/alternativa de regressao do oraculo; nao fornecer ao agente avaliado.

import math
def calculate_shipping(weight_kg, destination, subtotal_cents, express=False):
    if isinstance(weight_kg,bool) or not isinstance(weight_kg,(int,float)) or weight_kg!=weight_kg or weight_kg in (float("inf"),) or not 0<weight_kg<=30: raise ValueError
    if not isinstance(destination,str): raise ValueError
    d=destination.strip().lower()
    if d not in ("local","regional","national"): raise ValueError
    if not isinstance(subtotal_cents,int) or isinstance(subtotal_cents,bool) or subtotal_cents<0: raise ValueError
    if not isinstance(express,bool): raise ValueError
    std={"local":850,"regional":1550,"national":2490}[d]+(math.ceil(weight_kg)-1)*200
    out=0 if subtotal_cents>=20000 else std
    if express: out+=max(1000,int(std*0.25+0.5))
    return out
