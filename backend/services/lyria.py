"""Lyria 3 Pro music generation wrapper.

Sends a text prompt (with optional timestamps) to Lyria 3 Pro
and saves the generated audio file.
"""

from google import genai
from google.genai import types

from backend.config import GOOGLE_AI_API_KEY

client = genai.Client(api_key=GOOGLE_AI_API_KEY)


def _check_content_filter(response) -> str | None:
    """Check if Lyria blocked the prompt. Returns reason string or None."""
    if not response.candidates:
        # Check if there's a block reason
        if hasattr(response, 'prompt_feedback') and response.prompt_feedback:
            return f"Prompt blocked: {response.prompt_feedback}"
        return "Lyria returned no output — prompt may reference a real artist or contain blocked content"

    candidate = response.candidates[0]
    if hasattr(candidate, 'finish_reason') and candidate.finish_reason:
        reason = str(candidate.finish_reason)
        if 'SAFETY' in reason or 'BLOCKED' in reason:
            return f"Content filtered: {reason}"

    return None


def generate_music(prompt: str, output_path: str = "output/generated_score.mp3") -> str:
    """Generate music from a text prompt using Lyria 3 Pro.

    Args:
        prompt: Music generation prompt, optionally with [MM:SS] timestamps.
        output_path: Where to save the generated audio file.

    Returns:
        Path to the saved audio file.
    """
    if not prompt or not prompt.strip():
        raise ValueError("Empty music prompt")

    print(f"[lyria] Generating music ({len(prompt)} chars prompt)...")

    response = client.models.generate_content(
        model="lyria-3-pro-preview",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_modalities=["AUDIO", "TEXT"],
        ),
    )

    # Check for content filter / empty response
    block_reason = _check_content_filter(response)
    if block_reason:
        raise ContentFilterError(block_reason)

    candidate = response.candidates[0]
    if not candidate.content or not candidate.content.parts:
        raise RuntimeError("Lyria returned empty content")

    # Extract audio
    audio_saved = False
    for part in candidate.content.parts:
        if part.inline_data is not None:
            if not part.inline_data.data:
                continue
            with open(output_path, "wb") as f:
                f.write(part.inline_data.data)
            audio_saved = True
            print(f"[lyria] Audio saved to {output_path}")
        elif part.text is not None:
            print(f"[lyria] Model text: {part.text[:200]}")

    if not audio_saved:
        raise RuntimeError("Lyria did not return audio data in the response.")

    return output_path


class ContentFilterError(RuntimeError):
    """Raised when Lyria blocks a prompt due to content filtering."""
    pass
