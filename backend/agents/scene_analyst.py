"""Scene Analyst agent node — wraps Gemini video analysis with retry."""

import time
from backend.services.gemini import analyze_video


def analyze_scene(state: dict) -> dict:
    """LangGraph node: analyze video with Gemini and return scene data."""
    video_path = state["video_path"]
    print(f"[scene_analyst] Analyzing: {video_path}")

    # Retry up to 3 times on 503/transient errors
    last_error = None
    for attempt in range(3):
        try:
            analysis = analyze_video(video_path)
            return {
                "scene_analysis": analysis,
                "stage": "analyzing",
                "progress": 25,
                "message": "Scene analysis complete",
            }
        except Exception as e:
            last_error = e
            if attempt < 2:
                wait = 15 * (attempt + 1)
                print(f"[scene_analyst] Error: {e}. Retrying in {wait}s... (attempt {attempt + 1}/3)")
                time.sleep(wait)
            else:
                raise last_error
