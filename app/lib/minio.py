"""MinIO module."""

import os
from typing import Callable

from minio import Minio


def _get_minio_client_factory() -> Callable:
    """Factory that creates a lazy-loading MinIO client singleton.
    Returns a callable that returns a MinIO client.
    The first call initializes the client.
    Subsequent calls return the same client instance within the same process.
    """
    client: Minio | None = None

    def _get_client() -> Minio:
        nonlocal client
        if client is None:
            client = Minio(
                "minio:9000",
                access_key=os.environ.get("MINIO_ROOT_USER", ""),
                secret_key=os.environ.get("MINIO_ROOT_PASSWORD", ""),
                secure=False,
            )
        return client

    return _get_client


get_minio_client: Callable = _get_minio_client_factory()
