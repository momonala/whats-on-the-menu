"""Flask application for menu translation."""

import logging
from pathlib import Path

from flask import Flask
from flask import jsonify
from flask import render_template
from flask import request

from src.config import DEFAULT_OPENAI_MODEL
from src.config import DEFAULT_TARGET_CURRENCY
from src.config import FLASK_PORT
from src.config import MAX_UPLOAD_SIZE_MB
from src.image_validation import ImageValidationError
from src.image_validation import save_uploaded_image
from src.services.image_search_brave import ImageSearchError
from src.services.image_search_brave import cached_brave_search
from src.services.openai_service import TranslationError
from src.services.openai_service import translate_menu_image
from src.values import BRAVE_API_KEY

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

project_root = Path(__file__).parent.parent
app = Flask(
    __name__,
    template_folder=str(project_root / "templates"),
    static_folder=str(project_root / "static"),
)
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_SIZE_MB * 1024 * 1024


@app.route("/")
def index():
    """Serve the main page."""
    return render_template("index.html")


@app.route("/status")
def status():
    """Health check endpoint."""
    return jsonify({"status": "ok"})


@app.route("/api/translate", methods=["POST"])
def translate_menu():
    """Translate a menu image.

    Returns:
        JSON response with translated menu data or error message.
    """
    if "image" not in request.files:
        return jsonify({"status": "error", "message": "No image file provided"}), 400

    file = request.files["image"]
    target_currency = request.form.get("currency", DEFAULT_TARGET_CURRENCY)
    model = request.form.get("model", DEFAULT_OPENAI_MODEL)
    include_images = request.form.get("include_images", "true").lower() == "true"
    file_content = file.read()
    filename = file.filename
    image_path = None
    try:
        image_path = save_uploaded_image(file_content, filename)
    except ImageValidationError as e:
        return jsonify({"status": "error", "message": str(e)}), 400

    try:
        translation = translate_menu_image(image_path, target_currency, model)

        dishes_data = []
        for dish in translation.dishes:
            if include_images:
                try:
                    search_results = cached_brave_search(
                        dish.name, translation.source_language, BRAVE_API_KEY
                    )
                    if search_results:
                        dish.image_urls = search_results
                    else:
                        placeholder_url = (
                            f"https://via.placeholder.com/400x300?text={dish.name.replace(' ', '+')}"
                        )
                        dish.image_urls = [placeholder_url]
                except ImageSearchError as e:
                    logger.warning(f"Image search failed for '{dish.name}': {e}")
                    dish.image_urls = None
            else:
                dish.image_urls = None
            dishes_data.append(dish.model_dump())

        return jsonify(
            {
                "status": "success",
                "data": {
                    "source_language": translation.source_language,
                    "dishes": dishes_data,
                    "original_currency": translation.original_currency,
                    "exchange_rate_to_eur": translation.exchange_rate_to_eur,
                    "target_currency": translation.target_currency,
                },
            }
        )
    except TranslationError as e:
        logger.error(f"Translation error: {e}")
        return jsonify({"status": "error", "message": f"Translation failed: {e}"}), 500
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return jsonify({"status": "error", "message": "An unexpected error occurred during translation"}), 500
    finally:
        if image_path:
            image_path.unlink(missing_ok=True)


def main():
    """Run the Flask application."""
    app.run(host="0.0.0.0", port=FLASK_PORT, debug=False)


if __name__ == "__main__":
    main()
