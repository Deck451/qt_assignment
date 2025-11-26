"""Redis module."""

import os
from typing import Callable

from redis import Redis


def _get_redis_client_factory() -> Callable:
    """Factory that creates a lazy-loading Redis client singleton.
    Returns a callable that returns a Redis client.
    The first call initializes the client.
    Subsequent calls return the same client instance within the same process.
    """
    client: Redis | None = None

    def _get_client() -> Redis:
        nonlocal client
        if client is None:
            client = Redis.from_url(os.environ.get("REDIS_URL", "redis://redis:6379/0"))
        return client

    return _get_client


get_redis_client: Callable = _get_redis_client_factory()
