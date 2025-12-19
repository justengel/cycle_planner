"""Service to convert a Spotify playlist into a LessonPlan."""

from app.models.schemas import LessonPlan, Segment
from app.services.spotify import get_playlist_tracks, get_audio_features_batch


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
    base = round(tempo / 5) * 5
    return f"{base - 5}-{base + 5}"


def get_segment_type(index: int, total: int, intensity: str) -> tuple[str, str, str]:
    """
    Determine segment type, position, and description based on position and intensity.

    Returns: (name, position, description)
    """
    # First track is always warm-up
    if index == 0:
        return (
            "Warm-Up",
            "seated",
            "Light resistance, easy pace. Focus on warming up the legs and finding your rhythm."
        )

    # Last track is always cool-down
    if index == total - 1:
        return (
            "Cool-Down",
            "seated",
            "Low resistance, slow pace. Focus on deep breathing and bringing heart rate down."
        )

    # Middle tracks based on intensity
    if intensity == "high":
        segment_types = [
            ("Seated Sprint", "seated", "High cadence, moderate resistance. Push for speed while staying controlled."),
            ("Standing Climb", "standing", "Heavy resistance, slow powerful pushes. Drive through your legs."),
            ("Standing Sprint", "standing", "High cadence out of the saddle. Stay light on the pedals."),
            ("Attack", "standing", "Maximum effort! Give it everything you've got."),
        ]
    elif intensity == "medium":
        segment_types = [
            ("Endurance", "seated", "Moderate resistance, steady cadence. Find a sustainable pace."),
            ("Rolling Hills", "seated", "Alternating resistance. Up and over the hills."),
            ("Seated Climb", "seated", "Building resistance, controlled cadence. Steady power output."),
            ("Intervals", "seated", "Work-rest cycles. Push during work, recover during rest."),
        ]
    else:  # low
        segment_types = [
            ("Recovery", "seated", "Light resistance, easy cadence. Active recovery."),
            ("Flat Road", "seated", "Moderate pace, low resistance. Keep the legs moving."),
            ("Easy Spin", "seated", "Minimal resistance, comfortable cadence. Just keep pedaling."),
        ]

    # Cycle through options based on index for variety
    choice = segment_types[index % len(segment_types)]
    return choice


async def playlist_to_plan(
    access_token: str,
    playlist_id: str,
    playlist_name: str,
) -> LessonPlan:
    """
    Convert a Spotify playlist into a LessonPlan.

    Args:
        access_token: Spotify access token
        playlist_id: Spotify playlist ID
        playlist_name: Name of the playlist (used as theme)

    Returns:
        LessonPlan with segments created from playlist tracks
    """
    # Fetch all tracks from the playlist
    tracks = await get_playlist_tracks(access_token, playlist_id)

    if not tracks:
        raise ValueError("Playlist is empty or contains no playable tracks")

    if len(tracks) < 3:
        raise ValueError("Playlist must contain at least 3 tracks for a valid workout plan")

    # Fetch audio features for all tracks in batch (much faster than individual calls)
    track_ids = [track["id"] for track in tracks]
    audio_features_map = await get_audio_features_batch(track_ids, access_token)

    segments = []
    total_tracks = len(tracks)
    total_duration_seconds = 0

    for i, track in enumerate(tracks):
        # Get audio features from batch results
        audio_features = audio_features_map.get(track["id"])

        # Determine intensity from energy
        energy = audio_features.get("energy", 0.5) if audio_features else 0.5
        tempo = audio_features.get("tempo", 100) if audio_features else 100

        # Force first and last track to low intensity
        if i == 0 or i == total_tracks - 1:
            intensity = "low"
        else:
            intensity = energy_to_intensity(energy)

        # Get segment type based on position and intensity
        name, position, description = get_segment_type(i, total_tracks, intensity)

        # Duration from track length with bounds checking
        duration_ms = track.get("duration_ms", 0)
        if duration_ms is None or duration_ms < 0:
            duration_ms = 0
        duration_seconds = min(duration_ms // 1000, 3600)  # Cap at 1 hour per track
        total_duration_seconds += duration_seconds

        segment = Segment(
            name=name,
            duration_seconds=duration_seconds,
            intensity=intensity,
            position=position,
            description=description,
            suggested_bpm_range=tempo_to_bpm_range(tempo),
            song=f"{track['name']} - {track['artist']}",
            spotify_uri=track["uri"],
            song_start_seconds=0,
            song_end_seconds=None,
            fade_out=False,
            sub_segments=None,
        )
        segments.append(segment)

    return LessonPlan(
        theme=playlist_name,
        total_duration_minutes=(total_duration_seconds + 59) // 60,
        segments=segments,
        notes=f"Created from Spotify playlist: {playlist_name}",
    )
