"""Cálculo de frete."""

import math


def calculate_shipping(weight_kg, destination, subtotal_cents, express=False):
    valid_weight = False
    if not isinstance(weight_kg, bool) and isinstance(weight_kg, (int, float)):
        try:
            valid_weight = math.isfinite(weight_kg) and 0 < weight_kg <= 30
        except (OverflowError, TypeError):
            valid_weight = False
    if not valid_weight:
        raise ValueError("weight_kg must be finite and between 0 and 30")

    if not isinstance(destination, str):
        raise ValueError("destination must be a supported string")
    destination = destination.strip().lower()
    base_by_destination = {"local": 850, "regional": 1550, "national": 2490}
    if destination not in base_by_destination:
        raise ValueError("destination must be local, regional, or national")

    if (
        isinstance(subtotal_cents, bool)
        or not isinstance(subtotal_cents, int)
        or subtotal_cents < 0
        or not isinstance(express, bool)
    ):
        raise ValueError("invalid subtotal_cents or express")

    standard_fee = base_by_destination[destination] + (math.ceil(weight_kg) - 1) * 200
    express_fee = 0
    if express:
        # Round 25% to the nearest cent, with ties rounded upward.
        express_fee = max(1000, (standard_fee * 25 + 50) // 100)

    if subtotal_cents >= 20000:
        standard_fee = 0

    return standard_fee + express_fee
