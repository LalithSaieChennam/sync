"""FFmpeg wrapper for audio/video post-processing.

Handles: duration probing, trimming/looping, dialogue ducking,
audio/video mixing, fade in/out, sample rate normalization,
vocal extraction (via Demucs), and final export.
"""

import json
import os
import subprocess


def _run(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess:
    """Run an FFmpeg/FFprobe command. Logs stderr on failure."""
    print(f"[ffmpeg] {' '.join(cmd[:6])}...")
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if check and result.returncode != 0:
        stderr = result.stderr[:500] if result.stderr else "no stderr"
        raise RuntimeError(f"FFmpeg failed (exit {result.returncode}): {stderr}")
    return result


def get_audio_duration(audio_path: str) -> float:
    """Get audio file duration in seconds."""
    result = _run([
        "ffprobe", "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        audio_path,
    ])
    try:
        info = json.loads(result.stdout)
        return float(info["format"]["duration"])
    except (json.JSONDecodeError, KeyError, ValueError):
        return 0.0


def get_video_duration(video_path: str) -> float:
    """Get video duration in seconds using ffprobe."""
    result = _run([
        "ffprobe", "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        video_path,
    ])
    try:
        info = json.loads(result.stdout)
        duration_str = info.get("format", {}).get("duration")
        if not duration_str:
            raise ValueError("No duration field in ffprobe output")
        duration = float(duration_str)
    except (json.JSONDecodeError, ValueError, TypeError) as e:
        raise RuntimeError(f"Failed to read video duration: {e}")

    if duration <= 0:
        raise RuntimeError(f"Invalid video duration: {duration}s")

    print(f"[ffmpeg] Video duration: {duration:.2f}s")
    return duration


def has_video_stream(video_path: str) -> bool:
    """Check if file contains a video stream."""
    probe = _run([
        "ffprobe", "-v", "quiet",
        "-print_format", "json",
        "-show_streams",
        video_path,
    ])
    try:
        streams = json.loads(probe.stdout).get("streams", [])
    except json.JSONDecodeError:
        return False
    return any(s.get("codec_type") == "video" for s in streams)


def normalize_audio(audio_path: str, output_path: str, sample_rate: int = 48000) -> str:
    """Normalize audio to consistent sample rate and format.

    Lyria outputs 48kHz. Video audio can be anything. Normalize both
    to the same rate before mixing to avoid pitch/speed artifacts.
    """
    _run([
        "ffmpeg", "-y",
        "-i", audio_path,
        "-ar", str(sample_rate),
        "-ac", "2",  # stereo
        output_path,
    ])
    return output_path


def match_duration(audio_path: str, target_duration: float, output_path: str) -> str:
    """Make audio match target duration exactly.

    - If audio is longer: trim with fade-out
    - If audio is shorter by <3s: just pad with silence
    - If audio is much shorter: loop with crossfade then trim
    """
    audio_duration = get_audio_duration(audio_path)

    if audio_duration <= 0:
        raise RuntimeError(f"Cannot read audio duration from {audio_path}")

    diff = target_duration - audio_duration

    if abs(diff) < 0.5:
        # Close enough — just hard trim
        _run(["ffmpeg", "-y", "-i", audio_path, "-t", str(target_duration), output_path])
        print(f"[ffmpeg] Duration matched (within 0.5s) -> {output_path}")
        return output_path

    if diff < 0:
        # Audio is longer — trim with fade-out
        fade_duration = min(2.0, target_duration * 0.3)
        fade_start = max(0, target_duration - fade_duration)
        _run([
            "ffmpeg", "-y",
            "-i", audio_path,
            "-t", str(target_duration),
            "-af", f"afade=t=out:st={fade_start}:d={fade_duration}",
            output_path,
        ])
        print(f"[ffmpeg] Trimmed {audio_duration:.1f}s -> {target_duration:.1f}s")
        return output_path

    if diff <= 3.0:
        # Slightly short — pad with silence at the end
        _run([
            "ffmpeg", "-y",
            "-i", audio_path,
            "-af", f"apad=whole_dur={target_duration}",
            "-t", str(target_duration),
            output_path,
        ])
        print(f"[ffmpeg] Padded {audio_duration:.1f}s -> {target_duration:.1f}s (silence fill)")
        return output_path

    # Much shorter — loop the audio then trim
    loops_needed = int(target_duration / audio_duration) + 1
    _run([
        "ffmpeg", "-y",
        "-stream_loop", str(loops_needed),
        "-i", audio_path,
        "-t", str(target_duration),
        "-af", f"afade=t=out:st={max(0, target_duration - 2)}:d=2",
        output_path,
    ])
    print(f"[ffmpeg] Looped {audio_duration:.1f}s x{loops_needed} -> {target_duration:.1f}s")
    return output_path


def add_fades(audio_path: str, output_path: str,
              fade_in: float = 0.5, fade_out: float = 2.0,
              has_dialogue: bool = False) -> str:
    """Apply fade-in and fade-out to an audio file.

    If has_dialogue is True, skip fades entirely to avoid muffling
    speech that may be at the start or end of the video.
    """
    if has_dialogue:
        # Don't fade — speech might be at the boundaries
        _run(["ffmpeg", "-y", "-i", audio_path, "-c", "copy", output_path])
        print("[ffmpeg] Skipped fades (dialogue present)")
        return output_path

    duration = get_audio_duration(audio_path)
    if duration <= 0:
        _run(["ffmpeg", "-y", "-i", audio_path, "-c", "copy", output_path])
        return output_path

    # Clamp fades so they don't exceed total duration
    fade_in = min(fade_in, duration * 0.2)
    fade_out = min(fade_out, duration * 0.3)
    fade_out_start = max(0, duration - fade_out)

    _run([
        "ffmpeg", "-y",
        "-i", audio_path,
        "-af", (
            f"afade=t=in:st=0:d={fade_in},"
            f"afade=t=out:st={fade_out_start}:d={fade_out}"
        ),
        output_path,
    ])
    print(f"[ffmpeg] Added fades -> {output_path}")
    return output_path


def apply_dialogue_ducking(audio_path: str, dialogue_segments: list[dict],
                           output_path: str) -> str:
    """Reduce music volume during dialogue segments with smooth transitions."""
    if not dialogue_segments:
        _run(["ffmpeg", "-y", "-i", audio_path, "-c", "copy", output_path])
        return output_path

    audio_duration = get_audio_duration(audio_path)

    # Validate, filter, and clamp segments to audio duration
    valid_segments = []
    for seg in dialogue_segments:
        try:
            start = float(seg.get("start", -1))
            end = float(seg.get("end", -1))
        except (TypeError, ValueError):
            continue
        if start >= 0 and end > start:
            # Clamp to audio duration
            start = min(start, audio_duration)
            end = min(end, audio_duration)
            if end > start:
                valid_segments.append((start, end))

    if not valid_segments:
        _run(["ffmpeg", "-y", "-i", audio_path, "-c", "copy", output_path])
        return output_path

    # Merge overlapping segments (with 0.3s padding for smooth transitions)
    valid_segments.sort()
    merged = [valid_segments[0]]
    for start, end in valid_segments[1:]:
        prev_start, prev_end = merged[-1]
        # Merge if overlapping or within 0.5s of each other
        if start <= prev_end + 0.5:
            merged[-1] = (prev_start, max(prev_end, end))
        else:
            merged.append((start, end))

    # Build volume filter — duck to 15% during speech (was 20%)
    volume_filters = [
        f"volume=enable='between(t,{s},{e})':volume=0.15"
        for s, e in merged
    ]

    _run([
        "ffmpeg", "-y",
        "-i", audio_path,
        "-af", ",".join(volume_filters),
        output_path,
    ])
    print(f"[ffmpeg] Applied ducking for {len(merged)} dialogue segment(s) -> {output_path}")
    return output_path


def extract_vocals(video_path: str, output_dir: str) -> str:
    """Extract vocals from video audio using Demucs source separation.

    Splits audio into vocals + accompaniment, returns path to vocals track.
    Used when video has both speech AND existing music — we keep the speech,
    discard the old music, and replace it with our new Lyria score.
    """
    # Step 1: Extract audio from video
    extracted_audio = os.path.join(output_dir, "extracted_audio.wav")
    _run([
        "ffmpeg", "-y",
        "-i", video_path,
        "-vn",
        "-ar", "44100",
        "-ac", "2",
        extracted_audio,
    ])

    # Step 2: Run Demucs via Python API (bypasses torchaudio save bug with FFmpeg 8)
    print("[demucs] Separating vocals from music (this takes 30-60s)...")
    vocals_path = os.path.join(output_dir, "vocals.wav")

    try:
        import torch
        import soundfile as sf
        from demucs.pretrained import get_model
        from demucs.apply import apply_model
        from demucs.audio import AudioFile

        model = get_model("htdemucs")
        model.eval()

        # Load audio
        audio_file = AudioFile(extracted_audio)
        wav = audio_file.read(streams=0, samplerate=model.samplerate, channels=model.audio_channels)
        ref = wav.mean(0)
        wav -= ref.mean()
        wav /= ref.std() + 1e-8

        # Separate
        sources = apply_model(model, wav[None], device="cpu")[0]

        # Find vocals index
        vocals_idx = model.sources.index("vocals")
        vocals = sources[vocals_idx]

        # Undo normalization
        vocals = vocals * ref.std() + ref.mean()

        # Save with soundfile (no torchcodec dependency)
        vocals_np = vocals.cpu().numpy().T  # (channels, samples) -> (samples, channels)
        sf.write(vocals_path, vocals_np, model.samplerate)
        print(f"[demucs] Vocals extracted -> {vocals_path}")

    except Exception as e:
        print(f"[demucs] Warning: separation failed: {e}")
        print("[demucs] Falling back to original audio")
        return extracted_audio

    if not os.path.exists(vocals_path):
        print("[demucs] Falling back to original audio")
        return extracted_audio

    print(f"[demucs] Vocals extracted -> {vocals_path}")
    return vocals_path


def mix_audio_video(video_path: str, music_path: str, output_path: str,
                    has_dialogue: bool = False,
                    has_existing_music: bool = False,
                    job_dir: str = "") -> str:
    """Merge generated music with the original video.

    Priority order:
    1. Dialogue + existing music -> extract vocals via Demucs, mix with new music
    2. Dialogue only             -> keep original at full volume, music quiet underneath
    3. No audio stream           -> 100% new music
    4. Existing music, no speech -> replace original audio with new music
    5. Ambient sounds            -> original 30% + music 70%
    """
    # Check if original video has an audio stream
    probe = _run([
        "ffprobe", "-v", "quiet",
        "-print_format", "json",
        "-show_streams",
        video_path,
    ])
    try:
        streams = json.loads(probe.stdout).get("streams", [])
    except json.JSONDecodeError:
        streams = []

    has_audio = any(
        s.get("codec_type") == "audio"
        for s in streams
    )

    if has_dialogue and has_existing_music and has_audio:
        # SPEECH + MUSIC MODE: Extract vocals, discard old music, add new score
        print("[ffmpeg] Mix mode: speech+music -> extracting vocals, replacing music")
        sep_dir = job_dir or os.path.dirname(output_path)
        vocals_path = extract_vocals(video_path, sep_dir)

        # Mix: extracted vocals at full volume + new music underneath
        _run([
            "ffmpeg", "-y",
            "-i", video_path,
            "-i", vocals_path,
            "-i", music_path,
            "-filter_complex",
            (
                "[1:a]aresample=48000[voice];"
                "[2:a]aresample=48000,volume=0.18[music];"
                "[voice][music]amix=inputs=2:duration=longest:normalize=0[out]"
            ),
            "-map", "0:v",
            "-map", "[out]",
            "-c:v", "copy",
            "-c:a", "aac", "-b:a", "192k",
            "-shortest",
            output_path,
        ])
    elif has_dialogue and has_audio:
        # DIALOGUE ONLY MODE: speech is sacred.
        # Music plays at a consistent low volume the entire time.
        print("[ffmpeg] Mix mode: dialogue -> original 1.0 + music 0.15 (consistent level)")
        _run([
            "ffmpeg", "-y",
            "-i", video_path,
            "-i", music_path,
            "-filter_complex",
            (
                "[0:a]aresample=48000[voice];"
                "[1:a]aresample=48000,volume=0.15[music];"
                "[voice][music]amix=inputs=2:duration=first:normalize=0[out]"
            ),
            "-map", "0:v",
            "-map", "[out]",
            "-c:v", "copy",
            "-c:a", "aac", "-b:a", "192k",
            output_path,
        ])
    elif not has_audio or (has_existing_music and not has_dialogue):
        # NO AUDIO or EXISTING MUSIC (no dialogue): replace entirely
        mode = "replace (existing music)" if has_existing_music else "no original audio"
        print(f"[ffmpeg] Mix mode: {mode} -> 100% new music")
        _run([
            "ffmpeg", "-y",
            "-i", video_path,
            "-i", music_path,
            "-map", "0:v",
            "-map", "1:a",
            "-c:v", "copy",
            "-c:a", "aac", "-b:a", "192k",
            "-shortest",
            output_path,
        ])
    else:
        # AMBIENT MODE: natural sounds, no speech — music leads
        print("[ffmpeg] Mix mode: ambient -> original 0.3 + music 0.7")
        _run([
            "ffmpeg", "-y",
            "-i", video_path,
            "-i", music_path,
            "-filter_complex",
            (
                "[0:a]aresample=48000,volume=0.3[voice];"
                "[1:a]aresample=48000,volume=0.7[music];"
                "[voice][music]amix=inputs=2:duration=first:normalize=0[out]"
            ),
            "-map", "0:v",
            "-map", "[out]",
            "-c:v", "copy",
            "-c:a", "aac", "-b:a", "192k",
            output_path,
        ])

    print(f"[ffmpeg] Scored video saved -> {output_path}")
    return output_path


def export_music_only(audio_path: str, output_path: str) -> str:
    """Export standalone music file as MP3 320kbps."""
    _run([
        "ffmpeg", "-y",
        "-i", audio_path,
        "-c:a", "libmp3lame", "-b:a", "320k",
        output_path,
    ])
    print(f"[ffmpeg] Music-only export -> {output_path}")
    return output_path
