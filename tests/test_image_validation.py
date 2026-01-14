"""Tests for image validation."""

import io
from pathlib import Path

import pytest
from PIL import Image

from src.image_validation import ImageValidationError
from src.image_validation import save_uploaded_image
from src.image_validation import validate_image_file


def create_test_image(format: str = "JPEG") -> bytes:
    """Create a test image in memory."""
    img = Image.new("RGB", (100, 100), color="red")
    buffer = io.BytesIO()
    img.save(buffer, format=format)
    return buffer.getvalue()


@pytest.mark.parametrize(
    "format,extension",
    [
        ("JPEG", "jpeg"),
        ("JPEG", "jpg"),
        ("PNG", "png"),
        ("WEBP", "webp"),
    ],
)
def test_validate_image_file_valid_formats(format: str, extension: str):
    """Test validation accepts supported image formats."""
    image_data = create_test_image(format)
    validate_image_file(image_data, f"test.{extension}")


def test_validate_image_file_invalid_format():
    """Test validation rejects unsupported formats."""
    image_data = create_test_image("JPEG")
    with pytest.raises(ImageValidationError, match="Unsupported file format"):
        validate_image_file(image_data, "test.avi")


def test_validate_image_file_too_large():
    """Test validation rejects files exceeding size limit."""
    large_data = b"x" * (11 * 1024 * 1024)
    with pytest.raises(ImageValidationError, match="exceeds maximum"):
        validate_image_file(large_data, "test.jpg")


def test_validate_image_file_invalid_image():
    """Test validation rejects invalid image data."""
    invalid_data = b"not an image"
    with pytest.raises(ImageValidationError, match="Invalid image file"):
        validate_image_file(invalid_data, "test.jpeg")


def test_save_uploaded_image(tmp_path: Path):
    """Test saving uploaded image."""
    image_data = create_test_image()
    file_path = save_uploaded_image(image_data, "test.jpeg")

    assert file_path.exists()
    assert file_path.suffix == ".jpeg"
    assert file_path.read_bytes() == image_data


def test_validate_image_file_empty_filename():
    """Test validation rejects empty filename."""
    image_data = create_test_image()
    with pytest.raises(ImageValidationError, match="Filename cannot be empty"):
        validate_image_file(image_data, "")


def test_validate_image_file_empty_content():
    """Test validation rejects empty file content."""
    with pytest.raises(ImageValidationError, match="File is empty"):
        validate_image_file(b"", "test.jpg")
