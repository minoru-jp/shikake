FREE_SHIPPING_THRESHOLD: int = 5000
STANDARD_SHIPPING_FEE: int = 600


def calculate_total(
    prices: dict[str, int],
    sku: str,
    quantity: int,
) -> int:
    unit_price = prices[sku]
    subtotal = unit_price * quantity

    if subtotal >= FREE_SHIPPING_THRESHOLD:
        shipping_fee = 0
    else:
        shipping_fee = STANDARD_SHIPPING_FEE

    return subtotal + shipping_fee
