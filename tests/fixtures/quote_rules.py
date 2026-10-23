"""Order quotation rules used to inspect written operators, not to execute them."""

MIN_QUANTITY: int = 1
MAX_QUANTITY: int = 20
FREE_SHIPPING_FROM: int = 5000


def quote_total(
    unit_price: int,
    quantity: int,
    sku: str,
    allowed_skus: list[str],
    member: bool,
    shipping: int | None = None,
) -> int:
    if not (MIN_QUANTITY <= quantity <= MAX_QUANTITY) or sku not in allowed_skus:
        return -1

    subtotal = unit_price * quantity
    if member and (subtotal >= FREE_SHIPPING_FROM or shipping is None):
        shipping = 0
    else:
        if shipping is None:
            shipping = 600
    return subtotal + shipping
