from pydantic import BaseModel, Field
from datetime import datetime


class SubSegment(BaseModel):
    """A sub-segment within a song segment for activity changes during continuous playback."""
    name: str = Field(..., description="Activity name (e.g., 'Standing Sprint', 'Seated Recovery')")
    duration_seconds: int = Field(..., ge=5, description="Duration in seconds (minimum 5)")
    intensity: str = Field(..., description="Intensity level: low, medium, or high")
    position: str = Field(..., description="Position: seated or standing")
    description: str = Field(..., description="Coaching cues and instructions")
    suggested_bpm_range: str = Field(default="", description="Suggested music BPM range (e.g., '90-100')")


class Segment(BaseModel):
    """A single segment/exercise in the lesson plan."""
    name: str = Field(..., description="Exercise name (e.g., 'Warm-up', 'Standing Climb')")
    duration_seconds: int = Field(..., description="Duration in seconds")
    intensity: str = Field(..., description="Intensity level: low, medium, or high")
    position: str = Field(..., description="Position: seated or standing")
    description: str = Field(..., description="Coaching cues and instructions")
    suggested_bpm_range: str = Field(..., description="Suggested music BPM range (e.g., '90-100')")
    song: str | None = Field(default=None, description="Song name and artist")
    spotify_uri: str | None = Field(default=None, description="Spotify track URI")
    song_start_seconds: int = Field(default=0, description="Start song at this second")
    song_end_seconds: int | None = Field(default=None, description="Stop song at this second")
    fade_out: bool = Field(default=False, description="Fade out song at end")
    sub_segments: list[SubSegment] | None = Field(default=None, description="Optional sub-segments for activity changes within this segment")


class LessonPlan(BaseModel):
    """Complete lesson plan structure."""
    theme: str
    total_duration_minutes: int = 0  # Calculated from segments, not provided by AI
    segments: list[Segment]
    notes: str | None = None


class GenerateRequest(BaseModel):
    """Request to generate a new lesson plan."""
    theme: str = Field(..., description="Theme or description for the class")
    duration_minutes: int = Field(default=50, ge=15, le=120, description="Class duration in minutes")


class GenerateResponse(BaseModel):
    """Response containing the generated lesson plan."""
    plan: LessonPlan


class SavedPlan(BaseModel):
    """A saved lesson plan with metadata."""
    id: str
    user_id: str
    theme: str
    duration_minutes: int
    plan: LessonPlan
    created_at: datetime
    updated_at: datetime | None = None


class SavePlanRequest(BaseModel):
    """Request to save a lesson plan."""
    plan: LessonPlan


class UserInfo(BaseModel):
    """Basic user information."""
    id: str
    email: str
