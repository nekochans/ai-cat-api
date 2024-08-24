import os
from typing import TypedDict


class GoogleCloudStoragePathComponents(TypedDict):
    bucket_name: str
    filename: str


def parse_gcs_path(gcs_path: str) -> GoogleCloudStoragePathComponents:
    """
    Google Cloud Storage（GCS）のパスを解析し、そのコンポーネントを抽出する関数

    :param gcs_path: GCSの完全なパス（例: 'gs://bucket-name/path/to/file.ext'）
    :return: パスの各コンポーネントを含む辞書
    """
    if not gcs_path:
        raise ValueError("GCS path cannot be empty")

    if not gcs_path.startswith("gs://"):
        raise ValueError("Invalid GCS path format. Must start with 'gs://'")

    # GCSのプレフィックス（'gs://'）を取り除く
    path_without_prefix = gcs_path[5:]

    if not path_without_prefix:
        raise ValueError("GCS path must contain a bucket name")

    # パスをコンポーネントに分割
    components = path_without_prefix.split("/", 1)

    # バケット名を取得
    bucket_name = components[0]

    if not bucket_name:
        raise ValueError("Bucket name cannot be empty")

    # ファイル名を取得（パスが1つのコンポーネントしかない場合に対応）
    filename = os.path.basename(components[1]) if len(components) > 1 else ""

    return {"bucket_name": bucket_name, "filename": filename}
