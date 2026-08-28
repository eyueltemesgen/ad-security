"""Application configuration.

All secrets and environment-specific values are read from environment
variables.  See .env.example for the full list.
"""
import os


class Config:
    """Base configuration."""

    BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))

    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-change-me-in-production")

    # SQLite by default; override with DATABASE_URL for Postgres/MySQL.
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "sqlite:///" + os.path.join(BASE_DIR, "app.db"),
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}

    # Uploads
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "app", "static", "img", "uploads")
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    ALLOWED_IMAGE_TYPES = {"png", "jpg", "jpeg", "gif", "webp", "svg"}
    ALLOWED_DOCUMENT_TYPES = {"pdf", "doc", "docx", "txt", "png", "jpg", "jpeg"}

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    REMEMBER_COOKIE_HTTPONLY = True

    # Mail (SMTP) - optional. Used for forgot password etc. Falls back to
    # a token-based reset shown on-screen when SMTP is not configured.
    MAIL_SERVER = os.environ.get("MAIL_SERVER", "")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", 587))
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME", "")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD", "")
    MAIL_FROM = os.environ.get("MAIL_FROM", "noreply@adsecurity.example")
    MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS", "1") == "1"
    MAIL_USE_SSL = os.environ.get("MAIL_USE_SSL", "0") == "1"

    # Allow uploading service request photos/documents
    SERVICE_FILE_TYPES = ALLOWED_IMAGE_TYPES.union(ALLOWED_DOCUMENT_TYPES)


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False