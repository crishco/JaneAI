"""LangGraph agent state definitions."""

from __future__ import annotations

from typing import Literal, TypedDict

RouteName = Literal["conversation", "memory", "tools"]


class AgentState(TypedDict, total=False):
    """Shared state passed between LangGraph nodes."""

    user_message: str
    conversation_id: str
    route: RouteName
    context: str
    tool_results: list[str]
    response: str
