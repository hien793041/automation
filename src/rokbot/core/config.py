"""Pydantic configuration models for ROK Bot Engine v2."""

from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class VisionConfig(BaseModel):
    """Vision pipeline configuration."""

    yolo_model_path: Path = Field(default=Path("models/yolo/rok_ui_v8.pt"))
    confidence_threshold: float = Field(default=0.5, ge=0.0, le=1.0)
    ocr_lang: str = Field(default="eng+vie")


class PCConfig(BaseModel):
    """PC game client configuration."""

    window_title: str = Field(default="Rise of Kingdoms")


class HumanizationConfig(BaseModel):
    """Humanization engine configuration.

    Supports both flat overrides (for backward compatibility) and rich
    per-engine blocks loaded from ``config/humanization.yaml``.
    """

    enabled: bool = Field(default=True)
    schedule_enabled: bool = Field(default=False)
    profile_path: Optional[Path] = None
    fatigue_half_life_hours: float = Field(default=2.0)
    base_distraction_rate: float = Field(default=0.08, ge=0.0, le=1.0)
    base_misclick_rate: float = Field(default=0.01, ge=0.0, le=1.0)

    # Rich per-engine configuration loaded from humanization.yaml
    timing: Optional[Dict[str, Dict[str, Any]]] = None
    movement: Optional[Dict[str, Any]] = None


class ActionConfig(BaseModel):
    """Action priority and timeout configuration."""

    enabled_actions: List[str] = Field(default_factory=lambda: ["gather", "alliance_help", "scout", "train_troops", "reconnect"])
    priorities: Dict[str, int] = Field(default_factory=dict)
    # Full per-action configuration blocks from actions.yaml.
    action_configs: Dict[str, Dict[str, Any]] = Field(default_factory=dict)


class BotConfig(BaseModel):
    """Top-level bot configuration."""

    project_name: str = Field(default="rok-bot-engine")
    screenshot_interval_seconds: float = Field(default=1.0)
    max_retry_attempts: int = Field(default=3)
    stuck_threshold_seconds: float = Field(default=60.0)
    vision: VisionConfig = Field(default_factory=VisionConfig)
    humanization: HumanizationConfig = Field(default_factory=HumanizationConfig)
    pc: PCConfig = Field(default_factory=PCConfig)
    actions: ActionConfig = Field(default_factory=ActionConfig)
