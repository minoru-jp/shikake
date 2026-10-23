"""A small, runnable order calculation illustrating function and class forms."""

from abc import ABC, abstractmethod
from dataclasses import dataclass


def line_amount(price: int, quantity: int = 1, /) -> int:
    return price * quantity


def subtotal(*amounts: int, discount: int = 0) -> int:
    return sum(amounts) - discount


class ShippingPolicy(ABC):
    @abstractmethod
    def fee(self, amount: int) -> int:
        raise NotImplementedError


@dataclass(frozen=True)
class StandardShipping(ShippingPolicy):
    flat_fee: int = 600
    free_from: int = 5000

    def fee(self, amount: int) -> int:
        if amount >= self.free_from:
            return 0
        return self.flat_fee

    @classmethod
    def for_members(cls) -> "StandardShipping":
        return cls(flat_fee=300, free_from=3000)

    @staticmethod
    def valid_amount(amount: int) -> bool:
        return amount >= 0


def checkout(
    amounts: list[int],
    *,
    policy: ShippingPolicy,
    discount: int = 0,
) -> int:
    amount = subtotal(*amounts, discount=discount)

    if not StandardShipping.valid_amount(amount):
        raise ValueError("Invalid subtotal")

    return amount + policy.fee(amount)


def sample_order() -> int:
    amounts = [
        line_amount(1200, 2),
        line_amount(800),
    ]

    options = {"discount": 100}
    policy = StandardShipping.for_members()

    return checkout(amounts, policy=policy, **options)
