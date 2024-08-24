import pytest
from infrastructure.google.parse_gcs_path import parse_gcs_path


@pytest.mark.parametrize(
    "gcs_path, expected",
    [
        (
            "gs://my-bucket/path/to/file.txt",
            {
                "bucket_name": "my-bucket",
                "filename": "file.txt",
                "file_extension": "txt",
            },
        ),
        (
            "gs://another-bucket/file.jpg",
            {
                "bucket_name": "another-bucket",
                "filename": "file.jpg",
                "file_extension": "jpg",
            },
        ),
        (
            "gs://bucket-with-dots.and-dashes/some/deep/path/doc.pdf",
            {
                "bucket_name": "bucket-with-dots.and-dashes",
                "filename": "doc.pdf",
                "file_extension": "pdf",
            },
        ),
        (
            "gs://empty-bucket/",
            {"bucket_name": "empty-bucket", "filename": "", "file_extension": ""},
        ),
        (
            "gs://bucket-only",
            {"bucket_name": "bucket-only", "filename": "", "file_extension": ""},
        ),
        (
            "gs://bucket/file with spaces.txt",
            {
                "bucket_name": "bucket",
                "filename": "file with spaces.txt",
                "file_extension": "txt",
            },
        ),
        (
            "gs://bucket/file_without_extension",
            {
                "bucket_name": "bucket",
                "filename": "file_without_extension",
                "file_extension": "",
            },
        ),
        (
            "gs://bucket/file.with.multiple.dots.txt",
            {
                "bucket_name": "bucket",
                "filename": "file.with.multiple.dots.txt",
                "file_extension": "txt",
            },
        ),
        (
            "gs://bucket/.hidden_file",
            {"bucket_name": "bucket", "filename": ".hidden_file", "file_extension": ""},
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


def test_parse_gcs_path_only_gs():
    with pytest.raises(ValueError):
        parse_gcs_path("gs://")
