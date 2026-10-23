"""Assignments with more than one destination, unpacking and expression binding."""


def summarize_shipments(shipments: list[tuple[str, int]]) -> dict[str, int]:
    first, *remaining = shipments
    first_sku, first_quantity = first
    amount = initial = first_quantity
    totals = {first_sku: amount}

    for sku, quantity in remaining:
        totals[sku] = quantity

    if (remaining_count := len(remaining)) > 0:
        totals["remaining_count"] = remaining_count

    totals["initial"] = initial
    return totals
