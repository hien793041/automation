"""Pydantic configuration models for ROK Bot Engine v2."""

from pathlib import Path
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class VisionConfig(BaseModel):
    """Vision pipeline configuration."""

    yolo_model_path: Path = Field(default=Path("models/yolo/rok_ui_v8.pt"))
    yolo_onnx_path: Optional[Path] = Field(default=Path("models/yolo/rok_ui_v8.onnx"))
    labels_path: Path = Field(default=Path("models/yolo/labels.yaml"))
    confidence_threshold: float = Field(default=0.5, ge=0.0, le=1.0)
    iou_threshold: float = Field(default=0.45, ge=0.0, le=1.0)
    ocr_lang: str = Field(default="eng+vie")
    template_fallback: bool = Field(default=True)


class PCConfig(BaseModel):
    """PC game client configuration."""

    window_title: str = Field(default="Rise of Kingdoms")


class HumanizationConfig(BaseModel):
    """Humanization engine configuration."""

    enabled: bool = Field(default=True)
    profile_path: Optional[Path] = None
    reaction_time_mu: float = Field(default=350.0)  # ms
    reaction_time_sigma: float = Field(default=80.0)  # ms
    click_interval_shape: float = Field(default=0.8)
    click_interval_scale: float = Field(default=1.2)
    fatigue_half_life_hours: float = Field(default=2.0)
    base_distraction_rate: float = Field(default=0.08, ge=0.0, le=1.0)
    base_misclick_rate: float = Field(default=0.01, ge=0.0, le=1.0)


class EmulatorConfig(BaseModel):
    """Emulator connection configuration."""

    adb_host: str = Field(default="127.0.0.1")
    adb_port: int = Field(default=5555)
    device_serial: Optional[str] = None
    scrcpy_enabled: bool = Field(default=False)
    scrcpy_port: int = Field(default=27183)


class ActionConfig(BaseModel):
    """Action priority and timeout configuration."""

    enabled_actions: List[str] = Field(default_factory=lambda: ["gather", "alliance_help", "scout", "train_troops", "reconnect"])
    priorities: Dict[str, int] = Field(default_factory=dict)
    default_timeout_seconds: float = Field(default=30.0)


class BotConfig(BaseModel):
    """Top-level bot configuration."""

    project_name: str = Field(default="rok-bot-engine")
    log_level: str = Field(default="INFO")
    screenshot_interval_seconds: float = Field(default=1.0)
    max_retry_attempts: int = Field(default=3)
    stuck_threshold_seconds: float = Field(default=60.0)
    vision: VisionConfig = Field(default_factory=VisionConfig)
    humanization: HumanizationConfig = Field(default_factory=HumanizationConfig)
    pc: PCConfig = Field(default_factory=PCConfig)
    emulator: EmulatorConfig = Field(default_factory=EmulatorConfig)
    actions: ActionConfig = Field(default_factory=ActionConfig)
