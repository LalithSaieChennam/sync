"""LangGraph pipeline: analyze -> compose -> generate & assemble.

Usage:
    from backend.agents.pipeline import run_pipeline
    result = run_pipeline("video.mp4", vibe="cinematic", platform="shorts")
"""

from typing import Any, Callable, Optional
from typing_extensions import TypedDict

from langgraph.graph import StateGraph, START, END

from backend.agents.scene_analyst import analyze_scene
from backend.agents.composer import compose_prompt
from backend.agents.audio_director import generate_and_assemble


class PipelineState(TypedDict, total=False):
    # Inputs
    video_path: str
    job_id: str
    vibe: str
    platform: str
    vocals: bool
    # Callback (not serialized, passed through state)
    on_stage_change: Optional[Callable]
    # Intermediate
    scene_analysis: dict[str, Any]
    lyria_prompt: str
    # Outputs
    scored_video_path: str
    music_only_path: str
    # Progress tracking
    stage: str
    progress: int
    message: str


def _notify(state: dict, stage: str, progress: int, message: str):
    """Call the progress callback if present."""
    cb = state.get("on_stage_change")
    if cb:
        try:
            cb(stage, progress, message)
        except Exception:
            pass


def _analyze_with_progress(state: dict) -> dict:
    _notify(state, "analyzing", 10, "Analyzing video scenes...")
    result = analyze_scene(state)
    _notify(state, "composing", 30, "Composing soundtrack prompt...")
    return result


def _compose_with_progress(state: dict) -> dict:
    _notify(state, "composing", 40, "Composing soundtrack prompt...")
    result = compose_prompt(state)
    _notify(state, "generating", 55, "Generating music with Lyria...")
    return result


def _generate_with_progress(state: dict) -> dict:
    _notify(state, "generating", 60, "Generating music with Lyria...")
    result = generate_and_assemble(state)
    _notify(state, "assembling", 90, "Mixing and mastering...")
    return result


def _build_graph() -> StateGraph:
    graph = StateGraph(PipelineState)

    graph.add_node("analyze_scene", _analyze_with_progress)
    graph.add_node("compose_prompt", _compose_with_progress)
    graph.add_node("generate_and_assemble", _generate_with_progress)

    graph.add_edge(START, "analyze_scene")
    graph.add_edge("analyze_scene", "compose_prompt")
    graph.add_edge("compose_prompt", "generate_and_assemble")
    graph.add_edge("generate_and_assemble", END)

    return graph.compile()


pipeline = _build_graph()


def run_pipeline(
    video_path: str,
    job_id: str = "default",
    vibe: str = "",
    platform: str = "general",
    vocals: bool = False,
    on_stage_change: Optional[Callable] = None,
) -> dict:
    """Run the full scoring pipeline on a video.

    Args:
        on_stage_change: Optional callback(stage, progress, message) for live updates.

    Returns the final state dict with scored_video_path and music_only_path.
    """
    initial_state = {
        "video_path": video_path,
        "job_id": job_id,
        "vibe": vibe,
        "platform": platform,
        "vocals": vocals,
        "on_stage_change": on_stage_change,
        "stage": "uploading",
        "progress": 0,
        "message": "Starting pipeline...",
    }

    result = pipeline.invoke(initial_state)
    return result
