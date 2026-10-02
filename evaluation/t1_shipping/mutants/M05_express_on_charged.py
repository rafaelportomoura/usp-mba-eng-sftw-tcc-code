# EVALUATION-ONLY: mutante/alternativa de regressao do oraculo; nao fornecer ao agente avaliado.
"""Cálculo de frete (solução de referência)."""

import math

_BASE = {"local": 850, "regional": 1550, "national": 2490}
_FREE_THRESHOLD = 20000
_EXPRESS_MIN = 1000


def calculate_shipping(weight_kg, destination, subtotal_cents, express=False):
    if isinstance(weight_kg, bool) or not isinstance(weight_kg, (int, float)):
        raise ValueError("weight_kg must be a number")
    if not (0 < weight_kg <= 30):  # falso também para NaN; comparação exata evita OverflowError de isfinite
        raise ValueError("weight_kg must be in (0, 30]")
    if not isinstance(destination, str):
        raise ValueError("destination must be a string")
    zone = destination.strip().lower()
    if zone not in _BASE:
        raise ValueError("unknown destination")
    if isinstance(subtotal_cents, bool) or not isinstance(subtotal_cents, int) or subtotal_cents < 0:
        raise ValueError("subtotal_cents must be a non-negative int")
    if not isinstance(express, bool):
        raise ValueError("express must be a bool")

    standard = _BASE[zone] + (math.ceil(weight_kg) - 1) * 200
    charged = 0 if subtotal_cents >= _FREE_THRESHOLD else standard
    surcharge = 0
    if express:
        surcharge = max(_EXPRESS_MIN, (charged * 25 + 50) // 100)
    return charged + surcharge
