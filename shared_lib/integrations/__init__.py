"""
External API integrations (Salesforce, etc.).
Use get_ticket_connector() to obtain the configured connector, if any.
"""

from typing import Optional, Dict, Any

from .base import TicketConnector, TicketResult


def get_ticket_connector() -> Optional[TicketConnector]:
    """Return the configured ticket connector (e.g. Salesforce), or None if not configured."""
    try:
        from .salesforce import SalesforceConnector
        return SalesforceConnector.get_if_configured()
    except Exception:
        return None


__all__ = ["TicketConnector", "TicketResult", "get_ticket_connector"]
