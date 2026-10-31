"""Central configuration: the only module that reads environment variables.

Values are read on access (not cached at import), so tests and long-running
processes see environment changes, like the per-request VAT rounding method.
"""
import os

from dotenv import load_dotenv

load_dotenv()  # optional python/.env; real environment variables take precedence

TRAINING_VALUES = ("1", "true", "yes", "on")
DEFAULT_CORS_ORIGINS = "http://localhost:5173,http://127.0.0.1:5173"
DEFAULT_AUTH_SECRET = "dev-secret-change-me-please-set-AUTH_SECRET-in-env"


def env(name: str, default: str | None = None) -> str | None:
    """Raw variable; used by the keyed groups below (`DSFINVK_*`, `SOLL_*`)."""
    return os.getenv(name, default)


def training_mode() -> bool:
    """True when this API instance runs against the disposable training database."""
    return (env("TRAINING_MODE", "") or "").strip().lower() in TRAINING_VALUES


def database_url() -> str:
    """Production MariaDB URL built from `DBHOST`/`DBNAME`/`DBUSER`/`DBPASS`."""
    # engine = create_engine("mariadb+mariadbconnector://<user>:<password>@<host>/<dbname>")
    return (
        f"mariadb+mariadbconnector://{env('DBUSER')}:{env('DBPASS')}"
        f"@{env('DBHOST')}/{env('DBNAME')}"
    )


def training_db_url() -> str:
    url = env("TRAINING_DB_URL")
    if not url:
        raise RuntimeError(
            "TRAINING_MODE is enabled but TRAINING_DB_URL is not set "
            "(e.g. sqlite:///training.db or a separate MariaDB database)"
        )
    return url


def auth_secret() -> str:
    return env("AUTH_SECRET") or env("SECRET_KEY") or DEFAULT_AUTH_SECRET


def auth_token_ttl() -> int:
    return int(env("AUTH_TOKEN_TTL", "3600"))


def cors_origins() -> list[str]:
    raw = env("CORS_ORIGINS", DEFAULT_CORS_ORIGINS) or ""
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


def tse_id() -> int | None:
    """`bc.TSE_ID` of the Java POS: the TSE number stored in `abrechnung_tag_tse`."""
    value = env("TSE_ID")
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def tse_lib_path() -> str | None:
    return env("TSE_LIB_PATH")


def tse_device_path() -> str | None:
    return env("TSE_DEVICE_PATH")


def tse_client_id() -> bytes:
    return (env("TSE_CLIENT_ID", "WeltladenKasse") or "").encode("utf-8")


def dsfinvk_export_dir() -> str | None:
    return env("DSFINVK_EXPORT_DIR")
