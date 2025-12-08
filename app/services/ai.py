import json
from anthropic import Anthropic

from app.config import get_settings
from app.models.schemas import LessonPlan, Segment

SYSTEM_PROMPT = """You are an expert cycle/spin class instructor helping to create lesson plans.

When given a theme and duration, create a structured workout plan with varied segments including:
- Warm-up (always start with this, 3-5 minutes, LOW intensity)
- Seated flats (moderate effort, recovery)
- Standing climbs (high resistance, slow cadence)
- Seated climbs (moderate-high resistance)
- Sprints/jumps (high cadence, lower resistance)
- Tabata intervals (20 sec on / 10 sec off patterns)
- Cool-down (always end with this, 3-5 minutes, LOW intensity)

INTENSITY PROGRESSION IS KEY:
- Start LOW (warm-up)
- Build to MEDIUM
- Peak at HIGH intensity segments
- Recovery periods (MEDIUM or LOW)
- End LOW (cool-down)

SONG SELECTION - PRIORITIZE INTENSITY OVER THEME:
- Songs MUST match the required INTENSITY and ENERGY level for the segment
- LOW intensity = calm, slower songs (< 100 BPM, low energy)
- MEDIUM intensity = moderate energy songs (100-130 BPM)
- HIGH intensity = high energy, driving songs (> 130 BPM, high energy)
- The theme influences the vibe/era/genre, but NEVER pick a calm song for a high intensity segment
- Example: For a "Disney" theme high-intensity sprint, pick an energetic Disney song, NOT a ballad

For each segment, provide:
- A descriptive name
- Duration in seconds
- Intensity level (low, medium, high) - this determines the song energy
- Position (seated or standing)
- Coaching cues and motivational instructions
- Suggested BPM range for music selection
- A song suggestion that MATCHES THE INTENSITY (format: "Song Name - Artist")

IMPORTANT: Respond ONLY with valid JSON matching this exact structure:
{
  "theme": "string",
  "total_duration_minutes": number,
  "segments": [
    {
      "name": "string",
      "duration_seconds": number,
      "intensity": "low|medium|high",
      "position": "seated|standing",
      "description": "string",
      "suggested_bpm_range": "string",
      "song": "string"
    }
  ],
  "notes": "string or null"
}"""


async def generate_lesson_plan(theme: str, duration_minutes: int) -> LessonPlan:
    """Generate a cycle class lesson plan using Claude."""
    settings = get_settings()
    client = Anthropic(api_key=settings.anthropic_api_key)

    user_prompt = f"""Create a {duration_minutes}-minute cycle class lesson plan with the theme: "{theme}"

Remember to:
- Start with a warm-up
- Build intensity gradually
- Include variety (seated, standing, climbs, sprints)
- End with a cool-down
- Make the theme influence the coaching cues and energy

Respond with ONLY the JSON, no additional text."""

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        messages=[
            {"role": "user", "content": user_prompt}
        ],
        system=SYSTEM_PROMPT,
    )

    # Extract the text content
    response_text = message.content[0].text

    # Parse JSON response
    try:
        plan_data = json.loads(response_text)
    except json.JSONDecodeError:
        # Try to extract JSON from the response if it's wrapped in markdown
        import re
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response_text)
        if json_match:
            plan_data = json.loads(json_match.group(1))
        else:
            raise ValueError(f"Failed to parse AI response as JSON: {response_text[:200]}")

    # Validate and create the LessonPlan
    return LessonPlan(**plan_data)
