"""Sample for literal singletons, imports, pass and augmented assignment."""

import math
from typing import Protocol


class FeePolicy(Protocol):
    def fee(self, subtotal: int) -> int: ...


def quote_total(subtotal: int, deduction: int | None = None) -> int:
    total = math.ceil(subtotal / 100) * 100
    total += 250
    if deduction is None:
        pass
    else:
        total -= deduction
    return total
