"""Sync storage module."""

from logging import Logger, getLogger

import requests
from requests import Response
from redis import Redis

from app.lib.redis import get_redis_client
from app.lib import config


logger: Logger = getLogger()


def run():
    """
    Fetches CIK data from the SEC and populates it into Redis.
    """
    logger.info("Contacting SEC to fetch CIK data...")

    try:
        response: Response = requests.get(
            url=config.CIK_URL,
            headers=config.REQUEST_HEADERS,
            timeout=10,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise RuntimeError(f"Failed to fetch CIK data: {exc}") from exc

    logger.info("CIK data fetched successfully.")

    lines: list[str] = response.text.splitlines()
    total_count: int = 0
    data: dict = {}

    for line in lines:
        normalized_line: str = line.rstrip(":").lower()

        if ":" not in normalized_line:
            logger.warning("Skipping malformed line: %s", line)
            continue

        key, value = normalized_line.rsplit(":", 1)
        data[key.strip()] = value.strip()
        total_count += 1

        if total_count % 100000 == 0:
            logger.info("Pushed %s records so far", total_count)

    redis_client: Redis = get_redis_client()
    redis_client.hset(config.REDIS_KEY, mapping=data)
    logger.info("Finished pushing %s records to Redis.", total_count)
    logger.info("Redis syncing complete.")
