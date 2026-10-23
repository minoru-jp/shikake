from .member_shipping import MemberShippingPolicy
from .shipping import ShippingPolicy


def calculate_total(subtotal: int, is_member: bool) -> int:
    if is_member:
        policy = MemberShippingPolicy()
    else:
        policy = ShippingPolicy()

    shipping_fee = policy.calculate_fee(subtotal)
    return subtotal + shipping_fee
