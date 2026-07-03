"""Desktop and automation tools exposed to the LangGraph agent."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Any, Callable

from app.desktop.screen_control import ScreenControlError, ScreenControlService
from app.desktop.screenshot import ScreenCaptureService, ScreenshotError

logger = logging.getLogger(__name__)


class ToolExecutionError(Exception):
    """Raised when a tool call cannot be executed."""


@dataclass(frozen=True)
class ToolDefinition:
    """Metadata for an agent tool."""

    name: str
    description: str
    handler: Callable[[dict[str, Any]], str]


class ToolRegistry:
    """Registers and executes desktop tools for the agent."""

    def __init__(
        self,
        screen_capture: ScreenCaptureService,
        screen_control: ScreenControlService,
    ) -> None:
        self._screen_capture = screen_capture
        self._screen_control = screen_control
        self._tools: dict[str, ToolDefinition] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        self.register(
            "capture_screen",
            "Capture the primary monitor screenshot and return dimensions.",
            self._capture_screen,
        )
        self.register(
            "get_active_window",
            "Return metadata about the currently active desktop window.",
            self._get_active_window,
        )
        self.register(
            "list_windows",
            "List visible desktop windows with titles and bounds.",
            self._list_windows,
        )
        self.register(
            "click",
            "Click the mouse at x and y coordinates. Args: x, y, button, clicks.",
            self._click,
        )
        self.register(
            "move_mouse",
            "Move the mouse cursor to x and y coordinates. Args: x, y.",
            self._move_mouse,
        )
        self.register(
            "type_text",
            "Type text using the keyboard. Args: text.",
            self._type_text,
        )
        self.register(
            "press_key",
            "Press a keyboard key such as enter, esc, or tab. Args: key.",
            self._press_key,
        )
        self.register(
            "scroll",
            "Scroll the mouse wheel up or down. Args: amount (positive up).",
            self._scroll,
        )

    def register(
        self,
        name: str,
        description: str,
        handler: Callable[[dict[str, Any]], str],
    ) -> None:
        self._tools[name] = ToolDefinition(name=name, description=description, handler=handler)

    @property
    def tool_descriptions(self) -> str:
        lines = []
        for tool in self._tools.values():
            lines.append(f"- {tool.name}: {tool.description}")
        return "\n".join(lines)

    def execute(self, tool_name: str, args: dict[str, Any] | None = None) -> str:
        tool = self._tools.get(tool_name)
        if tool is None:
            raise ToolExecutionError(f"Unknown tool: {tool_name}")
        try:
            return tool.handler(args or {})
        except (ScreenshotError, ScreenControlError) as exc:
            raise ToolExecutionError(str(exc)) from exc

    def parse_tool_call(self, llm_output: str) -> tuple[str, dict[str, Any]] | None:
        """Extract a JSON tool call from an LLM response."""
        match = re.search(r"\{.*\}", llm_output, re.DOTALL)
        if not match:
            return None

        try:
            payload = json.loads(match.group(0))
        except json.JSONDecodeError:
            return None

        tool_name = payload.get("tool") or payload.get("name")
        if not isinstance(tool_name, str):
            return None

        args = payload.get("args", {})
        if not isinstance(args, dict):
            args = {}
        return tool_name, args

    def _capture_screen(self, args: dict[str, Any]) -> str:
        monitor_index = int(args.get("monitor_index", 1))
        capture = self._screen_capture.capture_primary(monitor_index=monitor_index)
        summary = self._screen_capture.describe_capture(capture)
        return (
            f"{summary} "
            f"Image data is available internally for follow-up reasoning."
        )

    def _get_active_window(self, _args: dict[str, Any]) -> str:
        window = self._screen_control.get_active_window()
        return (
            f"Active window '{window.title}' at "
            f"({window.left}, {window.top}) size {window.width}x{window.height}."
        )

    def _list_windows(self, args: dict[str, Any]) -> str:
        limit = int(args.get("limit", 8))
        windows = self._screen_control.list_windows(limit=limit)
        if not windows:
            return "No visible windows were found."
        lines = []
        for index, window in enumerate(windows, start=1):
            active = " active" if window.is_active else ""
            lines.append(
                f"{index}. '{window.title}'{active} at "
                f"({window.left}, {window.top}) {window.width}x{window.height}"
            )
        return "\n".join(lines)

    def _click(self, args: dict[str, Any]) -> str:
        return self._screen_control.click(
            x=int(args["x"]),
            y=int(args["y"]),
            button=str(args.get("button", "left")),
            clicks=int(args.get("clicks", 1)),
        )

    def _move_mouse(self, args: dict[str, Any]) -> str:
        return self._screen_control.move_mouse(
            x=int(args["x"]),
            y=int(args["y"]),
            duration=float(args.get("duration", 0.2)),
        )

    def _type_text(self, args: dict[str, Any]) -> str:
        return self._screen_control.type_text(str(args.get("text", "")))

    def _press_key(self, args: dict[str, Any]) -> str:
        return self._screen_control.press_key(str(args.get("key", "")))

    def _scroll(self, args: dict[str, Any]) -> str:
        return self._screen_control.scroll(int(args.get("amount", -300)))
