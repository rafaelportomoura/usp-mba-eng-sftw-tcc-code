# EVALUATION-ONLY: mutante/alternativa de regressao do oraculo; nao fornecer ao agente avaliado.

from decimal import Decimal, ROUND_HALF_UP, ROUND_CEILING
import math
def calculate_shipping(weight_kg, destination, subtotal_cents, express=False):
    if type(weight_kg) not in (int, float): raise ValueError("w")
    if not (0 < weight_kg <= 30): raise ValueError("w")   # NaN fails comparison
    if not isinstance(destination, str): raise ValueError("d")
    base = {"local":850,"regional":1550,"national":2490}.get(destination.strip().lower())
    if base is None: raise ValueError("d")
    if type(subtotal_cents) is not int or subtotal_cents < 0: raise ValueError("s")
    if express is not True and express is not False: raise ValueError("e")
    kg = int(Decimal(repr(weight_kg)).to_integral_value(rounding=ROUND_CEILING))
    std = base + max(kg-1,0)*200
    total = 0 if subtotal_cents >= 20000 else std
    if express:
        fee = int((Decimal(std)*Decimal("0.25")).quantize(Decimal(1), rounding=ROUND_HALF_UP))
        total += max(1000, fee)
    return total
