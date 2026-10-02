"""Cálculo de frete."""

import math


def calculate_shipping(weight_kg, destination, subtotal_cents, express=False):
    if (isinstance(weight_kg, bool) or not isinstance(weight_kg, (int, float))):
        raise ValueError("weight_kg must be a finite number between 0 and 30")
    # Check the bounds before converting an arbitrary-size int to float.
    if weight_kg <= 0 or weight_kg > 30 or not math.isfinite(weight_kg):
        raise ValueError("weight_kg must be a finite number between 0 and 30")

    if not isinstance(destination, str):
        raise ValueError("destination must be a supported string")
    destination = destination.strip().lower()
    rates = {"local": 850, "regional": 1550, "national": 2490}
    if destination not in rates:
        raise ValueError("destination must be local, regional, or national")

    if (isinstance(subtotal_cents, bool)
            or not isinstance(subtotal_cents, int)
            or subtotal_cents < 0):
        raise ValueError("subtotal_cents must be a non-negative integer")
    if not isinstance(express, bool):
        raise ValueError("express must be a boolean")

    standard_fee = rates[destination] + (math.ceil(weight_kg) - 1) * 200
    standard_shipping = 0 if subtotal_cents >= 20000 else standard_fee

    express_fee = 0
    if express:
        # Round standard_fee / 4 to the nearest cent, with ties upward.
        express_fee = max(1000, (standard_fee + 2) // 4)

    return standard_shipping + express_fee
