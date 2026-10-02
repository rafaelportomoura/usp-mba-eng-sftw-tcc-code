"""Cálculo de preços de um pedido."""


def _round_percent(amount, percentage):
    """Calcula uma percentagem inteira, arredondando meios para cima."""
    return (amount * percentage + 50) // 100


def _validate_items(items):
    if not isinstance(items, (list, tuple)) or not items:
        raise ValueError("items deve ser uma lista ou tupla não vazia")

    subtotal = 0
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("cada item deve ser um dicionário")
        sku = item.get("sku")
        price = item.get("unit_price_cents")
        quantity = item.get("quantity")
        if not isinstance(sku, str) or not sku:
            raise ValueError("sku deve ser uma string não vazia")
        if isinstance(price, bool) or not isinstance(price, int) or price < 0:
            raise ValueError("unit_price_cents deve ser um inteiro não negativo")
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
            raise ValueError("quantity deve ser um inteiro positivo")
        subtotal += price * quantity
    return subtotal


def _validate_customer(customer):
    if not isinstance(customer, dict):
        raise ValueError("customer deve ser um dicionário")
    if "vip" in customer and not isinstance(customer["vip"], bool):
        raise ValueError("vip deve ser bool")


def _coupon_discount(remaining, coupon):
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
    """Retorna subtotal, descontos, imposto e total de um pedido."""
    subtotal = _validate_items(items)
    _validate_customer(customer)
    vip_discount = _round_percent(subtotal, 10) if customer.get("vip", False) else 0
    remaining = subtotal - vip_discount
    coupon_discount = _coupon_discount(remaining, coupon)
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
