"""Screen capture utilities using mss and OpenCV."""

from __future__ import annotations

import base64
import logging
from dataclasses import dataclass

import cv2
import mss
import numpy as np

logger = logging.getLogger(__name__)


class ScreenshotError(Exception):
    """Raised when screen capture fails."""


@dataclass(frozen=True)
class ScreenshotResult:
    """Captured screen metadata and encoded image."""

    width: int
    height: int
    monitor_index: int
    image_base64: str
    format: str = "png"


class ScreenCaptureService:
    """Captures the primary display and encodes it for tool responses."""

    def capture_primary(self, monitor_index: int = 1) -> ScreenshotResult:
        """Capture a monitor and return a base64-encoded PNG."""
        try:
            with mss.mss() as sct:
                monitors = sct.monitors
                if monitor_index >= len(monitors):
                    raise ScreenshotError(
                        f"Monitor index {monitor_index} is unavailable "
                        f"(found {len(monitors) - 1} monitor(s))"
                    )

                monitor = monitors[monitor_index]
                raw = sct.grab(monitor)
                frame = np.array(raw)
                frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
                success, buffer = cv2.imencode(".png", frame)
                if not success:
                    raise ScreenshotError("Failed to encode screenshot as PNG")

                encoded = base64.b64encode(buffer.tobytes()).decode("ascii")
                logger.info(
                    "Captured screenshot %dx%d from monitor %d",
                    frame.shape[1],
                    frame.shape[0],
                    monitor_index,
                )
                return ScreenshotResult(
                    width=int(frame.shape[1]),
                    height=int(frame.shape[0]),
                    monitor_index=monitor_index,
                    image_base64=encoded,
                )
        except ScreenshotError:
            raise
        except Exception as exc:
            logger.exception("Screen capture failed")
            raise ScreenshotError(f"Screen capture failed: {exc}") from exc

    def describe_capture(self, result: ScreenshotResult) -> str:
        """Return a concise textual summary of a capture."""
        return (
            f"Captured monitor {result.monitor_index} at "
            f"{result.width}x{result.height}px ({result.format})."
        )
