import math
import pytest

from backend.services.similarity import cosine_similarity


def test_identical_vectors_have_similarity_one():
    v = [1.0, 2.0, 3.0]
    assert math.isclose(cosine_similarity(v, v), 1.0, rel_tol=1e-9)


def test_opposite_vectors_have_similarity_negative_one():
    a = [1.0, 0.0]
    b = [-1.0, 0.0]
    assert math.isclose(cosine_similarity(a, b), -1.0, rel_tol=1e-9)


def test_orthogonal_vectors_have_similarity_zero():
    a = [1.0, 0.0]
    b = [0.0, 1.0]
    assert math.isclose(cosine_similarity(a, b), 0.0, abs_tol=1e-9)


def test_similarity_ignores_magnitude_only_direction():
    a = [1.0, 1.0]
    b = [5.0, 5.0]  # same direction, different length
    assert math.isclose(cosine_similarity(a, b), 1.0, rel_tol=1e-9)


def test_mismatched_lengths_raise():
    with pytest.raises(ValueError):
        cosine_similarity([1.0, 2.0], [1.0, 2.0, 3.0])


def test_zero_vector_returns_zero_not_a_crash():
    # Should not raise a ZeroDivisionError.
    assert cosine_similarity([0.0, 0.0], [1.0, 1.0]) == 0.0
    assert cosine_similarity([0.0, 0.0], [0.0, 0.0]) == 0.0


def test_more_similar_vector_scores_higher():
    query = [1.0, 1.0, 0.0]
    close = [1.0, 0.9, 0.0]
    far = [0.0, 0.0, 1.0]
    assert cosine_similarity(query, close) > cosine_similarity(query, far)