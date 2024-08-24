import pytest
from infrastructure.google.parse_gcs_path import parse_gcs_path


@pytest.mark.parametrize(
    "gcs_path, expected",
    [
        (
            "gs://my-bucket/path/to/file.txt",
            {"bucket_name": "my-bucket", "filename": "file.txt"},
        ),
        (
            "gs://another-bucket/file.jpg",
            {"bucket_name": "another-bucket", "filename": "file.jpg"},
        ),
        (
            "gs://bucket-with-dots.and-dashes/some/deep/path/doc.pdf",
            {"bucket_name": "bucket-with-dots.and-dashes", "filename": "doc.pdf"},
        ),
        (
            "gs://empty-bucket/",
            {"bucket_name": "empty-bucket", "filename": ""},
        ),
        (
            "gs://bucket-only",
            {"bucket_name": "bucket-only", "filename": ""},
        ),
        (
            "gs://bucket/file with spaces.txt",
            {"bucket_name": "bucket", "filename": "file with spaces.txt"},
        ),
    ],
)
def test_parse_gcs_path(gcs_path, expected):
    assert parse_gcs_path(gcs_path) == expected


def test_parse_gcs_path_invalid_input():
    with pytest.raises(ValueError):
        parse_gcs_path("invalid_path")


def test_parse_gcs_path_empty_input():
    with pytest.raises(ValueError):
        parse_gcs_path("")
