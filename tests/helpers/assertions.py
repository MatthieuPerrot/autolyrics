"""Assertion helpers for tests. All test assertions go through these functions."""


def assert_equal(actual, expected, msg=None):
    """Assert that actual equals expected."""
    if actual != expected:
        detail = f"\n  actual:   {actual!r}\n  expected: {expected!r}"
        raise AssertionError(f"{msg or 'Values not equal'}{detail}")


def assert_is_none(value, msg=None):
    """Assert that value is None."""
    if value is not None:
        raise AssertionError(f"{msg or 'Expected None'}, got {value!r}")


def assert_is_not_none(value, msg=None):
    """Assert that value is not None."""
    if value is None:
        raise AssertionError(msg or "Expected non-None value")


def assert_true(value, msg=None):
    """Assert that value is truthy."""
    if not value:
        raise AssertionError(f"{msg or 'Expected truthy value'}, got {value!r}")


def assert_false(value, msg=None):
    """Assert that value is falsy."""
    if value:
        raise AssertionError(f"{msg or 'Expected falsy value'}, got {value!r}")


def assert_in(item, container, msg=None):
    """Assert that item is in container."""
    if item not in container:
        raise AssertionError(f"{msg or f'{item!r} not found in container'}")


def assert_not_in(item, container, msg=None):
    """Assert that item is not in container."""
    if item in container:
        raise AssertionError(f"{msg or f'{item!r} unexpectedly found in container'}")


def assert_greater(actual, threshold, msg=None):
    """Assert that actual > threshold."""
    if not (actual > threshold):
        raise AssertionError(
            f"{msg or 'Value not greater than threshold'}: {actual!r} <= {threshold!r}"
        )


def assert_contains_text(text, substring, msg=None):
    """Assert that substring appears in text."""
    if substring not in text:
        raise AssertionError(
            f"{msg or f'Substring not found'}: {substring!r} not in text "
            f"(first 200 chars: {text[:200]!r})"
        )


def assert_len(collection, expected_len, msg=None):
    """Assert that collection has expected length."""
    actual = len(collection)
    if actual != expected_len:
        raise AssertionError(
            f"{msg or 'Wrong length'}: expected {expected_len}, got {actual}"
        )


def assert_isinstance(obj, cls, msg=None):
    """Assert that obj is an instance of cls."""
    if not isinstance(obj, cls):
        raise AssertionError(
            f"{msg or 'Wrong type'}: expected {cls.__name__}, "
            f"got {type(obj).__name__}"
        )


def assert_greater_equal(actual, threshold, msg=None):
    """Assert that actual >= threshold."""
    if not (actual >= threshold):
        raise AssertionError(
            f"{msg or 'Value not >= threshold'}: {actual!r} < {threshold!r}"
        )


def assert_less(actual, threshold, msg=None):
    """Assert that actual < threshold."""
    if not (actual < threshold):
        raise AssertionError(
            f"{msg or 'Value not less than threshold'}: {actual!r} >= {threshold!r}"
        )
