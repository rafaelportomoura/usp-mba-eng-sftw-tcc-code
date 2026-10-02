"""Cálculo validado de pedidos, usando apenas centavos inteiros."""


def _is_int(value):
    """Retorna True para int, mas não para bool (subclasse de int)."""
    return isinstance(value, int) and not isinstance(value, bool)


def _validate_items(items):
    if not isinstance(items, (list, tuple)) or not items:
        raise ValueError("items deve ser uma lista ou tupla não vazia")

    for current in items:
        if not isinstance(current, dict):
            raise ValueError("cada item deve ser um dicionário")
        if not isinstance(current.get("sku"), str) or not current["sku"]:
            raise ValueError("sku deve ser uma string não vazia")
        price = current.get("unit_price_cents")
        if not _is_int(price) or price < 0:
            raise ValueError("unit_price_cents deve ser um int não negativo")
        quantity = current.get("quantity")
        if not _is_int(quantity) or quantity <= 0:
            raise ValueError("quantity deve ser um int positivo")


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
    normalized = coupon.strip().upper()
    if normalized not in {"SAVE10", "FIXED500"}:
        raise ValueError("cupom desconhecido")
    return normalized


def _round_percent(amount, percent):
    """Calcula amount * percent / 100, arredondando meio para cima."""
    return (amount * percent + 50) // 100


def _subtotal(items):
    return sum(item["unit_price_cents"] * item["quantity"] for item in items)


def calculate_order(items, customer, coupon=None):
    """Calcula os valores de um pedido sem alterar seus argumentos."""
    _validate_items(items)
    _validate_customer(customer)
    normalized_coupon = _validate_coupon(coupon)

    subtotal = _subtotal(items)
    vip_discount = _round_percent(subtotal, 10) if customer.get("vip", False) else 0
    after_vip = subtotal - vip_discount

    if normalized_coupon == "SAVE10":
        coupon_discount = _round_percent(after_vip, 10)
    elif normalized_coupon == "FIXED500":
        coupon_discount = min(500, after_vip)
    else:
        coupon_discount = 0

    taxable = after_vip - coupon_discount
    tax = _round_percent(taxable, 10)
    total = taxable + tax
    return {
        "subtotal_cents": subtotal,
        "vip_discount_cents": vip_discount,
        "coupon_discount_cents": coupon_discount,
        "taxable_cents": taxable,
        "tax_cents": tax,
        "total_cents": total,
    }
