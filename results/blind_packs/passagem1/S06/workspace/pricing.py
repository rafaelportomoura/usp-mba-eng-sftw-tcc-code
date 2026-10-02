"""Cálculo de preços de um pedido, usando somente aritmética inteira."""


def _round_percentage(value, percentage):
    """Calcula uma percentagem e arredonda meios para cima."""
    numerator = value * percentage
    denominator = 100
    return (numerator * 2 + denominator) // (2 * denominator)


def _validate_items(items):
    if not isinstance(items, (list, tuple)) or not items:
        raise ValueError("items deve ser uma lista ou tupla não vazia")
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("cada item deve ser um dicionário")
        if not isinstance(item.get("sku"), str) or not item["sku"]:
            raise ValueError("sku deve ser uma string não vazia")
        price = item.get("unit_price_cents")
        if isinstance(price, bool) or not isinstance(price, int) or price < 0:
            raise ValueError("unit_price_cents deve ser um inteiro não negativo")
        quantity = item.get("quantity")
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
            raise ValueError("quantity deve ser um inteiro positivo")


def _validate_customer(customer):
    if not isinstance(customer, dict):
        raise ValueError("customer deve ser um dicionário")
    if "vip" in customer and not isinstance(customer["vip"], bool):
        raise ValueError("vip deve ser bool")


def _coupon_discount(coupon, amount):
    if coupon is None:
        return 0
    if not isinstance(coupon, str):
        raise ValueError("coupon deve ser uma string ou None")
    normalized = coupon.strip().upper()
    if normalized == "SAVE10":
        return _round_percentage(amount, 10)
    if normalized == "FIXED500":
        return min(500, amount)
    raise ValueError("cupom desconhecido")


def calculate_order(items, customer, coupon=None):
    """Retorna os valores calculados de um pedido em centavos."""
    _validate_items(items)
    _validate_customer(customer)
    subtotal = sum(item["unit_price_cents"] * item["quantity"] for item in items)
    vip_discount = (
        _round_percentage(subtotal, 10) if customer.get("vip", False) else 0
    )
    after_vip = subtotal - vip_discount
    coupon_discount = _coupon_discount(coupon, after_vip)
    taxable = after_vip - coupon_discount
    tax = _round_percentage(taxable, 10)
    return {
        "subtotal_cents": subtotal,
        "vip_discount_cents": vip_discount,
        "coupon_discount_cents": coupon_discount,
        "taxable_cents": taxable,
        "tax_cents": tax,
        "total_cents": taxable + tax,
    }
