"""Image validation for uploads."""

import logging
import tempfile
from io import BytesIO
from pathlib import Path

from PIL import Image

from src.config import MAX_UPLOAD_SIZE_MB

logger = logging.getLogger(__name__)

SUPPORTED_IMAGE_FORMATS = {"png", "jpeg", "jpg", "webp"}


class ImageValidationError(Exception):
    """Raised when image validation fails."""


def validate_image_file(file_content: bytes, filename: str) -> None:
    """Validate an uploaded image file.

    Args:
        file_content: Raw file content as bytes.
        filename: Original filename.

    Raises:
        ImageValidationError: If validation fails.
    """
    if not filename:
        raise ImageValidationError("Filename cannot be empty")

    if not file_content:
        raise ImageValidationError("File is empty")

    max_size_bytes = MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if len(file_content) > max_size_bytes:
        raise ImageValidationError(
            f"File size ({len(file_content) / (1024 * 1024):.2f}MB) exceeds maximum of {MAX_UPLOAD_SIZE_MB}MB"
        )

    file_path = Path(filename)
    extension = file_path.suffix.lower().lstrip(".")
    if extension not in SUPPORTED_IMAGE_FORMATS:
        raise ImageValidationError(
            f"Unsupported file format: {extension}. "
            f"Supported formats: {', '.join(SUPPORTED_IMAGE_FORMATS)}"
        )

    try:
        image = Image.open(BytesIO(file_content))
        image.verify()
    except (OSError, ValueError, TypeError) as e:
        raise ImageValidationError(f"Invalid image file '{filename}': {e}") from e

    logger.info(f"Image validation passed for file: {filename}")


def save_uploaded_image(file_content: bytes, filename: str) -> Path:
    """Save an uploaded image file to temporary directory.

    Args:
        file_content: Raw file content as bytes.
        filename: Original filename.

    Returns:
        Path to saved temporary file.

    Raises:
        ImageValidationError: If validation fails.
        OSError: If file cannot be saved.
    """
    validate_image_file(file_content, filename)

    suffix = Path(filename).suffix or ".jpg"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
        tmp_file.write(file_content)
        tmp_path = Path(tmp_file.name)

    logger.info(f"Saved uploaded image to temporary file: {tmp_path}")
    return tmp_path
