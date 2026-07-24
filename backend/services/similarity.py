"""
Pure similarity math -- no I/O, no database, no Ollama calls. Kept
separate so it can be tested in isolation, same reasoning as chunking.py.
"""

import math


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """
    Returns a value between -1 and 1 (in practice, 0 to 1 for embedding
    vectors, which are non-negative in most models) indicating how similar
    two vectors are. 1 means identical direction, 0 means unrelated.
    """
    if len(a) != len(b):
        raise ValueError(
            f"Vectors must be the same length to compare (got {len(a)} and {len(b)})"
        )

    dot_product = sum(x * y for x, y in zip(a, b))
    magnitude_a = math.sqrt(sum(x * x for x in a))
    magnitude_b = math.sqrt(sum(y * y for y in b))

    if magnitude_a == 0 or magnitude_b == 0:
        return 0.0

    return dot_product / (magnitude_a * magnitude_b)