"""Tests for upload handler (Flask routes)."""

import io
import json
from unittest.mock import patch

import pytest
from PIL import Image

from src.app import app


@pytest.fixture
def client():
    """Create test client."""
    app.config["TESTING"] = True
    with app.test_client() as test_client:
        yield test_client


@pytest.fixture
def sample_image():
    """Create sample image bytes."""
    img = Image.new("RGB", (100, 100), color="red")
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG")
    return buffer.getvalue()


def test_status_endpoint(client):
    """Test health check endpoint."""
    response = client.get("/status")
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["status"] == "ok"


def test_index_endpoint(client):
    """Test main page endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    assert b"What's On the Menu?" in response.data


@patch("src.app.cached_brave_search")
@patch("src.app.translate_menu_image")
@patch("src.app.save_uploaded_image")
def test_translate_endpoint_success(
    mock_save,
    mock_translate,
    mock_brave_search,
    client,
    sample_image,
    tmp_path,
):
    """Test successful translation."""
    image_path = tmp_path / "test.jpg"
    image_path.write_bytes(sample_image)
    mock_save.return_value = image_path
    mock_brave_search.return_value = None

    from src.datamodels import MenuDish
    from src.datamodels import MenuTranslation

    mock_translation = MenuTranslation(
        dishes=[
            MenuDish(
                name="Paella",
                english_name="Paella",
                description="Spanish rice dish.",
                image_urls=None,
                original_text="Paella",
                pronunciation="pie-AY-uh",
                price="€15.50",
            )
        ],
        source_language="Spanish",
        country="Spain",
        original_currency="EUR",
        exchange_rate_to_eur=1.0,
        target_currency="EUR",
    )
    mock_translate.return_value = mock_translation

    response = client.post(
        "/api/translate",
        data={"image": (io.BytesIO(sample_image), "test.jpg")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["status"] == "success"
    assert data["data"]["source_language"] == "Spanish"
    assert len(data["data"]["dishes"]) == 1
    assert data["data"]["dishes"][0]["name"] == "Paella"
    assert "placeholder.com" in data["data"]["dishes"][0]["image_urls"][0]


def test_translate_endpoint_no_file(client):
    """Test translation endpoint with no file."""
    response = client.post("/api/translate")
    assert response.status_code == 400
    data = json.loads(response.data)
    assert data["status"] == "error"
    assert "No image file provided" in data["message"]


def test_translate_endpoint_empty_filename(client):
    """Test translation endpoint with empty filename."""
    response = client.post(
        "/api/translate",
        data={"image": (b"", "")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 400
    data = json.loads(response.data)
    assert data["status"] == "error"


@patch("src.app.save_uploaded_image")
def test_translate_endpoint_validation_error(mock_save, client, sample_image):
    """Test translation endpoint handles validation errors."""
    from src.image_validation import ImageValidationError

    mock_save.side_effect = ImageValidationError("File too large")

    response = client.post(
        "/api/translate",
        data={"image": (io.BytesIO(sample_image), "test.jpg")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 400
    data = json.loads(response.data)
    assert data["status"] == "error"
    assert "File too large" in data["message"]


@patch("src.app.save_uploaded_image")
@patch("src.app.translate_menu_image")
def test_translate_endpoint_translation_error(mock_translate, mock_save, client, sample_image, tmp_path):
    """Test translation endpoint handles translation errors."""
    image_path = tmp_path / "test.jpg"
    image_path.write_bytes(sample_image)
    mock_save.return_value = image_path

    mock_translate.side_effect = ValueError("Invalid response")

    response = client.post(
        "/api/translate",
        data={"image": (io.BytesIO(sample_image), "test.jpg")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 500
    data = json.loads(response.data)
    assert data["status"] == "error"
