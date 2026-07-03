"""Desktop automation using PyAutoGUI and PyGetWindow."""

from __future__ import annotations

import logging
from dataclasses import dataclass

import pyautogui
import pygetwindow as gw

logger = logging.getLogger(__name__)

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.05


class ScreenControlError(Exception):
    """Raised when a desktop automation action fails."""


@dataclass(frozen=True)
class WindowInfo:
    """Metadata about an active or named window."""

    title: str
    left: int
    top: int
    width: int
    height: int
    is_active: bool


class ScreenControlService:
    """Executes mouse, keyboard, and window queries on the desktop."""

    def get_active_window(self) -> WindowInfo:
        try:
            window = gw.getActiveWindow()
            if window is None:
                raise ScreenControlError("No active window detected")

            return WindowInfo(
                title=window.title or "Untitled",
                left=int(window.left),
                top=int(window.top),
                width=int(window.width),
                height=int(window.height),
                is_active=True,
            )
        except ScreenControlError:
            raise
        except Exception as exc:
            logger.exception("Failed to read active window")
            raise ScreenControlError(f"Failed to read active window: {exc}") from exc

    def list_windows(self, limit: int = 10) -> list[WindowInfo]:
        try:
            windows = gw.getAllWindows()
            visible = [w for w in windows if w.title and w.width > 0 and w.height > 0]
            active = gw.getActiveWindow()
            active_title = active.title if active else None

            results: list[WindowInfo] = []
            for window in visible[:limit]:
                results.append(
                    WindowInfo(
                        title=window.title,
                        left=int(window.left),
                        top=int(window.top),
                        width=int(window.width),
                        height=int(window.height),
                        is_active=window.title == active_title,
                    )
                )
            return results
        except Exception as exc:
            logger.exception("Failed to list windows")
            raise ScreenControlError(f"Failed to list windows: {exc}") from exc

    def click(self, x: int, y: int, button: str = "left", clicks: int = 1) -> str:
        try:
            pyautogui.click(x=x, y=y, button=button, clicks=clicks)
            return f"Clicked {button} button at ({x}, {y})"
        except Exception as exc:
            logger.exception("Click failed at (%s, %s)", x, y)
            raise ScreenControlError(f"Click failed: {exc}") from exc

    def move_mouse(self, x: int, y: int, duration: float = 0.2) -> str:
        try:
            pyautogui.moveTo(x, y, duration=duration)
            return f"Moved mouse to ({x}, {y})"
        except Exception as exc:
            logger.exception("Mouse move failed")
            raise ScreenControlError(f"Mouse move failed: {exc}") from exc

    def type_text(self, text: str, interval: float = 0.02) -> str:
        if not text.strip():
            raise ScreenControlError("Cannot type empty text")
        try:
            pyautogui.write(text, interval=interval)
            return f"Typed {len(text)} character(s)"
        except Exception as exc:
            logger.exception("Typing failed")
            raise ScreenControlError(f"Typing failed: {exc}") from exc

    def press_key(self, key: str) -> str:
        if not key.strip():
            raise ScreenControlError("Key name is required")
        try:
            pyautogui.press(key.strip())
            return f"Pressed key '{key.strip()}'"
        except Exception as exc:
            logger.exception("Key press failed")
            raise ScreenControlError(f"Key press failed: {exc}") from exc

    def scroll(self, amount: int) -> str:
        try:
            pyautogui.scroll(amount)
            direction = "up" if amount > 0 else "down"
            return f"Scrolled {direction} by {abs(amount)}"
        except Exception as exc:
            logger.exception("Scroll failed")
            raise ScreenControlError(f"Scroll failed: {exc}") from exc
