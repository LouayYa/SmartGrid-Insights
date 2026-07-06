import os

from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Application configuration loaded from environment variables."""

    # DATABASE_URL format examples:
    #   SQLite (dev fallback):  sqlite:///./household_power.db
    #   postgres:   postgresql://<user>:<pwd>@<server>/<db>
    
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "sqlite:///./household_power.db",
    )

    # App metadata
    APP_NAME: str = "Data Ingestion Service"
    APP_VERSION: str = "0.1.0"


settings = Settings()
