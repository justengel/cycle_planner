from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    app_env: str = "development"
    app_secret_key: str = "change-me-in-production"

    anthropic_api_key: str

    supabase_url: str
    supabase_key: str
    supabase_service_key: str | None = None
    database_url: str | None = None

    # Spotify
    spotify_client_id: str | None = None
    spotify_client_secret: str | None = None
    spotify_redirect_uri: str = "http://localhost:8000/api/spotify/callback"

    # GetSongBPM (fallback for audio features)
    getsongbpm_api_key: str | None = None

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()
