import httpx
from urllib.parse import urlparse
from app.config import get_settings

GETSONGBPM_API_URL = "https://api.getsong.co"


def _get_user_agent() -> str:
    """Build User-Agent with backlink URL derived from Spotify redirect URI."""
    settings = get_settings()
    if settings.spotify_redirect_uri:
        parsed = urlparse(settings.spotify_redirect_uri)
        site_url = f"{parsed.scheme}://{parsed.netloc}"
    else:
        site_url = "http://localhost:8000"
    return f"CyclePlanner/1.0 ({site_url})"


async def search_song_bpm(song_name: str, artist: str | None = None) -> dict | None:
    """Search for a song's BPM and other audio features using GetSongBPM API."""
    settings = get_settings()

    if not settings.getsongbpm_api_key:
        print("[getsongbpm] No API key configured")
        return None

    # Build search query - use just song name for broader matches
    query = song_name

    try:
        async with httpx.AsyncClient(headers={"User-Agent": _get_user_agent()}) as client:
            response = await client.get(
                f"{GETSONGBPM_API_URL}/search/",
                params={
                    "api_key": settings.getsongbpm_api_key,
                    "type": "song",
                    "lookup": query,
                },
                timeout=3.0,
            )

            print(f"[getsongbpm] Search for '{query}' status={response.status_code}")

            if response.status_code != 200:
                print(f"[getsongbpm] Error: {response.text}")
                return None

            data = response.json()

            # GetSongBPM returns a list on success, dict with error on failure
            search_results = data.get("search")
            if isinstance(search_results, list) and len(search_results) > 0:
                song = search_results[0]
                result = {
                    "tempo": int(song.get("tempo", 0)) if song.get("tempo") else None,
                    "key": song.get("key_of"),
                    "source": "getsongbpm",
                }
                print(f"[getsongbpm] Found: {result}")
                return result

            print(f"[getsongbpm] No results for '{query}'")
            return None

    except Exception as e:
        print(f"[getsongbpm] Exception: {e}")
        return None


async def get_song_by_id(song_id: str) -> dict | None:
    """Get song details by GetSongBPM song ID."""
    settings = get_settings()

    if not settings.getsongbpm_api_key:
        return None

    try:
        async with httpx.AsyncClient(headers={"User-Agent": _get_user_agent()}) as client:
            response = await client.get(
                f"{GETSONGBPM_API_URL}/song/",
                params={
                    "api_key": settings.getsongbpm_api_key,
                    "id": song_id,
                },
                timeout=3.0,
            )

            if response.status_code == 200:
                data = response.json()
                if data.get("song"):
                    song = data["song"]
                    return {
                        "tempo": int(song.get("tempo", 0)) if song.get("tempo") else None,
                        "key": song.get("key_of"),
                        "source": "getsongbpm",
                    }
            return None

    except Exception as e:
        print(f"[getsongbpm] Exception getting song by ID: {e}")
        return None
