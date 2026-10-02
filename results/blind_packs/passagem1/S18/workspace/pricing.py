"""Cálculo de pedidos em centavos, sem efeitos colaterais."""


def _round_percentage(amount, percentage):
    """Calcula uma percentagem, arredondando meio para cima."""
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
    vip = customer.get("vip", False)
    if not isinstance(vip, bool):
        raise ValueError("vip deve ser bool")
    return vip


def _coupon_discount(coupon, amount):
    if coupon is None:
        return 0
    if not isinstance(coupon, str):
        raise ValueError("coupon deve ser uma string ou None")
    code = coupon.strip().upper()
    if code == "SAVE10":
        return _round_percentage(amount, 10)
    if code == "FIXED500":
        return min(500, amount)
    raise ValueError("cupom desconhecido")


def calculate_order(items, customer, coupon=None):
    """Retorna os valores do pedido, todos expressos em centavos inteiros."""
    subtotal = _validate_items(items)
    is_vip = _validate_customer(customer)
    vip_discount = _round_percentage(subtotal, 10) if is_vip else 0
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
