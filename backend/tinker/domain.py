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
    def get_domain_name(self) -> str:
        ...
