"""Gemini 3 Flash video analysis wrapper.

Uploads a video file to Gemini and returns structured scene analysis JSON
for use by the music composition step.
"""

import json
import time

from google import genai
from google.genai import types

from backend.config import GOOGLE_AI_API_KEY

client = genai.Client(api_key=GOOGLE_AI_API_KEY)

SCENE_ANALYSIS_PROMPT = """
You are a film scoring assistant. Watch this video carefully
and analyze it for a music composer who needs to write a
perfectly synced soundtrack.

Return a JSON response with this exact structure:

{
  "duration_seconds": <number>,
  "has_dialogue": <boolean>,
  "dialogue_segments": [
    {"start": <float>, "end": <float>, "text": "<transcript snippet>"}
  ],
  "has_existing_music": <boolean>,
  "scenes": [
    {
      "start_seconds": <float>,
      "end_seconds": <float>,
      "visual_content": "<description of what's happening visually>",
      "mood": "<emotional tone>",
      "energy_level": "<low|medium|high>",
      "pacing": "<description of editing pace and shot length>",
      "camera_movement": "<static|tracking|handheld|etc>",
      "dominant_colors": "<color palette description>"
    }
  ],
  "overall_mood": "<one-line summary>",
  "overall_energy_arc": "<e.g. low -> medium -> low>",
  "suggested_genre": "<music genre suggestion>",
  "suggested_bpm_range": [<min>, <max>],
  "suggested_key": "<musical key suggestion>"
}

Be precise with timestamps. Identify every distinct scene change.
If there is dialogue or speech, transcribe it in dialogue_segments.
If there is existing background music, set has_existing_music to true.
""".strip()

# Required fields in the response
REQUIRED_FIELDS = ["duration_seconds", "scenes"]


def _validate_analysis(analysis: dict) -> dict:
    """Validate and sanitize the scene analysis response."""
    for field in REQUIRED_FIELDS:
        if field not in analysis:
            raise ValueError(f"Gemini response missing required field: {field}")

    # Ensure scenes is a list
    if not isinstance(analysis.get("scenes"), list):
        raise ValueError("Gemini response 'scenes' is not a list")

    # Ensure defaults for optional fields
    analysis.setdefault("has_dialogue", False)
    analysis.setdefault("dialogue_segments", [])
    analysis.setdefault("has_existing_music", False)
    analysis.setdefault("overall_mood", "")
    analysis.setdefault("overall_energy_arc", "")
    analysis.setdefault("suggested_genre", "cinematic ambient")
    analysis.setdefault("suggested_bpm_range", [80, 100])
    analysis.setdefault("suggested_key", "C minor")

    # Validate each scene has start/end times
    for i, scene in enumerate(analysis["scenes"]):
        if "start_seconds" not in scene or "end_seconds" not in scene:
            raise ValueError(f"Scene {i} missing start_seconds or end_seconds")

    return analysis


def analyze_video(video_path: str) -> dict:
    """Upload a video to Gemini and get structured scene analysis.

    Args:
        video_path: Path to the video file (MP4, MOV, WebM).

    Returns:
        Parsed dict matching the scene analysis schema.
    """
    print(f"[gemini] Uploading video: {video_path}")
    uploaded_file = client.files.upload(file=video_path)

    # Poll until the video is fully processed (timeout after 5 minutes)
    max_wait = 300  # 5 minutes
    waited = 0
    while not uploaded_file.state or uploaded_file.state.name != "ACTIVE":
        if uploaded_file.state and uploaded_file.state.name == "FAILED":
            raise RuntimeError("Gemini failed to process the video file.")
        if waited >= max_wait:
            raise RuntimeError(f"Gemini video processing timed out after {max_wait}s.")
        print(f"[gemini] Processing video... ({waited}s)")
        time.sleep(5)
        waited += 5
        uploaded_file = client.files.get(name=uploaded_file.name)

    print("[gemini] Video processed. Running scene analysis...")

    response = client.models.generate_content(
        model="gemini-3-flash-preview",
        contents=[uploaded_file, SCENE_ANALYSIS_PROMPT],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
        ),
    )

    # Parse and validate
    try:
        analysis = json.loads(response.text)
    except (json.JSONDecodeError, TypeError) as e:
        raise RuntimeError(f"Gemini returned invalid JSON: {e}")

    # Handle list-wrapped response
    if isinstance(analysis, list):
        if len(analysis) == 0:
            raise RuntimeError("Gemini returned empty list")
        analysis = analysis[0]

    if not isinstance(analysis, dict):
        raise RuntimeError(f"Gemini returned unexpected type: {type(analysis)}")

    analysis = _validate_analysis(analysis)
    print(f"[gemini] Analysis complete: {len(analysis['scenes'])} scenes detected")
    return analysis
