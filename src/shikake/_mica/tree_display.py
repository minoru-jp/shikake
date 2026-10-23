"""Opt-in, bounded and iterative visual inspection of a Model composition tree."""

from __future__ import annotations

from .model import Model, _features_summary, _summary


def format_model_tree(
    model: Model,
    *,
    max_depth: int = 8,
    max_nodes: int = 200,
    max_chars: int = 12000,
) -> str:
    """Show Kind, roles, scalar summaries and Features, without recursion.

    Limits include the root at depth zero. The output is for diagnostics,
    not lossless serialization; children beyond a limit are summarized.
    """
    if max_depth < 0 or max_nodes < 1 or max_chars < 4:
        raise ValueError("max_depth must be >= 0, max_nodes >= 1, max_chars >= 4")

    lines: list[str] = []
    length = 0
    nodes = 0
    pending: list[tuple[Model, int, str]] = [(model, 0, "")]

    def append(line: str) -> bool:
        nonlocal length
        remaining = max_chars - length
        cost = len(line) + (1 if lines else 0)
        if cost > remaining:
            if remaining > 0:
                lines.append("...")
            return False
        lines.append(line)
        length += cost
        return True

    while pending:
        current, depth, label = pending.pop()
        if nodes >= max_nodes:
            append("  " * depth + "... (max_nodes reached)")
            break
        nodes += 1
        span = current.span
        position = (
            ""
            if span is None
            else f" @{span.line}:{span.column}-{span.end_line}:{span.end_column}"
        )
        features = (
            f" features={_features_summary(current.features)}"
            if current.features
            else ""
        )
        if not append(f"{'  ' * depth}{label}{current.kind.id}{position}{features}"):
            break
        children: list[tuple[Model, int, str]] = []
        cutoff = False
        for part in current.parts():
            value = part.value
            prefix = "  " * (depth + 1) + part.role
            if isinstance(value, Model):
                children.append((value, depth + 1, f"{part.role}: "))
            elif isinstance(value, tuple) and value and isinstance(value[0], Model):
                if not append(f"{prefix}: <{len(value)} models>"):
                    cutoff = True
                    break
                # Avoid scheduling an enormous sequence when output is bounded.
                limit = min(len(value), max_nodes)
                for index in range(limit):
                    child = value[index]
                    if isinstance(child, Model):
                        children.append((child, depth + 1, f"{part.role}[{index}]: "))
                if len(value) > limit and not append(
                    f"{prefix}: ... ({len(value) - limit} more models)"
                ):
                    cutoff = True
                    break
            else:
                if not append(f"{prefix}: {_summary(value)}"):
                    cutoff = True
                    break
        if cutoff:
            break
        if children:
            if depth >= max_depth:
                if not append("  " * (depth + 1) + "... (max_depth reached)"):
                    break
            else:
                pending.extend(reversed(children))
    return "\n".join(lines)[:max_chars]
