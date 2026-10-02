"""Cálculo de pedido com descontos e tributação em centavos inteiros."""


def _round_percent(value, percent):
    """Calcula uma percentagem arredondando meio para cima."""
    return (value * percent + 50) // 100


def _validate_items(items):
    if not isinstance(items, (list, tuple)) or not items:
        raise ValueError("items deve ser uma lista ou tupla não vazia")
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("cada item deve ser um dicionário")
        sku = item.get("sku")
        price = item.get("unit_price_cents")
        quantity = item.get("quantity")
        if not isinstance(sku, str) or not sku:
            raise ValueError("sku inválido")
        if isinstance(price, bool) or not isinstance(price, int) or price < 0:
            raise ValueError("unit_price_cents inválido")
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
            raise ValueError("quantity inválida")


def _validate_customer(customer):
    if not isinstance(customer, dict):
        raise ValueError("customer deve ser um dicionário")
    if "vip" in customer and not isinstance(customer["vip"], bool):
        raise ValueError("vip deve ser bool")


def _validate_coupon(coupon):
    if coupon is None:
        return None
    if not isinstance(coupon, str):
        raise ValueError("coupon deve ser uma string ou None")
    coupon = coupon.strip().upper()
    if coupon not in {"SAVE10", "FIXED500"}:
        raise ValueError("cupom desconhecido")
    return coupon


def _calculate_coupon_discount(coupon, remaining):
    if coupon is None:
        return 0
    if coupon == "SAVE10":
        return _round_percent(remaining, 10)
    return min(500, remaining)


def calculate_order(items, customer, coupon=None):
    """Calcula os valores de um pedido, sem modificar as entradas."""
    _validate_items(items)
    _validate_customer(customer)
    coupon = _validate_coupon(coupon)

    subtotal = sum(item["unit_price_cents"] * item["quantity"] for item in items)
    vip_discount = _round_percent(subtotal, 10) if customer.get("vip", False) else 0
    after_vip = subtotal - vip_discount
    coupon_discount = _calculate_coupon_discount(coupon, after_vip)
    taxable = after_vip - coupon_discount
    tax = _round_percent(taxable, 10)
    return {
        "subtotal_cents": subtotal,
        "vip_discount_cents": vip_discount,
        "coupon_discount_cents": coupon_discount,
        "taxable_cents": taxable,
        "tax_cents": tax,
        "total_cents": taxable + tax,
    }
