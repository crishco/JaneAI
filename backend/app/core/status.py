"""Thread-safe runtime status tracking for the JaneAI agent."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class RuntimeStatus:
    """Current agent activity exposed to clients."""

    status: str = "Idle"
    detail: str = ""
    errors: list[str] = field(default_factory=list)
    updated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class StatusManager:
    """Tracks what JaneAI is doing and any startup/runtime errors."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._status = RuntimeStatus()
        self._startup_errors: list[str] = []

    def set(self, status: str, detail: str = "") -> None:
        with self._lock:
            self._status.status = status
            self._status.detail = detail
            self._status.updated_at = datetime.now(timezone.utc).isoformat()

    def add_error(self, message: str) -> None:
        with self._lock:
            self._status.errors.append(message)
            self._status.updated_at = datetime.now(timezone.utc).isoformat()

    def add_startup_error(self, message: str) -> None:
        with self._lock:
            self._startup_errors.append(message)
            self._status.errors.append(message)
            self._status.updated_at = datetime.now(timezone.utc).isoformat()

    def snapshot(self) -> RuntimeStatus:
        with self._lock:
            return RuntimeStatus(
                status=self._status.status,
                detail=self._status.detail,
                errors=list(self._status.errors),
                updated_at=self._status.updated_at,
            )

    @property
    def startup_errors(self) -> list[str]:
        with self._lock:
            return list(self._startup_errors)

    def clear_errors(self) -> None:
        with self._lock:
            self._status.errors.clear()
            self._status.updated_at = datetime.now(timezone.utc).isoformat()


status_manager = StatusManager()
