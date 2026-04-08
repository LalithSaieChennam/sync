"""End-to-end test: video in → scene analysis → music prompt → music → scored video out.

Usage:
    1. Set GOOGLE_AI_API_KEY in .env
    2. Place a test video at the path below (or change VIDEO_PATH)
    3. Run: python test_pipeline.py
"""

import json
import os
import sys

# --- CONFIG ---
VIDEO_PATH = "15271674_2160_3840_25fps.mp4"
OUTPUT_DIR = "output"
# ---------------

os.makedirs(OUTPUT_DIR, exist_ok=True)

# Add project root to path so imports work
sys.path.insert(0, os.path.dirname(__file__))

from backend.services.gemini import analyze_video
from backend.services.lyria import generate_music
from backend.services.ffmpeg import (
    get_video_duration,
    trim_audio,
    add_fades,
    apply_dialogue_ducking,
    mix_audio_video,
    export_music_only,
)


def compose_prompt(analysis: dict) -> str:
    """Convert Gemini scene analysis into a timestamp-formatted Lyria prompt.

    This is a simple bridge for Night 1. Day 2 replaces this with the
    full LangGraph Composer Agent.
    """
    duration = analysis["duration_seconds"]
    scenes = analysis["scenes"]
    has_dialogue = analysis.get("has_dialogue", False)
    genre = analysis.get("suggested_genre", "cinematic ambient")
    bpm_range = analysis.get("suggested_bpm_range", [80, 100])
    key = analysis.get("suggested_key", "C minor")
    mood = analysis.get("overall_mood", "reflective")

    # Header
    lines = [
        f"A {mood} {genre} track.",
        "Instrumental only." if has_dialogue else "",
        f"Tempo: {(bpm_range[0] + bpm_range[1]) // 2} BPM. Key of {key}.",
        "",
    ]

    # Timestamp sections from scenes
    for scene in scenes:
        start = scene["start_seconds"]
        minutes = int(start // 60)
        seconds = int(start % 60)
        timestamp = f"[{minutes:02d}:{seconds:02d}]"

        energy = scene.get("energy_level", "medium")
        scene_mood = scene.get("mood", "")
        visual = scene.get("visual_content", "")

        # Map energy to musical direction
        if energy == "low":
            arrangement = "Minimal and spacious. Soft textures, sparse instrumentation."
        elif energy == "high":
            arrangement = "Full arrangement, driving rhythm, strong energy."
        else:
            arrangement = "Moderate arrangement, balanced instrumentation."

        lines.append(f"{timestamp} {scene_mood.capitalize()}. {arrangement}")
        lines.append(f"  Visuals: {visual[:100]}")
        lines.append("")

    # Ending
    end_seconds = int(duration)
    end_min = end_seconds // 60
    end_sec = end_seconds % 60
    fade_start = max(0, end_seconds - 5)
    fade_min = fade_start // 60
    fade_sec = fade_start % 60
    lines.append(
        f"[{fade_min:02d}:{fade_sec:02d}] Begin fading out. "
        f"Fade to silence by [{end_min:02d}:{end_sec:02d}]."
    )

    return "\n".join(line for line in lines if line is not None)


def main():
    if not os.path.exists(VIDEO_PATH):
        print(f"ERROR: Video not found at '{VIDEO_PATH}'")
        print("Place a test video (15-120s, MP4) and update VIDEO_PATH.")
        sys.exit(1)

    print("=" * 60)
    print("SYNC — End-to-End Pipeline Test")
    print("=" * 60)

    # Step 1: Get video duration
    print("\n--- Step 1: Video Duration ---")
    duration = get_video_duration(VIDEO_PATH)

    if duration > 120:
        print(f"WARNING: Video is {duration:.0f}s (max 120s). Proceeding anyway.")

    # Step 2: Analyze video with Gemini
    print("\n--- Step 2: Scene Analysis (Gemini) ---")
    analysis = analyze_video(VIDEO_PATH)
    print(json.dumps(analysis, indent=2))

    # Save analysis for reference
    analysis_path = os.path.join(OUTPUT_DIR, "scene_analysis.json")
    with open(analysis_path, "w") as f:
        json.dump(analysis, f, indent=2)
    print(f"Scene analysis saved to {analysis_path}")

    # Step 3: Compose Lyria prompt from analysis
    print("\n--- Step 3: Compose Music Prompt ---")
    prompt = compose_prompt(analysis)
    print(prompt)

    # Save prompt for reference
    prompt_path = os.path.join(OUTPUT_DIR, "lyria_prompt.txt")
    with open(prompt_path, "w") as f:
        f.write(prompt)
    print(f"Prompt saved to {prompt_path}")

    # Step 4: Generate music with Lyria 3 Pro
    print("\n--- Step 4: Generate Music (Lyria 3 Pro) ---")
    raw_music_path = os.path.join(OUTPUT_DIR, "raw_music.mp3")
    generate_music(prompt, raw_music_path)

    # Step 5: Post-process audio
    print("\n--- Step 5: Audio Post-Processing (FFmpeg) ---")

    # Trim to video duration
    trimmed_path = os.path.join(OUTPUT_DIR, "trimmed_music.mp3")
    trim_audio(raw_music_path, duration, trimmed_path)

    # Apply dialogue ducking if needed
    ducked_path = os.path.join(OUTPUT_DIR, "ducked_music.mp3")
    dialogue_segments = analysis.get("dialogue_segments", [])
    apply_dialogue_ducking(trimmed_path, dialogue_segments, ducked_path)

    # Add fades
    faded_path = os.path.join(OUTPUT_DIR, "faded_music.mp3")
    add_fades(ducked_path, faded_path)

    # Step 6: Mix audio + video
    print("\n--- Step 6: Final Mix ---")
    scored_path = os.path.join(OUTPUT_DIR, "scored_video.mp4")
    has_dialogue = analysis.get("has_dialogue", False)
    has_existing_music = analysis.get("has_existing_music", False)
    mix_audio_video(VIDEO_PATH, faded_path, scored_path,
                    has_dialogue=has_dialogue,
                    has_existing_music=has_existing_music)

    # Export music-only file
    music_only_path = os.path.join(OUTPUT_DIR, "score_only.mp3")
    export_music_only(faded_path, music_only_path)

    # Done
    print("\n" + "=" * 60)
    print("PIPELINE COMPLETE")
    print("=" * 60)
    print(f"  Scored video : {scored_path}")
    print(f"  Music only   : {music_only_path}")
    print(f"  Scene analysis: {analysis_path}")
    print(f"  Lyria prompt  : {prompt_path}")


if __name__ == "__main__":
    main()
