"""Cálculo de frete."""

import math


def calculate_shipping(weight_kg, destination, subtotal_cents, express=False):
    if (
        isinstance(weight_kg, bool)
        or not isinstance(weight_kg, (int, float))
        or weight_kg <= 0
        or weight_kg > 30
        or not math.isfinite(weight_kg)
    ):
        raise ValueError("weight_kg must be a finite number in (0, 30]")

    if not isinstance(destination, str):
        raise ValueError("destination must be a supported string")
    destination = destination.strip().lower()
    if destination not in {"local", "regional", "national"}:
        raise ValueError("destination must be local, regional, or national")

    if (
        isinstance(subtotal_cents, bool)
        or not isinstance(subtotal_cents, int)
        or subtotal_cents < 0
        or not isinstance(express, bool)
    ):
        raise ValueError("subtotal_cents or express has an invalid value")

    base = {"local": 850, "regional": 1550, "national": 2490}[destination]
    standard_fee = base + (math.ceil(weight_kg) - 1) * 200
    express_fee = 0
    if express:
        # Integer arithmetic implements rounding half up without float error.
        express_fee = max(1000, (standard_fee * 25 + 50) // 100)

    if subtotal_cents >= 20000:
        standard_fee = 0
    return standard_fee + express_fee
