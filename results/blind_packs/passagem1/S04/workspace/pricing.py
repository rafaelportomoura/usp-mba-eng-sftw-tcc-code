"""Cálculo de preços de um pedido, usando apenas aritmética inteira."""


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _validate_items(items):
    if not isinstance(items, (list, tuple)) or not items:
        raise ValueError("items deve ser uma lista ou tupla não vazia")
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("cada item deve ser um dicionário")
        if not isinstance(item.get("sku"), str) or not item["sku"]:
            raise ValueError("sku deve ser uma string não vazia")
        price = item.get("unit_price_cents")
        quantity = item.get("quantity")
        if not _is_int(price) or price < 0:
            raise ValueError("unit_price_cents deve ser um inteiro não negativo")
        if not _is_int(quantity) or quantity <= 0:
            raise ValueError("quantity deve ser um inteiro positivo")


def _validate_customer(customer):
    if not isinstance(customer, dict):
        raise ValueError("customer deve ser um dicionário")
    if "vip" in customer and not isinstance(customer["vip"], bool):
        raise ValueError("vip deve ser booleano")


def _round_percent(amount, percent):
    """Percentagem não negativa com arredondamento de meio para cima."""
    return (amount * percent + 50) // 100


def _coupon_discount(coupon, remaining):
    if coupon is None:
        return 0
    if not isinstance(coupon, str):
        raise ValueError("coupon deve ser uma string ou None")
    normalized = coupon.strip().upper()
    if normalized == "SAVE10":
        return _round_percent(remaining, 10)
    if normalized == "FIXED500":
        return min(500, remaining)
    raise ValueError("cupom desconhecido")


def calculate_order(items, customer, coupon=None):
    """Calcula subtotal, descontos, imposto e total de um pedido."""
    _validate_items(items)
    _validate_customer(customer)
    subtotal = sum(item["unit_price_cents"] * item["quantity"] for item in items)
    vip_discount = _round_percent(subtotal, 10) if customer.get("vip", False) else 0
    remaining = subtotal - vip_discount
    coupon_discount = _coupon_discount(coupon, remaining)
    taxable = remaining - coupon_discount
    tax = _round_percent(taxable, 10)
    return {
        "subtotal_cents": subtotal,
        "vip_discount_cents": vip_discount,
        "coupon_discount_cents": coupon_discount,
        "taxable_cents": taxable,
        "tax_cents": tax,
        "total_cents": taxable + tax,
    }
