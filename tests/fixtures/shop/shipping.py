class ShippingPolicy:
    def calculate_fee(self, subtotal: int) -> int:
        if subtotal >= 5000:
            return 0
        return 600

    def description(self) -> str:
        return "Standard shipping"
