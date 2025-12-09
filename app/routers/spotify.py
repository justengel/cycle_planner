import secrets
from fastapi import APIRouter, HTTPException, Request, Response, Depends
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from app.config import get_settings
from app.services import spotify as spotify_service
from app.services import getsongbpm as getsongbpm_service
from app.services.supabase import get_supabase_client, SupabaseClient

router = APIRouter()


@router.get("/login")
async def spotify_login(request: Request):
    """Initiate Spotify OAuth flow."""
    settings = get_settings()
    if not settings.spotify_client_id:
        raise HTTPException(status_code=500, detail="Spotify not configured")

    # Generate state for CSRF protection
    state = secrets.token_urlsafe(16)

    auth_url = spotify_service.get_auth_url(state)

    response = RedirectResponse(url=auth_url)
    response.set_cookie(key="spotify_auth_state", value=state, httponly=True, max_age=600)
    return response


@router.get("/callback")
async def spotify_callback(request: Request, code: str = None, error: str = None, state: str = None):
    """Handle Spotify OAuth callback."""
    if error:
        return RedirectResponse(url=f"/?spotify_error={error}")

    # Verify state (skip in development due to localhost/127.0.0.1 cookie issues)
    settings = get_settings()
    stored_state = request.cookies.get("spotify_auth_state")
    if settings.app_env != "development" and (not state or state != stored_state):
        raise HTTPException(status_code=400, detail="State mismatch")

    try:
        tokens = await spotify_service.exchange_code(code)

        # Get user profile
        profile = await spotify_service.get_user_profile(tokens["access_token"])

        # Redirect to frontend with tokens (stored in fragment for security)
        # Frontend will store these in memory/sessionStorage
        response = RedirectResponse(url="/spotify-connected")

        # Set tokens in HTTP-only cookies for API calls
        response.set_cookie(
            key="spotify_access_token",
            value=tokens["access_token"],
            httponly=True,
            max_age=tokens.get("expires_in", 3600),
            samesite="lax"
        )
        response.set_cookie(
            key="spotify_refresh_token",
            value=tokens.get("refresh_token", ""),
            httponly=True,
            max_age=60 * 60 * 24 * 30,  # 30 days
            samesite="lax"
        )
        response.delete_cookie("spotify_auth_state")

        return response

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to exchange code: {str(e)}")


@router.get("/token")
async def get_token(request: Request):
    """Get current access token for Web Playback SDK."""
    access_token = request.cookies.get("spotify_access_token")
    refresh_token = request.cookies.get("spotify_refresh_token")

    if not access_token and refresh_token:
        # Try to refresh
        try:
            tokens = await spotify_service.refresh_access_token(refresh_token)
            access_token = tokens["access_token"]
            # Note: Would need to set new cookie in response
        except Exception:
            return {"connected": False}

    if not access_token:
        return {"connected": False}

    return {
        "connected": True,
        "access_token": access_token,
    }


@router.post("/refresh")
async def refresh_token(request: Request, response: Response):
    """Refresh the access token."""
    refresh_token = request.cookies.get("spotify_refresh_token")

    if not refresh_token:
        raise HTTPException(status_code=401, detail="No refresh token")

    try:
        tokens = await spotify_service.refresh_access_token(refresh_token)

        response.set_cookie(
            key="spotify_access_token",
            value=tokens["access_token"],
            httponly=True,
            max_age=tokens.get("expires_in", 3600),
            samesite="lax"
        )

        return {
            "access_token": tokens["access_token"],
            "expires_in": tokens.get("expires_in", 3600),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to refresh: {str(e)}")


@router.get("/search")
async def search_tracks(request: Request, q: str, limit: int = 10):
    """Search for tracks on Spotify."""
    access_token = request.cookies.get("spotify_access_token")

    if not access_token:
        raise HTTPException(status_code=401, detail="Not connected to Spotify")

    try:
        results = await spotify_service.search_tracks(q, access_token, limit)

        # Simplify response for frontend
        tracks = []
        for track in results.get("tracks", {}).get("items", []):
            track_data = {
                "id": track["id"],
                "name": track["name"],
                "artist": ", ".join(a["name"] for a in track["artists"]),
                "album": track["album"]["name"],
                "duration_ms": track["duration_ms"],
                "preview_url": track.get("preview_url"),
                "image": track["album"]["images"][0]["url"] if track["album"]["images"] else None,
                "uri": track["uri"],
                "tempo": None,
                "energy": None,
                "valence": None,
                "danceability": None,
            }

            tracks.append(track_data)

        return {"tracks": tracks}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Search failed: {str(e)}")


@router.get("/audio-features/{track_id}")
async def get_track_audio_features(request: Request, response: Response, track_id: str):
    """Get audio features for a track, with GetSongBPM fallback."""
    access_token = request.cookies.get("spotify_access_token")
    refresh_token = request.cookies.get("spotify_refresh_token")

    if not access_token and not refresh_token:
        raise HTTPException(status_code=401, detail="Not connected to Spotify")

    # Try to refresh token if no access token
    if not access_token and refresh_token:
        try:
            tokens = await spotify_service.refresh_access_token(refresh_token)
            access_token = tokens["access_token"]
            response.set_cookie(
                key="spotify_access_token",
                value=access_token,
                httponly=True,
                max_age=tokens.get("expires_in", 3600),
                samesite="lax"
            )
        except Exception:
            raise HTTPException(status_code=401, detail="Failed to refresh token")

    try:
        # Try Spotify first
        audio_features = await spotify_service.get_audio_features(track_id, access_token)

        if audio_features:
            return {
                "tempo": round(audio_features.get("tempo", 0)),
                "energy": round(audio_features.get("energy", 0) * 100),
                "valence": round(audio_features.get("valence", 0) * 100),
                "danceability": round(audio_features.get("danceability", 0) * 100),
            }

        # Spotify failed (403 or other) - try GetSongBPM fallback
        track_info = await spotify_service.get_track(track_id, access_token)
        if track_info:
            song_name = track_info.get("name", "")
            artist = track_info["artists"][0]["name"] if track_info.get("artists") else ""

            # Search GetSongBPM
            bpm_data = await getsongbpm_service.search_song_bpm(song_name, artist)
            if bpm_data and bpm_data.get("tempo"):
                return {
                    "tempo": bpm_data["tempo"],
                    "energy": None,
                    "valence": None,
                    "danceability": None,
                }

        return {"tempo": None, "energy": None, "valence": None, "danceability": None}

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to get audio features: {str(e)}")


@router.post("/logout")
async def spotify_logout(response: Response):
    """Disconnect from Spotify."""
    response.delete_cookie("spotify_access_token")
    response.delete_cookie("spotify_refresh_token")
    return {"message": "Disconnected from Spotify"}


class CreatePlaylistRequest(BaseModel):
    plan_id: str
    public: bool = False


async def get_current_user_id(
    request: Request,
    client: SupabaseClient = Depends(get_supabase_client)
) -> str:
    """Extract and verify user ID from auth cookie."""
    access_token = request.cookies.get("access_token")
    if not access_token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        user_response = client.auth.get_user(access_token)
        if user_response and user_response.user:
            return user_response.user.id
    except Exception:
        pass

    raise HTTPException(status_code=401, detail="Invalid or expired token")


@router.post("/create-playlist")
async def create_playlist_from_plan(
    request: Request,
    body: CreatePlaylistRequest,
    user_id: str = Depends(get_current_user_id),
    client: SupabaseClient = Depends(get_supabase_client),
):
    """Create a Spotify playlist from a saved plan."""
    access_token = request.cookies.get("spotify_access_token")

    if not access_token:
        raise HTTPException(status_code=401, detail="Not connected to Spotify")

    # Fetch the plan
    try:
        plan_response = client.table("lesson_plans").select("*").eq("id", body.plan_id).eq("user_id", user_id).single().execute()
        if not plan_response.data:
            raise HTTPException(status_code=404, detail="Plan not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch plan: {str(e)}")

    plan_data = plan_response.data["plan_json"]
    theme = plan_data.get("theme", "Cycle Class")

    # Extract track URIs from segments
    track_uris = []
    for segment in plan_data.get("segments", []):
        uri = segment.get("spotify_uri")
        if uri and uri not in track_uris:
            track_uris.append(uri)

    if not track_uris:
        raise HTTPException(status_code=400, detail="No Spotify tracks linked to this plan")

    # Create the playlist
    try:
        playlist = await spotify_service.create_playlist(
            access_token=access_token,
            name=f"Cycle Class: {theme}",
            description=f"Generated playlist for {plan_data.get('total_duration_minutes', 0)} minute cycle class",
            public=body.public,
        )

        # Add tracks to the playlist
        await spotify_service.add_tracks_to_playlist(
            access_token=access_token,
            playlist_id=playlist["id"],
            track_uris=track_uris,
        )

        return {
            "playlist_id": playlist["id"],
            "playlist_url": playlist["external_urls"]["spotify"],
            "name": playlist["name"],
            "tracks_added": len(track_uris),
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to create playlist: {str(e)}")
