from itertools import islice


def batched(iterable, n: int):
    if n < 1:
        raise ValueError("n must be at least one")

    iterator = iter(iterable)
    while batch := tuple(islice(iterator, n)):
        yield batch
