"""Stock processing with alternative paths, loops and exception cleanup."""


def stock_state(stock: int, minimum: int) -> str:
    if stock < 0:
        return "negative"
    elif stock < minimum:
        return "low"
    else:
        return "ready"


def rebalance_stock(
    events: list[tuple[str, int]], minimum: int, lot: int
) -> tuple[int, int, int, bool]:
    stock = 0
    accepted = 0
    inspected = 0
    scanned_all = False
    for event in events:
        try:
            match event:
                case ("receive", amount) if amount > 0:
                    stock += amount
                case ("ship", amount) if amount > 0:
                    stock -= amount
                case _:
                    raise ValueError("Unknown event")
        except ValueError:
            continue
        else:
            accepted += 1
        finally:
            inspected += 1
        if stock >= minimum:
            break
    else:
        scanned_all = True

    while stock < minimum:
        stock += lot
    return stock, accepted, inspected, scanned_all
