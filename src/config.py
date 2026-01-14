import tomllib
from pathlib import Path

import typer

_config_file = Path(__file__).parent.parent / "pyproject.toml"
with _config_file.open("rb") as f:
    _config = tomllib.load(f)

_project_config = _config["project"]
_tool_config = _config["tool"]["config"]

PROJECT_NAME = _project_config["name"]
PROJECT_VERSION = _project_config["version"]

FLASK_PORT = _tool_config["flask_port"]
MAX_UPLOAD_SIZE_MB = _tool_config["max_upload_size_mb"]
DEFAULT_TARGET_CURRENCY = _tool_config["default_target_currency"]
DEFAULT_OPENAI_MODEL = _tool_config["default_openai_model"]

# Cache directory for all services
CACHE_DIR = Path(".cache")


def config_cli(
    all: bool = typer.Option(False, "--all", help="Show all configuration values"),
    project_name: bool = typer.Option(False, "--project-name", help=PROJECT_NAME),
    project_version: bool = typer.Option(False, "--project-version", help=PROJECT_VERSION),
    flask_port: bool = typer.Option(False, "--flask-port", help=str(FLASK_PORT)),
    max_upload_size_mb: bool = typer.Option(False, "--max-upload-size-mb", help=str(MAX_UPLOAD_SIZE_MB)),
    default_target_currency: bool = typer.Option(
        False, "--default-target-currency", help=DEFAULT_TARGET_CURRENCY
    ),
    default_openai_model: bool = typer.Option(False, "--default-openai-model", help=DEFAULT_OPENAI_MODEL),
) -> None:
    """Get configuration values from pyproject.toml.

    Only non-secret configuration is exposed via this CLI.
    Secrets should be imported directly from src.values in your code.
    """
    if all:
        typer.echo(f"project_name={PROJECT_NAME}")
        typer.echo(f"project_version={PROJECT_VERSION}")
        typer.echo(f"flask_port={FLASK_PORT}")
        typer.echo(f"max_upload_size_mb={MAX_UPLOAD_SIZE_MB}")
        typer.echo(f"default_target_currency={DEFAULT_TARGET_CURRENCY}")
        typer.echo(f"default_openai_model={DEFAULT_OPENAI_MODEL}")
        return

    param_map = {
        project_name: PROJECT_NAME,
        project_version: PROJECT_VERSION,
        flask_port: FLASK_PORT,
        max_upload_size_mb: MAX_UPLOAD_SIZE_MB,
        default_target_currency: DEFAULT_TARGET_CURRENCY,
        default_openai_model: DEFAULT_OPENAI_MODEL,
    }

    for is_set, value in param_map.items():
        if is_set:
            typer.echo(value)
            return

    typer.secho(
        "Error: No config key specified. Use --help to see available options.",
        fg=typer.colors.RED,
        err=True,
    )
    raise typer.Exit(1)


def main():
    typer.run(config_cli)


if __name__ == "__main__":
    main()
