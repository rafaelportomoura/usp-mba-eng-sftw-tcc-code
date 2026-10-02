# EVALUATION-ONLY: mutante/alternativa de regressao do oraculo; nao fornecer ao agente avaliado.
"""Cálculo de pedido (solução de referência, refatorada)."""

VIP_RATE_BP = 1000
TAX_RATE_BP = 1000
SAVE10_RATE_BP = 1000
FIXED500_CENTS = 500


def _percent(amount_cents, rate_bp):
    """Percentual em pontos-base com arredondamento meio para cima (inteiros)."""
    return (amount_cents * rate_bp + 5000) // 10000


def _validate(items, customer):
    if not isinstance(items, (list, tuple)) or not items:
        raise ValueError("items must be a non-empty list")
    for it in items:
        if not isinstance(it, dict):
            raise ValueError("item must be a dict")
        sku, price, qty = it.get("sku"), it.get("unit_price_cents"), it.get("quantity")
        if not isinstance(sku, str) or not sku:
            raise ValueError("invalid sku")
        if isinstance(price, bool) or not isinstance(price, int) or price < 0:
            raise ValueError("invalid unit_price_cents")
        if isinstance(qty, bool) or not isinstance(qty, int) or qty <= 0:
            raise ValueError("invalid quantity")
    if not isinstance(customer, dict):
        raise ValueError("customer must be a dict")
    if "vip" in customer and not isinstance(customer["vip"], bool):
        raise ValueError("vip must be a bool")


def _subtotal(items):
    return sum(it["unit_price_cents"] * it["quantity"] for it in items)


def _coupon_discount(coupon, remaining):
    if coupon is None:
        return 0
    if not isinstance(coupon, str):
        raise ValueError("coupon must be a string")
    code = coupon.strip().upper()
    if code == "SAVE10":
        return _percent(remaining, SAVE10_RATE_BP)
    if code == "FIXED500":
        return min(FIXED500_CENTS, remaining)
    raise ValueError("unknown coupon")


def calculate_order(items, customer, coupon=None):
    _validate(items, customer)
    subtotal = _subtotal(items)
    vip = _percent(subtotal, VIP_RATE_BP) if customer.get("vip", False) else 0
    coupon_discount = _coupon_discount(coupon, subtotal - vip)
    taxable = subtotal - vip - coupon_discount
    tax = _percent(taxable, TAX_RATE_BP)
    return {
        "subtotal_cents": subtotal,
        "vip_discount_cents": vip,
        "coupon_discount_cents": coupon_discount,
        "taxable_cents": taxable,
        "tax_cents": tax,
        "total_cents": int(float(taxable) + float(tax)),
    }
