"""Forex exchange rate service."""

import logging

import requests
from joblib import Memory

from src.config import CACHE_DIR

logger = logging.getLogger(__name__)

memory = Memory(CACHE_DIR / "forex_rates", verbose=0)


@memory.cache
def get_exchange_rate(from_currency: str, to_currency: str) -> float:
    """Cached exchange rate fetch from exchangerate-api.io.

    Args:
        from_currency: Source currency code (e.g., "USD").
        to_currency: Target currency code (e.g., "EUR").

    Returns:
        Exchange rate as float (e.g., 1.08 for USD to EUR).

    Raises:
        ValueError: If API request fails or returns invalid data.
    """
    if from_currency == to_currency:
        return 1.0

    url = f"https://api.exchangerate-api.com/v4/latest/{from_currency}"

    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()

        if "rates" not in data or to_currency not in data["rates"]:
            raise ValueError(f"Currency {to_currency} not found in exchange rate data")

        rate = float(data["rates"][to_currency])
        if rate <= 0:
            raise ValueError(f"Invalid exchange rate: {rate}")

        return rate
    except requests.RequestException as e:
        logger.error(f"Failed to fetch exchange rate: {e}")
        raise ValueError(f"Failed to fetch exchange rate: {e}") from e
    except (KeyError, ValueError, TypeError) as e:
        logger.error(f"Invalid exchange rate response: {e}")
        raise ValueError(f"Invalid exchange rate response: {e}") from e
