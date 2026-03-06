from __future__ import annotations

from copy import deepcopy
from typing import Any, Callable

from langgraph.graph import END, StateGraph

from tinker.domain import DomainAdapter
from tinker.nodes.alternative_suggester import alternative_suggester_node
from tinker.nodes.component_lookup import component_lookup_node
from tinker.nodes.physics_validation import physics_validation_node
from tinker.nodes.report_generator import report_generator_node
from tinker.nodes.tradeoff_analyzer import tradeoff_analyzer_node
from tinker.nodes.vision_analysis import vision_analysis_node
from tinker.state import TinkerAnalysisState

MAX_PHYSICS_RETRIES = 2


def _route_after_validation(state: dict[str, Any]) -> str:
    route = state.get("physics_validation", {}).get("route", "valid")
    retry = int(state.get("retry_count", 0))
    if route == "invalid_fixable" and retry < MAX_PHYSICS_RETRIES:
        return "invalid_fixable"
    if route == "invalid_fatal":
        return "invalid_fatal"
    return "valid"


def build_graph(
    adapter: DomainAdapter,
    llm: Any,
    on_event: Callable[[str, str, dict[str, Any]], None] | None = None,
) -> StateGraph:
    """Build and compile the tinker analysis StateGraph."""

    def emit(node: str, status: str, payload: dict[str, Any] | None = None) -> None:
        if on_event:
            on_event(node, status, payload or {})

    # -- node wrappers that delegate to the pure node functions --

    def vision_analysis(state: dict[str, Any]) -> dict[str, Any]:
        emit("vision_analysis", "started")
        result = vision_analysis_node(state, adapter, llm)
        emit("vision_analysis", "completed", result)
        return result

    def component_lookup(state: dict[str, Any]) -> dict[str, Any]:
        emit("component_lookup", "started", {"retry": state.get("retry_count", 0)})
        result = component_lookup_node(state, adapter)
        emit("component_lookup", "completed", result)
        return result

    def physics_validation(state: dict[str, Any]) -> dict[str, Any]:
        retry = int(state.get("retry_count", 0))
        emit("physics_validation", "started", {"retry": retry})
        result = physics_validation_node(state, adapter)
        result["retry_count"] = retry + 1
        emit("physics_validation", "completed", result)
        return result

    def tradeoff_analyzer(state: dict[str, Any]) -> dict[str, Any]:
        emit("tradeoff_analyzer", "started")
        result = tradeoff_analyzer_node(state, adapter, llm)
        emit("tradeoff_analyzer", "completed", result)
        return result

    def alternative_suggester(state: dict[str, Any]) -> dict[str, Any]:
        emit("alternative_suggester", "started")
        result = alternative_suggester_node(state, adapter, llm)
        emit("alternative_suggester", "completed", result)
        return result

    def report_generator(state: dict[str, Any]) -> dict[str, Any]:
        emit("report_generator", "started")
        result = report_generator_node(state, adapter)
        emit("report_generator", "completed", result)
        return result

    # -- build the graph --

    graph = StateGraph(TinkerAnalysisState)

    graph.add_node("vision_analysis", vision_analysis)
    graph.add_node("component_lookup", component_lookup)
    graph.add_node("physics_validation", physics_validation)
    graph.add_node("tradeoff_analyzer", tradeoff_analyzer)
    graph.add_node("alternative_suggester", alternative_suggester)
    graph.add_node("report_generator", report_generator)

    graph.set_entry_point("vision_analysis")

    graph.add_edge("vision_analysis", "component_lookup")
    graph.add_edge("component_lookup", "physics_validation")

    graph.add_conditional_edges(
        "physics_validation",
        _route_after_validation,
        {
            "valid": "tradeoff_analyzer",
            "invalid_fixable": "component_lookup",
            "invalid_fatal": "report_generator",
        },
    )

    graph.add_edge("tradeoff_analyzer", "alternative_suggester")
    graph.add_edge("alternative_suggester", "report_generator")
    graph.add_edge("report_generator", END)

    return graph.compile()


def run_pipeline(
    initial_state: dict[str, Any],
    adapter: DomainAdapter,
    llm: Any,
    on_event: Callable[[str, str, dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    """Run the full tinker pipeline via the LangGraph StateGraph."""
    compiled = build_graph(adapter, llm, on_event)
    result = compiled.invoke(deepcopy(initial_state))
    return result
