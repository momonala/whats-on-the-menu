"""Tests for OpenAI service."""

from pathlib import Path
from unittest.mock import patch

import pytest

from src.datamodels import MenuTranslation
from src.services.openai_service import TranslationError
from src.services.openai_service import translate_menu_image


def create_test_image_file(tmp_path: Path) -> Path:
    """Create a test image file."""
    from PIL import Image

    img = Image.new("RGB", (100, 100), color="red")
    file_path = tmp_path / "test_menu.jpg"
    img.save(file_path, "JPEG")
    return file_path


def create_openai_response_dict(
    source_language: str,
    country: str,
    dishes: list[dict],
    original_currency: str | None = None,
) -> dict:
    """Create an OpenAI response dict for mocking."""
    return {
        "source_language": source_language,
        "country": country,
        "dishes": dishes,
        "original_currency": original_currency,
    }


@patch("src.services.openai_service.get_exchange_rate")
@patch("src.services.openai_service._cached_translate")
def test_translate_menu_image_success(mock_cached_translate, mock_get_exchange_rate, tmp_path: Path):
    """Test successful menu translation."""
    image_path = create_test_image_file(tmp_path)

    mock_cached_translate.return_value = create_openai_response_dict(
        source_language="Spanish",
        country="Spain",
        original_currency="EUR",
        dishes=[
            {
                "name": "Paella Valenciana",
                "english_name": "Valencian Paella",
                "description": "Traditional Spanish rice dish with seafood.",
                "pronunciation": "pie-AY-uh val-en-see-AH-nuh",
                "original_text": "Paella Valenciana",
                "price": "€18.00",
                "price_numeric": None,
            }
        ],
    )
    mock_get_exchange_rate.return_value = 1.0

    result = translate_menu_image(image_path)

    assert isinstance(result, MenuTranslation)
    assert result.source_language == "Spanish"
    assert len(result.dishes) == 1
    assert result.dishes[0].name == "Paella Valenciana"
    assert result.dishes[0].description == "Traditional Spanish rice dish with seafood."
    assert result.dishes[0].original_text == "Paella Valenciana"

    mock_cached_translate.assert_called_once()


@patch("src.services.openai_service.get_exchange_rate")
@patch("src.services.openai_service._cached_translate")
def test_translate_menu_image_multiple_dishes(mock_cached_translate, mock_get_exchange_rate, tmp_path: Path):
    """Test translation with multiple dishes."""
    image_path = create_test_image_file(tmp_path)

    mock_cached_translate.return_value = create_openai_response_dict(
        source_language="French",
        country="France",
        original_currency="EUR",
        dishes=[
            {
                "name": "Coq au Vin",
                "english_name": "Chicken in Wine",
                "description": "Chicken braised with wine.",
                "pronunciation": "coke oh van",
                "original_text": "Coq au Vin",
                "price": "€22.50",
                "price_numeric": None,
            },
            {
                "name": "Bouillabaisse",
                "english_name": "Provençal Fish Stew",
                "description": "Provençal fish stew.",
                "pronunciation": "boo-yah-BAYS",
                "original_text": "Bouillabaisse",
                "price": None,
                "price_numeric": None,
            },
        ],
    )
    mock_get_exchange_rate.return_value = 1.0

    result = translate_menu_image(image_path)

    assert len(result.dishes) == 2
    assert result.dishes[0].name == "Coq au Vin"
    assert result.dishes[1].name == "Bouillabaisse"


@patch("src.services.openai_service._cached_translate")
def test_translate_menu_image_file_not_found(mock_cached_translate):
    """Test error when image file doesn't exist."""
    image_path = Path("nonexistent.jpg")

    with pytest.raises(FileNotFoundError):
        translate_menu_image(image_path)

    mock_cached_translate.assert_not_called()


@patch("src.services.openai_service._cached_translate")
def test_translate_menu_image_translation_error_propagates(mock_cached_translate, tmp_path: Path):
    """Test that TranslationError from _cached_translate propagates."""
    image_path = create_test_image_file(tmp_path)

    mock_cached_translate.side_effect = TranslationError("API error")

    with pytest.raises(TranslationError, match="API error"):
        translate_menu_image(image_path)


@patch("src.services.openai_service.get_exchange_rate")
@patch("src.services.openai_service._cached_translate")
def test_translate_menu_image_with_custom_currency(
    mock_cached_translate, mock_get_exchange_rate, tmp_path: Path
):
    """Test translation with custom target currency."""
    image_path = create_test_image_file(tmp_path)

    mock_cached_translate.return_value = create_openai_response_dict(
        source_language="Italian",
        country="Italy",
        original_currency="EUR",
        dishes=[
            {
                "name": "Pasta",
                "english_name": "Pasta",
                "description": "Italian pasta dish.",
                "pronunciation": "PAH-stuh",
                "original_text": "Pasta",
                "price": "€12.00",
                "price_numeric": None,
            }
        ],
    )
    mock_get_exchange_rate.return_value = 1.1

    result = translate_menu_image(image_path, target_currency="USD")

    assert result.source_language == "Italian"
    assert result.target_currency == "USD"


@patch("src.services.openai_service.get_exchange_rate")
@patch("src.services.openai_service._cached_translate")
def test_translate_menu_image_forex_fetch_failure(
    mock_cached_translate, mock_get_exchange_rate, tmp_path: Path
):
    """Test handling when forex fetch fails - prices should not be converted."""
    image_path = create_test_image_file(tmp_path)

    mock_cached_translate.return_value = create_openai_response_dict(
        source_language="English",
        country="United States",
        original_currency="USD",
        dishes=[
            {
                "name": "Burger",
                "english_name": "Burger",
                "description": "A burger.",
                "pronunciation": "BUR-ger",
                "original_text": "Burger",
                "price": "$10.00",
                "price_numeric": 10.0,
            }
        ],
    )
    mock_get_exchange_rate.return_value = None

    result = translate_menu_image(image_path, target_currency="EUR")

    assert result.dishes[0].converted_price is None


@patch("src.services.openai_service.get_exchange_rate")
@patch("src.services.openai_service._cached_translate")
def test_translate_menu_image_same_currency_no_conversion(
    mock_cached_translate, mock_get_exchange_rate, tmp_path: Path
):
    """Test that same source and target currency uses 1.0 exchange rate."""
    image_path = create_test_image_file(tmp_path)

    mock_cached_translate.return_value = create_openai_response_dict(
        source_language="German",
        country="Germany",
        original_currency="EUR",
        dishes=[
            {
                "name": "Schnitzel",
                "english_name": "Schnitzel",
                "description": "Breaded cutlet.",
                "pronunciation": "SHNIT-sel",
                "original_text": "Schnitzel",
                "price": "€15.00",
                "price_numeric": 15.0,
            }
        ],
    )

    result = translate_menu_image(image_path, target_currency="EUR")

    # Should not call get_exchange_rate when currencies match
    mock_get_exchange_rate.assert_not_called()
    assert result.exchange_rate_to_eur == 1.0
    assert result.dishes[0].converted_price == 15.0


@patch("src.services.openai_service.get_exchange_rate")
@patch("src.services.openai_service._cached_translate")
def test_translate_menu_image_price_conversion(mock_cached_translate, mock_get_exchange_rate, tmp_path: Path):
    """Test that prices are correctly converted using exchange rate."""
    image_path = create_test_image_file(tmp_path)

    mock_cached_translate.return_value = create_openai_response_dict(
        source_language="Japanese",
        country="Japan",
        original_currency="JPY",
        dishes=[
            {
                "name": "Ramen",
                "english_name": "Ramen",
                "description": "Japanese noodle soup.",
                "pronunciation": "RAH-men",
                "original_text": "ラーメン",
                "price": "¥1000",
                "price_numeric": 1000.0,
            }
        ],
    )
    mock_get_exchange_rate.return_value = 0.0067  # 1 JPY = 0.0067 EUR

    result = translate_menu_image(image_path, target_currency="EUR")

    assert result.dishes[0].converted_price == pytest.approx(6.7, rel=0.01)
