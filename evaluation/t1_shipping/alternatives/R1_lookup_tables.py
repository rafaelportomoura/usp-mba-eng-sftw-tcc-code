# EVALUATION-ONLY: variante de avaliacao; nao fornecer ao agente avaliado.

import math
from decimal import Decimal
def calculate_shipping(weight_kg, destination, subtotal_cents, express=False):
    if type(weight_kg) not in (int, float) or weight_kg != weight_kg or weight_kg <= 0 or weight_kg > 30:
        raise ValueError('w')
    if type(destination) is not str: raise ValueError('d')
    d = destination.strip().lower()
    base = {'local':850,'regional':1550,'national':2490}.get(d)
    if base is None: raise ValueError('d')
    if type(subtotal_cents) is not int or subtotal_cents < 0: raise ValueError('s')
    if express is not True and express is not False: raise ValueError('e')
    kg = int(math.ceil(Decimal(weight_kg)))
    std = base + 200*(kg-1)
    pay = 0 if subtotal_cents >= 20000 else std
    extra = 0
    if express:
        q, r = divmod(std, 4)
        extra = q + (1 if r*2 >= 4 else 0)   # 25% half-up
        extra = max(extra, 1000)
    return int(pay + extra)
