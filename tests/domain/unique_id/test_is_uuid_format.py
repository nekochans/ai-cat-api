import pytest
from domain.unique_id import is_uuid_format


@pytest.mark.parametrize(
    "value, expected",
    [
        ("550e8400-e29b-41d4-a716-446655440000", True),
        ("550e8400e29b41d4a716446655440000", False),
        ("550e8400-e29b-41d4-a716-44665544000", False),
        ("550e8400-e29b-41d4-a716-44665544000g", False),
        ("", False),
    ],
)
def test_is_uuid_format(value, expected):
    assert is_uuid_format(value) == expected
