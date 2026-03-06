from typing import Any
from typing import Optional, TypedDict


class TinkerAnalysisState(TypedDict):
    # Input
    images: list[str]
    user_context: Optional[str]

    # Node 1 output
    system_classification: dict[str, Any]
    identified_components: list[dict[str, Any]]
    spatial_estimates: dict[str, Any]

    # Node 2 output
    matched_components: list[dict[str, Any]]
    power_estimate_mA: float
    cost_estimate_usd: float

    # Node 3 output
    physics_validation: dict[str, Any]
    system_valid: bool
    bottlenecks: list[dict[str, Any]]

    # Node 4 output
    tradeoff_analysis: list[dict[str, Any]]

    # Node 5 output
    suggestions: list[dict[str, Any]]

    # Node 6 output
    final_report: str

    # Meta
    errors: list[str]
    current_node: str
    retry_count: int
