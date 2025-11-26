"""Testing processing module."""

import uuid
from unittest.mock import patch, MagicMock

import pytest
import requests

from app.lib.processing import (
    SecGovUrlConstructor,
    RedisStorage,
    PDFExporter,
    FileStorage,
)
from app.lib import config


@pytest.mark.parametrize(
    "expected_value",
    [
        f"{uuid.uuid4()}",
        None,
    ],
)
def test_redis_storage_get_value(expected_value) -> None:
    """Test RedisStorage.get_value_from_storage method."""
    value: bytes | None = expected_value.encode("utf-8") if expected_value else None
    redis_key: str = f"{uuid.uuid4()}"
    mock_redis_client: MagicMock = MagicMock()
    mock_redis_client.hget.return_value = value

    storage: RedisStorage = RedisStorage(redis_client=mock_redis_client, key=redis_key)
    result: str | None = storage.get_value_from_storage("Apple")

    if expected_value:
        assert result == expected_value
    else:
        assert result is expected_value
    mock_redis_client.hget.assert_called_once_with(redis_key, "apple")


@pytest.mark.parametrize(
    "submission_data, file_type, expected_url",
    [
        ({"not_cik": "value"}, "irrelevant", None),
        ({"cik": "value"}, "irrelevant", None),
        ({"cik": "value", "filings": {}}, "irrelevant", None),
        ({"cik": "value", "filings": {"recent": {}}}, "irrelevant", None),
        (
            {"cik": "value", "filings": {"recent": {"accessionNumber": []}}},
            "irrelevant",
            None,
        ),
        (
            {
                "cik": "value",
                "filings": {"recent": {"form": ["not-10-K"], "accessionNumber": [123]}},
            },
            "10-K",
            None,
        ),
        (
            {
                "cik": "0451",
                "filings": {"recent": {"form": ["10-K"], "accessionNumber": [123]}},
            },
            "10-K",
            "https://www.sec.gov/Archives/edgar/data/451/123.txt",
        ),
    ],
    ids=[
        "Missing 'cik' key",
        "Missing 'filings' key",
        "Missing 'recent' key under 'filings'",
        "Missing 'accessionNumber' key under 'recent'",
        "Missing 'form' key under 'recent'",
        "File type not found in recent filings",
        "Successful URL extraction",
    ],
)
def test_secgov_url_constructor_get_file_url(
    submission_data: dict, file_type: str, expected_url: str | None
):
    """Test SecGovUrlConstructor.get_file_url method."""
    cik_padded: str = submission_data.get("cik", "").zfill(10)
    mock_storage: MagicMock = MagicMock()
    mock_storage.get_value_from_storage.return_value = cik_padded

    url_constructor: SecGovUrlConstructor = SecGovUrlConstructor(
        name="Apple",
        file_type=file_type,
        storage=mock_storage,
    )

    mock_response: MagicMock = MagicMock()
    mock_response.json.return_value = submission_data
    mock_response.raise_for_status = MagicMock()

    with patch(
        "app.lib.processing.requests.get", return_value=mock_response
    ) as mock_get:
        result_url: str | None = url_constructor.get_file_url()

        if expected_url is None:
            assert result_url is expected_url
        else:
            assert result_url == expected_url

        mock_storage.get_value_from_storage.assert_called_once_with("Apple")

        submissions_url: str = f"https://data.sec.gov/submissions/CIK{cik_padded}.json"
        mock_get.assert_called_once_with(
            url=submissions_url,
            headers=config.REQUEST_HEADERS,
            timeout=10,
        )


@pytest.mark.parametrize(
    "raises_exception",
    [
        False,
        True,
    ],
)
def test_save_to_storage(raises_exception):
    """Test PDFExporter.save_to_storage method."""
    with patch("app.lib.processing.requests.get") as mock_get:
        if raises_exception:
            mock_get.side_effect = requests.RequestException("Request failed")
        else:
            mock_response = MagicMock()
            mock_response.text = f"{uuid.uuid4()}"
            mock_response.raise_for_status = MagicMock()
            mock_get.return_value = mock_response

        mock_storage = MagicMock(FileStorage)
        mock_storage.upload.return_value = f"{uuid.uuid4()}"
        exporter = PDFExporter(mock_storage)

        filing_url = f"{uuid.uuid4()}"
        file_name = f"{uuid.uuid4()}"

        if raises_exception:
            with pytest.raises(RuntimeError):
                exporter.save_to_storage("http://dummy-url.com", "output.pdf")
                mock_storage.upload.assert_not_called()
        else:
            result = exporter.save_to_storage(filing_url, file_name)

            mock_get.assert_called_once_with(
                url=filing_url, headers=config.REQUEST_HEADERS, timeout=10
            )
            mock_storage.upload.assert_called_once()
            assert result == mock_storage.upload.return_value
