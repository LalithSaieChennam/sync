"""FastAPI routes for the Sync scoring API."""

import os
import re
import uuid
import shutil
import threading
import time
from typing import Optional

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse

from backend.models import JobStatus, Platform
from backend.services.ffmpeg import get_video_duration, has_video_stream

router = APIRouter(prefix="/api")

# Thread-safe job store
_jobs_lock = threading.Lock()
_jobs: dict[str, JobStatus] = {}
MAX_DURATION = 120
MIN_DURATION = 3
MAX_SIZE_BYTES = 100 * 1024 * 1024  # 100MB
JOB_ID_PATTERN = re.compile(r"^[a-f0-9]{12}$")


def _set_job(job_id: str, status: JobStatus):
    with _jobs_lock:
        _jobs[job_id] = status


def _get_job(job_id: str) -> Optional[JobStatus]:
    with _jobs_lock:
        return _jobs.get(job_id)


def _validate_job_id(job_id: str):
    """Prevent path traversal — job_id must be exactly 12 hex chars."""
    if not JOB_ID_PATTERN.match(job_id):
        raise HTTPException(400, "Invalid job ID.")


def _cleanup_job_dir(job_dir: str):
    """Remove a job directory and all its contents."""
    try:
        if os.path.exists(job_dir):
            shutil.rmtree(job_dir)
    except Exception:
        pass


def _run_pipeline_background(job_id: str, video_path: str, vibe: str,
                             platform: str, vocals: bool):
    """Run the pipeline in a background thread, updating job status at each stage."""
    # Import here to avoid circular imports at module level
    from backend.agents.pipeline import run_pipeline

    try:
        _set_job(job_id, JobStatus(
            job_id=job_id, stage="analyzing", progress=10,
            message="Analyzing video scenes..."
        ))

        result = run_pipeline(
            video_path=video_path,
            job_id=job_id,
            vibe=vibe,
            platform=platform,
            vocals=vocals,
            on_stage_change=lambda stage, progress, msg: _set_job(
                job_id, JobStatus(job_id=job_id, stage=stage, progress=progress, message=msg)
            ),
        )

        _set_job(job_id, JobStatus(
            job_id=job_id,
            stage="complete",
            progress=100,
            message="Scoring complete!",
            scored_video_url=f"/api/download/{job_id}",
            music_only_url=f"/api/download/{job_id}/music",
        ))

        # Cleanup intermediate files, keep only final outputs
        job_dir = os.path.join("output", job_id)
        for fname in ["raw_music.mp3", "matched.mp3", "trimmed.mp3", "ducked.mp3", "faded.mp3"]:
            fpath = os.path.join(job_dir, fname)
            if os.path.exists(fpath):
                os.remove(fpath)

    except Exception as e:
        _set_job(job_id, JobStatus(
            job_id=job_id, stage="error", progress=0,
            message=f"Pipeline failed: {str(e)[:200]}"
        ))


@router.post("/score")
async def score_video(
    video: UploadFile = File(...),
    vibe: str = Form(""),
    platform: Platform = Form(Platform.general),
    vocals: bool = Form(False),
):
    """Upload a video and start the scoring pipeline."""
    # Validate file type
    filename = video.filename or ""
    ext = os.path.splitext(filename)[1].lower()
    if ext not in (".mp4", ".mov", ".webm"):
        raise HTTPException(400, f"Unsupported format: {ext}. Use MP4, MOV, or WebM.")

    # Generate job ID and save video
    job_id = uuid.uuid4().hex[:12]
    job_dir = os.path.join("output", job_id)
    os.makedirs(job_dir, exist_ok=True)

    video_path = os.path.join(job_dir, f"input{ext}")
    try:
        with open(video_path, "wb") as f:
            shutil.copyfileobj(video.file, f)
    except Exception:
        _cleanup_job_dir(job_dir)
        raise HTTPException(500, "Failed to save video file.")

    # Validate file isn't empty
    file_size = os.path.getsize(video_path)
    if file_size == 0:
        _cleanup_job_dir(job_dir)
        raise HTTPException(400, "Empty video file.")

    # Validate file size
    if file_size > MAX_SIZE_BYTES:
        _cleanup_job_dir(job_dir)
        raise HTTPException(
            413, f"File is {file_size // 1024 // 1024}MB. Max {MAX_SIZE_BYTES // 1024 // 1024}MB."
        )

    # Validate it has a video stream (not an audio-only file)
    if not has_video_stream(video_path):
        _cleanup_job_dir(job_dir)
        raise HTTPException(400, "File has no video stream. Upload a video, not an audio file.")

    # Validate duration
    try:
        duration = get_video_duration(video_path)
    except Exception:
        _cleanup_job_dir(job_dir)
        raise HTTPException(400, "Could not read video file. Is it a valid video?")

    if duration < MIN_DURATION:
        _cleanup_job_dir(job_dir)
        raise HTTPException(400, f"Video is {duration:.1f}s. Minimum is {MIN_DURATION}s.")

    if duration > MAX_DURATION:
        _cleanup_job_dir(job_dir)
        raise HTTPException(400, f"Video is {duration:.0f}s. Maximum is {MAX_DURATION}s.")

    # Initialize job status
    _set_job(job_id, JobStatus(
        job_id=job_id, stage="uploading", progress=5,
        message="Video uploaded, starting pipeline..."
    ))

    # Launch pipeline in background thread
    thread = threading.Thread(
        target=_run_pipeline_background,
        args=(job_id, video_path, vibe, platform.value, vocals),
        daemon=True,
    )
    thread.start()

    return {"job_id": job_id}


@router.get("/status/{job_id}")
async def get_status(job_id: str):
    """Get current pipeline status for a job."""
    _validate_job_id(job_id)
    status = _get_job(job_id)
    if not status:
        raise HTTPException(404, "Job not found.")
    return status


@router.get("/download/{job_id}")
async def download_video(job_id: str):
    """Download the scored video."""
    _validate_job_id(job_id)
    path = os.path.join("output", job_id, "scored_video.mp4")
    if not os.path.exists(path):
        raise HTTPException(404, "Scored video not ready or not found.")
    return FileResponse(path, media_type="video/mp4", filename=f"sync_{job_id}.mp4")


@router.get("/download/{job_id}/music")
async def download_music(job_id: str):
    """Download the music-only file."""
    _validate_job_id(job_id)
    path = os.path.join("output", job_id, "score_only.mp3")
    if not os.path.exists(path):
        raise HTTPException(404, "Music file not ready or not found.")
    return FileResponse(path, media_type="audio/mpeg", filename=f"sync_{job_id}_music.mp3")
