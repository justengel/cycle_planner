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
            return response.json()
        return None


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
