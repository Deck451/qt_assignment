"""Main FastAPI service module."""

from logging import Logger, getLogger
from typing import Any

from fastapi import FastAPI, HTTPException

from app.tasks import refresh_cik_data
from app.lib.processing import (
    RedisStorage,
    SecGovUrlConstructor,
    PDFExporter,
    MinIOStorage,
)
from app.lib.redis import get_redis_client
from app.lib.minio import get_minio_client
from app.lib import config


application: FastAPI = FastAPI()
logger: Logger = getLogger()


@application.post("/refresh-cik")
def refresh_cik() -> dict[str, Any]:
    """Fetch CIK data from SEC and populate storage."""
    task: Any = refresh_cik_data.run_task.delay()
    return {"task_id": task.id}


@application.get("/get-file")
def get_file(
    name: str, file_type: str, cik: str | None = None
) -> dict[str, str] | None:
    """Get the file for the most recent submission of the given file type
    for the specified entity name.
    """
    redis_storage: RedisStorage = RedisStorage(
        redis_client=get_redis_client(), key=config.REDIS_KEY
    )
    minio_storage: MinIOStorage = MinIOStorage(
        client=get_minio_client(), bucket_name="sec-filings"
    )
    output_file_name: str = f"{name}_{file_type}.pdf"

    url_constructor: SecGovUrlConstructor = SecGovUrlConstructor(
        name=name,
        file_type=file_type,
        storage=redis_storage,
        cik=cik,
    )
    url: str | None = url_constructor.get_file_url()
    if url is None:
        raise HTTPException(status_code=404, detail="File URL not found")

    exporter: PDFExporter = PDFExporter(
        storage=minio_storage,
    )
    url: str = exporter.save_to_storage(
        filing_url=url,
        file_name=output_file_name,
    )

    return {"result": url}
