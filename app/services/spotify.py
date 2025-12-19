import base64
import urllib.parse
from typing import Optional
import httpx

from app.config import get_settings

SPOTIFY_AUTH_URL = "https://accounts.spotify.com/authorize"
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_API_URL = "https://api.spotify.com/v1"

SCOPES = [
    "streaming",
    "user-read-email",
    "user-read-private",
    "user-read-playback-state",
    "user-modify-playback-state",
    "playlist-read-private",
    "playlist-modify-public",
    "playlist-modify-private",
]


def get_auth_url(state: str) -> str:
    """Generate Spotify OAuth authorization URL."""
    settings = get_settings()
    params = {
        "client_id": settings.spotify_client_id,
        "response_type": "code",
        "redirect_uri": settings.spotify_redirect_uri,
        "scope": " ".join(SCOPES),
        "state": state,
    }
    return f"{SPOTIFY_AUTH_URL}?{urllib.parse.urlencode(params)}"


async def exchange_code(code: str) -> dict:
    """Exchange authorization code for access token."""
    settings = get_settings()

    auth_header = base64.b64encode(
        f"{settings.spotify_client_id}:{settings.spotify_client_secret}".encode()
    ).decode()

    async with httpx.AsyncClient() as client:
        response = await client.post(
            SPOTIFY_TOKEN_URL,
            headers={
                "Authorization": f"Basic {auth_header}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": settings.spotify_redirect_uri,
            },
        )
        response.raise_for_status()
        return response.json()


async def refresh_access_token(refresh_token: str) -> dict:
    """Refresh an expired access token."""
    settings = get_settings()

    auth_header = base64.b64encode(
        f"{settings.spotify_client_id}:{settings.spotify_client_secret}".encode()
    ).decode()

    async with httpx.AsyncClient() as client:
        response = await client.post(
            SPOTIFY_TOKEN_URL,
            headers={
                "Authorization": f"Basic {auth_header}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
            },
        )
        response.raise_for_status()
        return response.json()


async def search_tracks(query: str, access_token: str, limit: int = 10) -> dict:
    """Search for tracks on Spotify."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{SPOTIFY_API_URL}/search",
            headers={"Authorization": f"Bearer {access_token}"},
            params={
                "q": query,
                "type": "track",
                "limit": limit,
            },
        )
        response.raise_for_status()
        return response.json()


async def get_track(track_id: str, access_token: str) -> dict:
    """Get track details."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{SPOTIFY_API_URL}/tracks/{track_id}",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        response.raise_for_status()
        return response.json()


async def get_user_profile(access_token: str) -> dict:
    """Get current user's Spotify profile."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{SPOTIFY_API_URL}/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        response.raise_for_status()
        return response.json()


async def get_audio_features(track_id: str, access_token: str) -> dict | None:
    """Get audio features (tempo, energy, etc.) for a track."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{SPOTIFY_API_URL}/audio-features/{track_id}",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if response.status_code == 200:
            data = response.json()
            if data and data.get("tempo"):
                print(f"[spotify] Audio features for {track_id}: tempo={data.get('tempo')}")
                return data
            print(f"[spotify] Audio features empty for {track_id}")
            return None
        print(f"[spotify] Audio features failed for {track_id}: {response.status_code}")
        return None


async def get_audio_features_batch(track_ids: list[str], access_token: str) -> dict[str, dict]:
    """Get audio features for multiple tracks in one request (max 100)."""
    if not track_ids:
        return {}

    results = {}
    async with httpx.AsyncClient() as client:
        # Process in batches of 100 (Spotify limit)
        for i in range(0, len(track_ids), 100):
            batch = track_ids[i:i + 100]
            try:
                response = await client.get(
                    f"{SPOTIFY_API_URL}/audio-features",
                    headers={"Authorization": f"Bearer {access_token}"},
                    params={"ids": ",".join(batch)},
                )
                if response.status_code == 200:
                    data = response.json()
                    for feature in data.get("audio_features", []):
                        if feature and feature.get("id"):
                            results[feature["id"]] = feature
            except Exception as e:
                print(f"[spotify] Batch audio features failed: {e}")

    return results


async def create_playlist(
    access_token: str,
    name: str,
    description: str = "",
    public: bool = False,
) -> dict:
    """Create a new playlist for the current user."""
    profile = await get_user_profile(access_token)
    user_id = profile["id"]

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{SPOTIFY_API_URL}/users/{user_id}/playlists",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            json={
                "name": name,
                "description": description,
                "public": public,
            },
        )
        response.raise_for_status()
        return response.json()


async def add_tracks_to_playlist(
    access_token: str,
    playlist_id: str,
    track_uris: list[str],
) -> dict:
    """Add tracks to a playlist."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{SPOTIFY_API_URL}/playlists/{playlist_id}/tracks",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            json={"uris": track_uris},
        )
        response.raise_for_status()
        return response.json()


async def get_user_playlists(access_token: str, limit: int = 50) -> list[dict]:
    """Get current user's playlists."""
    playlists = []
    async with httpx.AsyncClient() as client:
        url = f"{SPOTIFY_API_URL}/me/playlists"
        params = {"limit": limit}

        while url:
            response = await client.get(
                url,
                headers={"Authorization": f"Bearer {access_token}"},
                params=params if "api.spotify.com" in url else None,
            )
            response.raise_for_status()
            data = response.json()

            for item in data.get("items", []):
                images = item.get("images") or []
                playlists.append({
                    "id": item["id"],
                    "name": item["name"],
                    "image": images[0]["url"] if images else None,
                    "track_count": item["tracks"]["total"],
                    "owner": item["owner"]["display_name"],
                })

            url = data.get("next")
            params = None  # Next URL includes params

    return playlists


async def get_playlist_tracks(access_token: str, playlist_id: str) -> list[dict]:
    """Get all tracks from a playlist."""
    tracks = []
    async with httpx.AsyncClient() as client:
        url = f"{SPOTIFY_API_URL}/playlists/{playlist_id}/tracks"
        params = {"limit": 100}

        while url:
            response = await client.get(
                url,
                headers={"Authorization": f"Bearer {access_token}"},
                params=params if "api.spotify.com" in url else None,
            )
            response.raise_for_status()
            data = response.json()

            for item in data.get("items", []):
                track = item.get("track")
                if track and track.get("id"):  # Skip local files
                    tracks.append({
                        "id": track["id"],
                        "uri": track["uri"],
                        "name": track["name"],
                        "artist": track["artists"][0]["name"] if track.get("artists") else "",
                        "duration_ms": track.get("duration_ms", 0),
                    })

            url = data.get("next")
            params = None

    return tracks
