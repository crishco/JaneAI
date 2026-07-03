"""Tool execution loop for desktop automation requests."""

from __future__ import annotations

import logging

from app.agents.state import AgentState
from app.core.status import status_manager
from app.services.ollama_service import OllamaService, OllamaServiceError
from app.tools.tool_registry import ToolExecutionError, ToolRegistry

logger = logging.getLogger(__name__)


class ToolExecutor:
    """Uses the LLM to choose and run desktop tools."""

    def __init__(self, ollama_service: OllamaService, tool_registry: ToolRegistry) -> None:
        self._ollama_service = ollama_service
        self._tool_registry = tool_registry

    async def run(self, state: AgentState) -> AgentState:
        message = state["user_message"]
        status_manager.set("Looking at screen", "Analyzing desktop request")

        planning_prompt = (
            "You are JaneAI, a desktop assistant with access to automation tools.\n"
            "If a tool is required, respond with JSON only in this shape:\n"
            '{"tool": "tool_name", "args": {"key": "value"}}\n'
            "If no tool is required, respond with plain text only.\n\n"
            "Available tools:\n"
            f"{self._tool_registry.tool_descriptions}\n\n"
            f"User request: {message}"
        )

        try:
            llm_output = await self._ollama_service.generate_response(planning_prompt)
        except OllamaServiceError as exc:
            logger.error("Tool planning failed: %s", exc)
            return {
                **state,
                "response": (
                    "I couldn't reach the local language model to plan desktop actions. "
                    f"Details: {exc}"
                ),
            }

        parsed = self._tool_registry.parse_tool_call(llm_output)
        if parsed is None:
            return {**state, "response": llm_output.strip()}

        tool_name, args = parsed
        status_manager.set("Controlling desktop", f"Running {tool_name}")
        logger.info("Executing tool %s with args=%s", tool_name, args)

        try:
            tool_result = self._tool_registry.execute(tool_name, args)
        except ToolExecutionError as exc:
            logger.warning("Tool execution failed: %s", exc)
            return {
                **state,
                "response": f"I tried to run `{tool_name}` but it failed: {exc}",
            }

        status_manager.set("Thinking", "Summarizing tool result")
        summary_prompt = (
            "Summarize the result of a desktop automation action for the user.\n"
            f"User request: {message}\n"
            f"Tool: {tool_name}\n"
            f"Result: {tool_result}\n"
            "Respond naturally and mention what was done."
        )

        try:
            response = await self._ollama_service.generate_response(summary_prompt)
        except OllamaServiceError:
            response = tool_result

        return {
            **state,
            "tool_results": [tool_result],
            "response": response.strip(),
        }
