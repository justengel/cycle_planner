import json
import logging
from anthropic import Anthropic

from app.config import get_settings
from app.models.schemas import LessonPlan, Segment

logger = logging.getLogger(__name__)

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
- LOW intensity = calm, slower songs (low energy, suggest 60-80 RPM cadence)
- MEDIUM intensity = moderate energy songs (suggest 80-100 RPM cadence)
- HIGH intensity = high energy, driving songs (suggest 100-120+ RPM cadence)
- The theme influences the vibe/era/genre, but NEVER pick a calm song for a high intensity segment
- Example: For a "Disney" theme high-intensity sprint, pick an energetic Disney song, NOT a ballad

SEGMENT DURATION - MUST FIT WITHIN SONG LENGTH:
- Most pop/rock songs are 3-4 minutes (180-240 seconds)
- NEVER make a segment longer than the song can support
- If you need more time, use multiple segments with different songs
- Warm-up and cool-down can be 3-5 minutes (one song each)
- High-intensity segments work best at 2-4 minutes
- For longer activities, split into multiple segments with song changes

SUB-SEGMENTS - USE FOR VARIED ACTIVITIES WITHIN ONE SONG:
Sub-segments break a single song into multiple activities. Use them when:
- Tabata intervals: 20 sec sprint / 10 sec recovery cycles (use sub-segments for each interval)
- Position changes: seated → standing → seated transitions during one song
- Intensity waves: building and recovering within a song
- Jumps: alternating seated/standing every 8-16 counts

Do NOT use sub-segments for:
- Simple segments with one consistent activity (warm-up, cool-down, basic climbs)
- Segments shorter than 60 seconds

When using sub-segments:
- The segment's duration_seconds should equal the sum of all sub-segment durations
- Each sub-segment has its own name, duration, intensity, position, description, and RPM range
- The parent segment's intensity/position reflect the overall character

For each segment, provide:
- A descriptive name
- Duration in seconds
- Intensity level (low, medium, high) - this determines the song energy
- Position (seated or standing)
- Coaching cues and motivational instructions
- Suggested RPM range for pedaling cadence (e.g., "80-100 RPM")
- A song suggestion that MATCHES THE INTENSITY (format: "Song Name - Artist")
- Optional: sub_segments array for varied activities within the song

IMPORTANT: Respond ONLY with valid JSON matching this exact structure:
{
  "theme": "string",
  "segments": [
    {
      "name": "string",
      "duration_seconds": number,
      "intensity": "low|medium|high",
      "position": "seated|standing",
      "description": "string",
      "suggested_bpm_range": "string",
      "song": "string",
      "sub_segments": [
        {
          "name": "string",
          "duration_seconds": number,
          "intensity": "low|medium|high",
          "position": "seated|standing",
          "description": "string",
          "suggested_bpm_range": "string"
        }
      ] or null
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

    logger.info(f"Generating lesson plan: theme='{theme}', duration={duration_minutes}min")

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=8192,
        messages=[
            {"role": "user", "content": user_prompt}
        ],
        system=SYSTEM_PROMPT,
    )

    # Extract the text content
    response_text = message.content[0].text

    logger.info(f"AI response received: stop_reason={message.stop_reason}, "
                f"input_tokens={message.usage.input_tokens}, output_tokens={message.usage.output_tokens}")
    logger.debug(f"AI response text: {response_text[:500]}...")

    # Check if response was truncated
    if message.stop_reason == "max_tokens":
        logger.error(f"AI response truncated at {message.usage.output_tokens} tokens")
        raise ValueError("AI response was truncated. Try a shorter duration or simpler theme.")

    # Parse JSON response
    try:
        plan_data = json.loads(response_text)
        logger.info(f"Successfully parsed JSON response with {len(plan_data.get('segments', []))} segments")
    except json.JSONDecodeError as e:
        logger.warning(f"Direct JSON parse failed: {e}. Attempting markdown extraction.")
        # Try to extract JSON from the response if it's wrapped in markdown
        import re
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response_text)
        if json_match:
            try:
                plan_data = json.loads(json_match.group(1))
                logger.info(f"Successfully parsed JSON from markdown with {len(plan_data.get('segments', []))} segments")
            except json.JSONDecodeError as e2:
                logger.error(f"Markdown JSON parse failed: {e2}. Response: {response_text[:500]}")
                raise ValueError("AI response was incomplete or malformed. Please try again.")
        else:
            logger.error(f"No JSON found in response: {response_text[:500]}")
            raise ValueError(f"Failed to parse AI response as JSON: {response_text[:200]}")

    # Validate and create the LessonPlan
    return LessonPlan(**plan_data)
