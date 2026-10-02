"""Cálculo de pedido (baseline monolítico com defeitos)."""


def calculate_order(items, customer, coupon=None):
    items.sort(key=lambda i: i["sku"])
    subtotal = 0
    for it in items:
        subtotal += it["unit_price_cents"] * it["quantity"]
    vip = 0
    if customer.get("vip"):
        vip = subtotal * 0.10
    rest = subtotal - vip
    disc = 0
    if coupon == "SAVE10":
        disc = rest * 0.10
    elif coupon == "FIXED500":
        disc = 500
    taxable = rest
    tax = taxable * 0.10
    total = taxable - disc + tax
    return {
        "subtotal_cents": int(subtotal),
        "vip_discount_cents": int(round(vip)),
        "coupon_discount_cents": int(round(disc)),
        "taxable_cents": int(round(taxable)),
        "tax_cents": int(round(tax)),
        "total_cents": int(round(total)),
    }
