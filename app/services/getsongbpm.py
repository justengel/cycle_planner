import httpx
from app.config import get_settings

GETSONGBPM_API_URL = "https://api.getsongbpm.com"


async def search_song_bpm(song_name: str, artist: str | None = None) -> dict | None:
    """Search for a song's BPM and other audio features using GetSongBPM API."""
    settings = get_settings()

    if not settings.getsongbpm_api_key:
        print("[getsongbpm] No API key configured")
        return None

    # Build search query
    query = song_name
    if artist:
        query = f"{song_name} {artist}"

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{GETSONGBPM_API_URL}/search/",
                params={
                    "api_key": settings.getsongbpm_api_key,
                    "type": "song",
                    "lookup": query,
                },
                timeout=10.0,
            )

            print(f"[getsongbpm] Search for '{query}' status={response.status_code}")

            if response.status_code != 200:
                print(f"[getsongbpm] Error: {response.text}")
                return None

            data = response.json()

            # GetSongBPM returns a search array
            if data.get("search") and len(data["search"]) > 0:
                song = data["search"][0]
                result = {
                    "tempo": int(song.get("tempo", 0)) if song.get("tempo") else None,
                    "key": song.get("key_of"),
                    "source": "getsongbpm",
                }
                print(f"[getsongbpm] Found: {result}")
                return result

            print("[getsongbpm] No results found")
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
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{GETSONGBPM_API_URL}/song/",
                params={
                    "api_key": settings.getsongbpm_api_key,
                    "id": song_id,
                },
                timeout=10.0,
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
