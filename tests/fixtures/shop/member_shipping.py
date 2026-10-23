from .shipping import ShippingPolicy


class MemberShippingPolicy(ShippingPolicy):
    def calculate_fee(self, subtotal: int) -> int:
        if subtotal >= 3000:
            return 0
        return 300

    def calculate_points(self, subtotal: int) -> int:
        return subtotal // 100
