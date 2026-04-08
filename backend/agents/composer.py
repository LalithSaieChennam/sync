"""Composer agent node — converts scene analysis into a Lyria 3 Pro prompt.

Applies the official Lyria prompting framework:
  [Genre/Style] + [Mood] + [Instrumentation] + [Tempo/Rhythm] + [Vocal Style]

Uses timestamp prompting [MM:SS] to sync music transitions to scene boundaries.
"""

import json

from google import genai
from google.genai import types

from backend.config import GOOGLE_AI_API_KEY

client = genai.Client(api_key=GOOGLE_AI_API_KEY)

COMPOSER_SYSTEM_PROMPT = """
You are an expert film score composer. Given a scene analysis of a short-form video,
compose a detailed music generation prompt for Lyria 3 Pro.

RULES:
1. Use the Lyria Prompting Framework:
   [Genre/Style] + [Mood] + [Instrumentation] + [Tempo/Rhythm] + [Vocal Style]

2. Use timestamp prompting [MM:SS] to map each scene boundary to a music transition.
   This creates frame-perfect sync between visuals and music.

3. Be extremely descriptive with instruments:
   - "warm nylon-string acoustic guitar" not just "guitar"
   - "muted boom-bap drum pattern with brushed snare" not just "drums"
   - "breathy soprano vocals" not just "vocals"

4. Reference genres AND eras: "90s boom-bap hip-hop", "early 2000s R&B"

5. If dialogue is detected, the track MUST be instrumental only.
   Keep arrangement sparse during dialogue segments.

6. Platform-specific adjustments:
   - tiktok: Strong hook in first 2 seconds, bass-heavy, 90-140 BPM, trendy sub-genres
   - reels: Clean production, melodic hooks, 80-120 BPM, pop/electronic adjacent
   - shorts: Cinematic quality, dynamic range, clean builds, wide tempo range
   - general: Balanced, professional, moderate tempo 90-110 BPM

7. Always specify BPM and musical key.

8. End with a fade-out instruction: strip back arrangement in the final 5 seconds.

9. Keep the prompt under 2000 characters — Lyria works best with focused prompts.

10. NEVER reference real artist names, band names, or song titles in the prompt.
    Lyria will reject prompts that try to mimic specific artists.
    Instead of "sounds like Anirudh" say "modern Tamil film score with punchy electronic beats".
    Instead of "like Hans Zimmer" say "epic orchestral with deep brass and intense percussion".
    Describe the SOUND, not the artist.

Return ONLY the Lyria prompt text. No JSON. No explanation. Just the prompt.
"""


def _format_timestamp(seconds: float) -> str:
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"[{minutes:02d}:{secs:02d}]"


def compose_prompt(state: dict) -> dict:
    """LangGraph node: compose a Lyria prompt from scene analysis + user preferences."""
    import time

    analysis = state["scene_analysis"]
    vibe = state.get("vibe", "")
    platform = state.get("platform", "general")
    vocals = state.get("vocals", False)
    duration = analysis.get("duration_seconds", 60)

    user_context = f"""
VIDEO DURATION: {duration} seconds
PLATFORM: {platform}
USER VIBE REQUEST: {vibe if vibe else "None -- fully automatic, use your best judgment"}
VOCALS: {"Yes, include vocals" if vocals else "Instrumental only"}

SCENE ANALYSIS:
{json.dumps(analysis, indent=2)}

Compose the Lyria 3 Pro prompt now. Use [MM:SS] timestamps aligned to scene boundaries.
The music must be exactly {duration} seconds long.
"""

    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model="gemini-3-flash-preview",
                contents=user_context,
                config=types.GenerateContentConfig(
                    system_instruction=COMPOSER_SYSTEM_PROMPT,
                ),
            )
            break
        except Exception as e:
            if attempt < 2:
                wait = 15 * (attempt + 1)
                print(f"[composer] Error: {e}. Retrying in {wait}s...")
                time.sleep(wait)
            else:
                raise

    lyria_prompt = response.text.strip()

    # Enforce max length — Lyria works best under 2000 chars
    if len(lyria_prompt) > 2000:
        print(f"[composer] Prompt too long ({len(lyria_prompt)} chars), truncating to 2000")
        # Cut at last complete sentence/line before 2000 chars
        truncated = lyria_prompt[:2000]
        last_newline = truncated.rfind("\n")
        if last_newline > 1500:
            lyria_prompt = truncated[:last_newline]
        else:
            lyria_prompt = truncated

    # Safety: if composer returned empty or garbage
    if len(lyria_prompt) < 20:
        # Fallback: generate a basic prompt from analysis
        genre = analysis.get("suggested_genre", "cinematic ambient")
        mood = analysis.get("overall_mood", "reflective")
        bpm = analysis.get("suggested_bpm_range", [80, 100])
        key = analysis.get("suggested_key", "C minor")
        lyria_prompt = (
            f"A {mood} {genre} instrumental track. "
            f"Tempo: {(bpm[0] + bpm[1]) // 2} BPM. Key of {key}. "
            f"Duration: {duration} seconds. Fade out in the final 5 seconds."
        )
        print(f"[composer] Fallback prompt generated ({len(lyria_prompt)} chars)")

    print(f"[composer] Generated Lyria prompt ({len(lyria_prompt)} chars)")

    return {
        "lyria_prompt": lyria_prompt,
        "stage": "composing",
        "progress": 50,
        "message": "Soundtrack prompt composed",
    }
