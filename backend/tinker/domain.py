from abc import ABC, abstractmethod
from typing import Any


class DomainAdapter(ABC):
    @abstractmethod
    def get_classification_prompt(self) -> str:
        ...

    @abstractmethod
    def get_component_id_prompt(self, classification: dict[str, Any]) -> str:
        ...

    @abstractmethod
    def get_spatial_prompt(self, components: list[dict[str, Any]]) -> str:
        ...

    @abstractmethod
    def lookup_components(self, identified: list[dict[str, Any]]) -> list[dict[str, Any]]:
        ...

    @abstractmethod
    def validate_physics(self, components: list[dict[str, Any]], spatial: dict[str, Any]) -> dict[str, Any]:
        ...

    @abstractmethod
    def get_tradeoff_prompt(self, components: list[dict[str, Any]], validation: dict[str, Any]) -> str:
        ...

    @abstractmethod
    def get_alternatives_prompt(self, components: list[dict[str, Any]], validation: dict[str, Any]) -> str:
        ...

    @abstractmethod
    def suggest_alternatives(self, components: list[dict[str, Any]], validation: dict[str, Any]) -> list[dict[str, Any]]:
        ...

    @abstractmethod
    def apply_suggestion(
        self, components: list[dict[str, Any]], suggestion: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Apply a suggested modification to a copy of the component list.

        Each domain knows how its component swaps map to actual spec changes.
        Returns a modified copy — the original must not be mutated.
        """
        ...

    @abstractmethod
    def get_domain_name(self) -> str:
        ...
