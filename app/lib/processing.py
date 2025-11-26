"""Main processing module containing URL builder and file format exporter classes."""

import logging
from logging import Logger
from abc import ABC, abstractmethod
from io import BytesIO
from datetime import timedelta

from requests import Response
import requests
from fpdf import FPDF
from minio import Minio

from app.lib import config


logger: Logger = logging.getLogger()
logging.basicConfig(level=logging.INFO)


# pylint: disable=too-few-public-methods


class Storage(ABC):
    """Abstract base class for storage, to be subclassed."""

    @abstractmethod
    def get_value_from_storage(self, name: str) -> None:
        """Abstract method, to be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement this method")


class FileStorage(ABC):
    """Abstract base class for file storage, to be subclassed."""

    @abstractmethod
    def upload(self, file_name: str, content: bytes) -> None:
        """Abstract method, to be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement this method")


class RedisStorage(Storage):
    """Class for handling Redis storage where we keep the name-CIK 'lookup table'."""

    def __init__(self, redis_client, key):
        self.redis = redis_client
        self.key = key

    def get_value_from_storage(self, name: str) -> str | None:
        """Get CIK value from redis storage based on company name.
        This for now works on exact matches, which is not ideal.
        Also because we store data in a hashmap format, there's no room
        for duplicate keys, which is not ideal either, as there are
        companies having multiple CIK ids.
        """
        name_normalized: str = name.strip().lower()
        value: bytes | None = self.redis.hget(self.key, name_normalized)
        if value:
            return value.decode("utf-8")

        return None


class SecGovUrlConstructor:
    """Class to construct URLs for SEC filings."""

    base_url: str = "https://www.sec.gov/Archives/edgar/data/{}/{}.txt"
    submissions_url: str = "https://data.sec.gov/submissions/CIK{}.json"

    def __init__(
        self, name: str, file_type: str, storage: Storage, cik: str | None = None
    ) -> None:
        self.name = name
        self.file_type = file_type
        self.storage = storage
        self.cik = cik

    def _get_all_submissions(self, name: str) -> dict | None:
        """Get all submissions JSON for a given entity name."""
        cik = self.cik or self.storage.get_value_from_storage(name)

        if not cik:
            logger.error("CIK not found for entity: %s", name)
            return None

        submissions_url: str = self.submissions_url.format(cik.zfill(10))
        logger.info("Fetching submissions from URL: %s", submissions_url)

        try:
            response: Response = requests.get(
                url=submissions_url,
                headers=config.REQUEST_HEADERS,
                timeout=10,
            )
            response.raise_for_status()
            logger.info(
                "Submission data for '%s (%s)' fetched successfully.", name, cik
            )
            return response.json()
        except requests.RequestException as exc:
            raise RuntimeError(
                f"Failed to fetch submission data for '{name}' ({cik}): {exc}"
            ) from exc

    def get_file_url(self) -> str | None:
        """Get the file URL for the specified file type."""
        submission_data = self._get_all_submissions(self.name)
        if not submission_data:
            return None

        cik = submission_data.get("cik", "").lstrip("0")
        if not cik:
            logger.error("CIK is missing in submission data.")
            return None

        recent_filings = submission_data.get("filings", {}).get("recent", {})
        if not recent_filings:
            logger.error("No recent filings found in submission data.")
            return None

        accession_numbers = recent_filings.get("accessionNumber", [])
        file_types = recent_filings.get("form", [])

        if not accession_numbers or not file_types:
            missing = "accession numbers" if not accession_numbers else "file types"
            logger.error("No %s found in recent filings.", missing)
            return None

        try:
            idx = file_types.index(self.file_type)
        except ValueError as exc:
            logger.error("Submission type %s was not found: %s", self.file_type, exc)
            return None

        accession_number = accession_numbers[idx]
        url = self.base_url.format(cik, accession_number)
        logger.info("URL to filing: %s", url)
        return url


class MinIOStorage(FileStorage):
    """Class for handling MinIO output storage where we keep exports."""

    def __init__(self, client: Minio, bucket_name: str) -> None:
        self.client = client
        self.bucket_name = bucket_name

        if not client.bucket_exists(self.bucket_name):
            client.make_bucket(self.bucket_name)

    def upload(self, file_name: str, content: BytesIO) -> str:
        self.client.put_object(
            bucket_name=self.bucket_name,
            object_name=file_name,
            data=content,
            length=len(content.getbuffer()),
        )

        url = self.client.presigned_get_object(
            "sec-filings",
            file_name,
            expires=timedelta(hours=24),
        )

        logger.info("File saved to MinIO at: %s", url)

        return url


class PDFExporter:
    """Class to export SEC filings as PDF."""

    def __init__(self, storage: FileStorage) -> BytesIO:
        self.storage = storage

    def _convert(self, filing_url: str) -> None:
        """Export the SEC filing at the given URL to a PDF file."""
        try:
            response: Response = requests.get(
                url=filing_url,
                headers=config.REQUEST_HEADERS,
                timeout=10,
            )
            response.raise_for_status()

            pdf = FPDF()
            pdf.add_page()
            pdf.set_auto_page_break(auto=True, margin=10)
            pdf.set_font("Arial", size=10)

            lines = response.text.splitlines()
            for line in lines:
                pdf.multi_cell(0, 10, line)

            pdf_bytes = pdf.output(dest="S").encode("latin1")
            pdf_buffer = BytesIO(pdf_bytes)
            pdf_buffer.seek(0)

            return pdf_buffer

        except requests.RequestException as exc:
            raise RuntimeError(
                f"Failed to fetch filing from '{filing_url}': {exc}"
            ) from exc

    def save_to_storage(self, filing_url: str, file_name: str) -> str:
        """Get the file from the URL resource, convert it and save it to storage."""
        pdf_buffer = self._convert(filing_url)
        return self.storage.upload(file_name, pdf_buffer)
