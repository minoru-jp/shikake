"""Generator modeling example; source is read, never executed, by Mica."""


def fallback_rows():
    yield 99


def filtered_rows(rows: list[int], *, minimum: int = 2):
    for row in rows:
        if row >= minimum:
            yield row
    yield from fallback_rows()


class Ledger:
    def entries(self, rows):
        yield from rows

    def count(self, rows):
        return len(rows)


def make_factory():
    def local_generator():
        yield 42

    return local_generator


def paused():
    yield
