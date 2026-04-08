"""Audio Director agent node — generates music and assembles final video."""

import os
import time

from backend.services.lyria import generate_music, ContentFilterError
from backend.services.ffmpeg import (
    get_video_duration,
    has_video_stream,
    match_duration,
    add_fades,
    apply_dialogue_ducking,
    mix_audio_video,
    export_music_only,
)


def _strip_artist_references(prompt: str) -> str:
    """Remove lines that likely contain artist/song references that trigger Lyria's filter.

    Keeps the musical description (genre, tempo, instruments, timestamps)
    but strips anything that looks like 'in the style of X' or names real artists.
    """
    import re
    cleaned_lines = []
    for line in prompt.split("\n"):
        # Skip lines with common artist-reference patterns
        lower = line.lower()
        if any(phrase in lower for phrase in [
            "style of", "inspired by", "similar to", "like the work of",
            "reminiscent of", "in the vein of", "made by", "composed by",
            "sounds like", "reference:", "artist:",
        ]):
            continue
        cleaned_lines.append(line)

    result = "\n".join(cleaned_lines).strip()
    # If we stripped too much, return a basic version
    if len(result) < 50:
        # Extract just timestamps and basic info
        timestamps = re.findall(r'\[\d{2}:\d{2}\].*', prompt)
        if timestamps:
            result = "An instrumental cinematic track.\n\n" + "\n".join(timestamps)
        else:
            result = "An instrumental cinematic ambient track. Tempo: 90 BPM. Key of C minor."

    print(f"[audio_director] Stripped artist references, prompt now {len(result)} chars")
    return result


def generate_and_assemble(state: dict) -> dict:
    """LangGraph node: generate music with Lyria, post-process, and merge with video."""
    video_path = state["video_path"]
    lyria_prompt = state["lyria_prompt"]
    analysis = state["scene_analysis"]
    job_id = state.get("job_id", "default")

    output_dir = os.path.join("output", job_id)
    os.makedirs(output_dir, exist_ok=True)

    # Validate video has a video stream (reject audio-only files)
    if not has_video_stream(video_path):
        raise RuntimeError("File has no video stream. Upload a video file, not audio.")

    # Save the prompt for reference
    with open(os.path.join(output_dir, "lyria_prompt.txt"), "w") as f:
        f.write(lyria_prompt)

    # Step 1: Generate music with retries
    print(f"[audio_director] Generating music for job {job_id}...")
    raw_music = os.path.join(output_dir, "raw_music.mp3")

    last_error = None
    for attempt in range(3):
        try:
            prompt_to_use = lyria_prompt if attempt < 2 else lyria_prompt[:800]
            generate_music(prompt_to_use, raw_music)
            last_error = None
            break
        except ContentFilterError as e:
            # Lyria blocked the prompt (likely artist name reference)
            # Strip the vibe/artist reference and retry with just the scene-based prompt
            print(f"[audio_director] Content filtered: {e}. Retrying with generic prompt...")
            generic_prompt = _strip_artist_references(lyria_prompt)
            try:
                generate_music(generic_prompt, raw_music)
                last_error = None
                break
            except Exception as e2:
                last_error = e2
                if attempt < 2:
                    time.sleep(15)
        except Exception as e:
            last_error = e
            if attempt < 2:
                wait = 15 * (attempt + 1)
                print(f"[audio_director] Lyria error: {e}. Retrying in {wait}s... (attempt {attempt + 1}/3)")
                time.sleep(wait)

    if last_error:
        raise last_error

    # Step 2: Post-process
    # Always use FFprobe duration (ground truth), not Gemini's estimate
    duration = get_video_duration(video_path)
    has_dialogue = analysis.get("has_dialogue", False)

    # Match music duration to video (handles short/long/exact)
    matched = os.path.join(output_dir, "matched.mp3")
    match_duration(raw_music, duration, matched)

    # When dialogue is present: skip ducking entirely.
    # The music will be mixed at a consistent low volume (0.15) in mix_audio_video.
    # No volume spikes, no jumps — just a steady bed under the voice.
    #
    # When no dialogue: apply fades normally for a polished sound.
    if has_dialogue:
        faded = matched  # pass through unchanged
        print("[audio_director] Dialogue present: skipping ducking/fades for consistent music level")
    else:
        faded = os.path.join(output_dir, "faded.mp3")
        add_fades(matched, faded, has_dialogue=False)

    # Step 3: Mix and export
    scored_video = os.path.join(output_dir, "scored_video.mp4")
    mix_audio_video(
        video_path, faded, scored_video,
        has_dialogue=has_dialogue,
        has_existing_music=analysis.get("has_existing_music", False),
        job_dir=output_dir,
    )

    music_only = os.path.join(output_dir, "score_only.mp3")
    export_music_only(faded, music_only)

    return {
        "scored_video_path": scored_video,
        "music_only_path": music_only,
        "stage": "complete",
        "progress": 100,
        "message": "Scoring complete",
    }
