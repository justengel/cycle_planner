import uuid
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, Field

from app.models.schemas import GenerateRequest, GenerateResponse, LessonPlan
from app.services.ai import generate_lesson_plan
from app.services.supabase import get_supabase_client, SupabaseClient
from app.services.spotify import search_tracks, get_audio_features
from app.services.playlist_to_plan import playlist_to_plan
from app.services.rate_limiter import check_rate_limit, record_request, get_remaining_requests
from app.dependencies import get_current_user_id

router = APIRouter()


class GenerateResponseWithId(GenerateResponse):
    """Response with plan and saved ID."""
    id: str | None = None


def energy_to_intensity(energy: float) -> str:
    """Convert Spotify energy (0-1) to intensity level."""
    if energy < 0.4:
        return "low"
    elif energy < 0.7:
        return "medium"
    else:
        return "high"


def tempo_to_bpm_range(tempo: float) -> str:
    """Convert Spotify tempo to a BPM range string."""
    # Round to nearest 5 and create a range
    base = round(tempo / 5) * 5
    return f"{base - 5}-{base + 5}"


async def auto_link_spotify_uris(plan: LessonPlan, spotify_token: str | None) -> LessonPlan:
    """Search Spotify for AI-suggested songs and add URIs, durations, and audio features."""
    if not spotify_token:
        return plan

    total_duration_seconds = 0

    for segment in plan.segments:
        if segment.song and not segment.spotify_uri:
            try:
                # Search Spotify for the song
                results = await search_tracks(segment.song, spotify_token, limit=1)
                tracks = results.get("tracks", {}).get("items", [])
                if tracks:
                    track = tracks[0]
                    track_id = track["id"]
                    segment.spotify_uri = track["uri"]

                    # Update song name with actual track info for accuracy
                    artist = track["artists"][0]["name"] if track["artists"] else ""
                    segment.song = f"{track['name']} - {artist}"

                    # Update segment duration to match actual song duration
                    if track.get("duration_ms"):
                        segment.duration_seconds = track["duration_ms"] // 1000

                    # Get audio features to set intensity and BPM based on actual song
                    audio_features = await get_audio_features(track_id, spotify_token)
                    if audio_features:
                        # Set intensity based on energy level
                        if audio_features.get("energy") is not None:
                            segment.intensity = energy_to_intensity(audio_features["energy"])

                        # Set BPM range based on actual tempo
                        if audio_features.get("tempo"):
                            segment.suggested_bpm_range = tempo_to_bpm_range(audio_features["tempo"])

            except Exception as e:
                # Log but don't fail - song will just not have URI
                print(f"Warning: Failed to search Spotify for '{segment.song}': {e}")

        total_duration_seconds += segment.duration_seconds

    # Update total plan duration
    plan.total_duration_minutes = (total_duration_seconds + 59) // 60  # Round up

    return plan


@router.post("/generate", response_model=GenerateResponseWithId)
async def generate(
    request: GenerateRequest,
    http_request: Request,
    user_id: str = Depends(get_current_user_id),
    client: SupabaseClient = Depends(get_supabase_client),
):
    """Generate a cycle class lesson plan using AI and save it."""
    # Check rate limit before doing any work
    check_rate_limit(user_id)

    try:
        plan = await generate_lesson_plan(
            theme=request.theme,
            duration_minutes=request.duration_minutes,
        )

        # Calculate total duration from segments
        total_seconds = sum(seg.duration_seconds for seg in plan.segments)
        plan.total_duration_minutes = (total_seconds + 59) // 60  # Round up

        # Record successful generation for rate limiting
        record_request(user_id)

        # Auto-link Spotify URIs if user is connected to Spotify
        spotify_token = http_request.cookies.get("spotify_access_token")
        plan = await auto_link_spotify_uris(plan, spotify_token)

        # Auto-save the generated plan
        plan_id = None
        try:
            plan_id = str(uuid.uuid4())
            data = {
                "id": plan_id,
                "user_id": user_id,
                "theme": plan.theme,
                "duration_minutes": plan.total_duration_minutes,
                "plan_json": plan.model_dump(),
            }
            client.table("lesson_plans").insert(data).execute()
        except Exception as save_error:
            # Log but don't fail if save fails
            print(f"Warning: Failed to auto-save plan: {save_error}")
            plan_id = None

        return GenerateResponseWithId(plan=plan, id=plan_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")


@router.get("/rate-limit")
async def get_rate_limit_status(
    user_id: str = Depends(get_current_user_id),
):
    """Get current rate limit status for the user."""
    return get_remaining_requests(user_id)


class FromPlaylistRequest(BaseModel):
    playlist_id: str = Field(..., min_length=1, max_length=100)
    playlist_name: str = Field(..., min_length=1, max_length=200)


@router.post("/from-playlist", response_model=GenerateResponseWithId)
async def generate_from_playlist(
    request: Request,
    body: FromPlaylistRequest,
    user_id: str = Depends(get_current_user_id),
    client: SupabaseClient = Depends(get_supabase_client),
):
    """Create a lesson plan from a Spotify playlist."""
    spotify_token = request.cookies.get("spotify_access_token")

    if not spotify_token:
        raise HTTPException(status_code=401, detail="Not connected to Spotify")

    try:
        # Convert playlist to plan
        plan = await playlist_to_plan(
            access_token=spotify_token,
            playlist_id=body.playlist_id,
            playlist_name=body.playlist_name,
        )

        # Auto-save the plan
        plan_id = str(uuid.uuid4())
        data = {
            "id": plan_id,
            "user_id": user_id,
            "theme": plan.theme,
            "duration_minutes": plan.total_duration_minutes,
            "plan_json": plan.model_dump(),
        }
        client.table("lesson_plans").insert(data).execute()

        return GenerateResponseWithId(plan=plan, id=plan_id)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create plan from playlist: {str(e)}")
