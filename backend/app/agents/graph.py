"""LangGraph orchestration graph for JaneAI."""

from __future__ import annotations

import logging

from langgraph.graph import END, START, StateGraph

from app.agents.executor import ToolExecutor
from app.agents.planner import Planner
from app.agents.state import AgentState, RouteName
from app.core.status import status_manager
from app.history.history_service import HistoryService, HistoryServiceError
from app.rag.retriever import Retriever, RetrieverError
from app.services.ollama_service import OllamaService, OllamaServiceError

logger = logging.getLogger(__name__)


class AgentGraph:
    """Builds and runs the JaneAI LangGraph workflow."""

    def __init__(
        self,
        ollama_service: OllamaService,
        retriever: Retriever,
        history_service: HistoryService,
        planner: Planner,
        tool_executor: ToolExecutor,
    ) -> None:
        self._ollama_service = ollama_service
        self._retriever = retriever
        self._history_service = history_service
        self._planner = planner
        self._tool_executor = tool_executor
        self._graph = self._build_graph()

    def _build_graph(self):
        builder = StateGraph(AgentState)
        builder.add_node("route", self._route_node)
        builder.add_node("conversation", self._conversation_node)
        builder.add_node("memory", self._memory_node)
        builder.add_node("tools", self._tools_node)

        builder.add_edge(START, "route")
        builder.add_conditional_edges(
            "route",
            self._route_decision,
            {
                "conversation": "conversation",
                "memory": "memory",
                "tools": "tools",
            },
        )
        builder.add_edge("conversation", END)
        builder.add_edge("memory", END)
        builder.add_edge("tools", END)
        return builder.compile()

    async def run(self, user_message: str, conversation_id: str) -> AgentState:
        initial_state: AgentState = {
            "user_message": user_message,
            "conversation_id": conversation_id,
            "tool_results": [],
        }
        return await self._graph.ainvoke(initial_state)

    async def _route_node(self, state: AgentState) -> AgentState:
        status_manager.set("Thinking", "Routing request")
        route = await self._planner.classify(state["user_message"])
        return {**state, "route": route}

    @staticmethod
    def _route_decision(state: AgentState) -> RouteName:
        return state.get("route", "conversation")

    async def _conversation_node(self, state: AgentState) -> AgentState:
        status_manager.set("Thinking", "Generating response")
        message = state["user_message"]
        try:
            response = await self._ollama_service.generate_response(message)
        except OllamaServiceError as exc:
            logger.error("Conversation generation failed: %s", exc)
            return {
                **state,
                "response": (
                    "I couldn't generate a response because Ollama is unavailable. "
                    f"Details: {exc}"
                ),
            }
        return {**state, "response": response}

    async def _memory_node(self, state: AgentState) -> AgentState:
        status_manager.set("Searching memory", "Retrieving relevant documents")
        message = state["user_message"]
        chunk_count = 0
        try:
            chunks = await self._retriever.retrieve(message)
            chunk_count = len(chunks)
            prompt = self._retriever.build_prompt(message, chunks)
            status_manager.set("Thinking", "Answering with retrieved context")
            response = await self._ollama_service.generate_response(prompt)
        except RetrieverError as exc:
            logger.warning("Memory retrieval failed, falling back: %s", exc)
            try:
                response = await self._ollama_service.generate_response(message)
            except OllamaServiceError as llm_exc:
                return {
                    **state,
                    "response": (
                        "Memory retrieval and fallback generation both failed. "
                        f"Details: {llm_exc}"
                    ),
                }
        except OllamaServiceError as exc:
            logger.error("Memory response generation failed: %s", exc)
            return {
                **state,
                "response": (
                    "I retrieved context but couldn't reach Ollama to answer. "
                    f"Details: {exc}"
                ),
            }

        context_summary = f"Retrieved {chunk_count} memory chunk(s)."
        return {**state, "context": context_summary, "response": response}

    async def _tools_node(self, state: AgentState) -> AgentState:
        return await self._tool_executor.run(state)


class AgentOrchestrator:
    """High-level interface used by the chat API."""

    def __init__(
        self,
        graph: AgentGraph,
        history_service: HistoryService,
    ) -> None:
        self._graph = graph
        self._history_service = history_service

    async def respond(
        self,
        message: str,
        conversation_id: str | None = None,
    ) -> tuple[str, str]:
        normalized = message.strip()
        if not normalized:
            raise ValueError("Message cannot be empty")

        conversation_id = self._resolve_conversation_id(conversation_id)
        self._history_service.add_message(conversation_id, "user", normalized)

        try:
            result = await self._graph.run(normalized, conversation_id)
            response = str(result.get("response", "")).strip()
            if not response:
                response = "I couldn't produce a response for that request."
            self._history_service.add_message(conversation_id, "assistant", response)
            status_manager.set("Idle", "Ready")
            return response, conversation_id
        except HistoryServiceError as exc:
            status_manager.set("Error", "History persistence failed")
            raise RuntimeError("Failed to persist conversation history") from exc
        except Exception as exc:
            status_manager.set("Error", str(exc))
            logger.exception("Agent orchestration failed")
            raise RuntimeError(f"Agent execution failed: {exc}") from exc

    def _resolve_conversation_id(self, conversation_id: str | None) -> str:
        if conversation_id is None:
            return self._history_service.create_conversation()
        if not self._history_service.conversation_exists(conversation_id):
            raise ValueError(f"Conversation not found: {conversation_id}")
        return conversation_id
