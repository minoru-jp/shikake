"""Written contexts and value constructions for an order aggregation workflow."""


def summarize(rows: list[tuple[str, list[int]]], path: str, logger):
    with logger("summary") as trace, open(path) as output:
        grouped = {
            name: [score * 2 for score in scores if score > 0]
            for name, scores in rows
            if scores
        }
        unique = {score for values in grouped.values() for score in values}
        indexed = {score: len(str(score)) for score in unique if score > 10}
        streamed = (score for score in unique if score > 0)
        trace(grouped)
        output.write("done")
        return grouped, unique, indexed, streamed
