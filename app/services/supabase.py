from supabase import create_client, Client
from functools import lru_cache

from app.config import get_settings

# Type alias for clarity
SupabaseClient = Client


@lru_cache
def get_supabase_client() -> SupabaseClient:
    """Get a cached Supabase client instance."""
    settings = get_settings()
    return create_client(settings.supabase_url, settings.supabase_key)
