"""An item label assembled from written value-expression structures."""


def describe_batch(codes: list[str], total: int, threshold: int) -> str:
    sampled = codes[1:5:2]  # type: ignore[index]
    statuses = {"ready", "reserved"}
    status = "ready" if total >= threshold else "reserved"
    if status in statuses:
        return f"{status!s}: {sampled!r}; total={total:06d}"
    return f"unavailable: {total}"
