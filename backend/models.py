"""Pydantic models for API request/response schemas."""

from enum import Enum
from typing import Optional

from pydantic import BaseModel


class Platform(str, Enum):
    tiktok = "tiktok"
    reels = "reels"
    shorts = "shorts"
    general = "general"


class JobStatus(BaseModel):
    job_id: str
    stage: str
    progress: int
    message: str
    scored_video_url: Optional[str] = None
    music_only_url: Optional[str] = None


class ScoreRequest(BaseModel):
    vibe: str = ""
    platform: Platform = Platform.general
    vocals: bool = False
