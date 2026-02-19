"""Base interface for external ticket systems (Salesforce Case, Work Order, etc.)."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class TicketResult:
    """Result of creating a ticket in an external system."""
    ticket_id: str
    url: Optional[str] = None
    title: Optional[str] = None
    body: Optional[str] = None


class TicketConnector(ABC):
    """Abstract connector for creating tickets in an external system."""

    @abstractmethod
    def create_case(
        self,
        subject: str,
        description: str = "",
        asset_id: str = "",
        plant_id: str = "",
        diagnosis_id: Optional[int] = None,
        root_cause: str = "",
        **kwargs: Any,
    ) -> TicketResult:
        """Create a Case (or equivalent) in the external system. Returns ticket id and optional url."""
        ...
