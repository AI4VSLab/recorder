from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import datetime
from typing import Any

try:
    import tobii_research as tobii_sdk
except ImportError:  # pragma: no cover - optional dependency
    tobii_sdk = None


@dataclass
class StimulusEvent:
    slide_id: str
    image_path: str
    shown_at: str
    tobii_timestamp: int | None = None
    source: str = "flask"
    metadata: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "slide_id": self.slide_id,
            "image_path": self.image_path,
            "shown_at": self.shown_at,
            "tobii_timestamp": self.tobii_timestamp,
            "source": self.source,
            "metadata": self.metadata or {},
        }


class TobiiStimulusTracker:
    """Tracks the last N stimuli our app presented and optionally timestamps them with Tobii."""

    def __init__(
        self,
        stimulus_template: str,
        history_size: int = 5,
        auto_connect_sdk: bool = True,
    ) -> None:
        self.stimulus_template = stimulus_template
        self.history: deque[StimulusEvent] = deque(maxlen=history_size)
        self.connected_tracker = None
        self.sdk_available = tobii_sdk is not None
        self.sdk_error = ""

        if auto_connect_sdk and self.sdk_available:
            self.discover_tracker()

    def discover_tracker(self):
        if tobii_sdk is None:
            self.sdk_error = "tobii_research is not installed"
            return None

        try:
            trackers = tobii_sdk.find_all_eyetrackers()
        except Exception as exc:  # pragma: no cover - hardware specific
            self.sdk_error = str(exc)
            return None

        self.connected_tracker = trackers[0] if trackers else None
        if self.connected_tracker is None:
            self.sdk_error = "No Tobii eye tracker discovered"
        else:
            self.sdk_error = ""
        return self.connected_tracker

    def resolve_image_path(self, slide_id: str, image_path: str | None = None) -> str:
        if image_path:
            return image_path
        return self.stimulus_template.format(slide_id=slide_id)

    def record_presented_stimulus(
        self,
        slide_id: str,
        image_path: str | None = None,
        metadata: dict[str, Any] | None = None,
        source: str = "flask",
    ) -> StimulusEvent:
        tobii_timestamp = None
        if tobii_sdk is not None:
            try:
                tobii_timestamp = tobii_sdk.get_system_time_stamp()
            except Exception:  # pragma: no cover - hardware specific
                tobii_timestamp = None

        event = StimulusEvent(
            slide_id=str(slide_id),
            image_path=self.resolve_image_path(str(slide_id), image_path=image_path),
            shown_at=datetime.now().isoformat(timespec="seconds"),
            tobii_timestamp=tobii_timestamp,
            source=source,
            metadata=metadata or {},
        )
        self.history.append(event)
        return event

    def get_recent_events(self) -> list[dict[str, Any]]:
        return [event.to_dict() for event in self.history]

    def get_recent_image_paths(self) -> list[str]:
        return [event.image_path for event in self.history]

    def get_latest_event(self) -> dict[str, Any] | None:
        if not self.history:
            return None
        return self.history[-1].to_dict()

    def reset(self) -> None:
        self.history.clear()

    def get_sdk_status(self) -> dict[str, Any]:
        tracker_name = None
        tracker_address = None

        if self.connected_tracker is not None:
            tracker_name = getattr(self.connected_tracker, "device_name", None)
            tracker_address = getattr(self.connected_tracker, "address", None)

        return {
            "sdk_available": self.sdk_available,
            "connected": self.connected_tracker is not None,
            "tracker_name": tracker_name,
            "tracker_address": tracker_address,
            "error": self.sdk_error,
        }
