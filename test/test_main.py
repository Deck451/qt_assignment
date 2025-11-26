"""Testing main API endpoints module."""

import uuid
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient
from requests import Response


def test_refresh_cik(client: TestClient) -> None:
    """Test the /refresh-cik endpoint."""
    with patch("app.main.refresh_cik_data.run_task.delay") as mock_delay:
        mock_task: MagicMock = MagicMock()
        mock_task.id = f"{uuid.uuid4()}"
        mock_delay.return_value = mock_task

        response: Response = client.post("/refresh-cik")

        assert response.status_code == 200
        assert response.json() == {"task_id": mock_task.id}

        mock_delay.assert_called_once()


def test_get_file(client: TestClient) -> None:
    """Test the /get-file endpoint."""

    with (
        patch("app.main.SecGovUrlConstructor.get_file_url") as mock_get_file,
        patch("app.main.PDFExporter.save_to_storage") as mock_save_to_storage,
        patch("app.main.get_minio_client") as mock_minio_client,
    ):
        mock_save_to_storage.return_value = f"{uuid.uuid4()}"
        mock_minio_client.return_value = MagicMock()
        mock_get_file.return_value = "https://example.com/file.txt"
        response: Response = client.get(
            "/get-file", params={"name": "Apple", "file_type": "10-K", "cik": "123"}
        )

        assert response.status_code == 200
        assert response.json() == {"result": mock_save_to_storage.return_value}
        mock_get_file.assert_called_once()
        mock_save_to_storage.assert_called_once()
