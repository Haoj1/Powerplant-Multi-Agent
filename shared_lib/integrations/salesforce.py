"""
Salesforce Case connector for Agent D approve flow.
Uses REST API: POST /services/data/v58.0/sobjects/Case.
Auth: access token (SALESFORCE_ACCESS_TOKEN) or OAuth2 client credentials / password flow.
"""

import json
from typing import Optional, Any

from ..config import get_settings
from .base import TicketConnector, TicketResult


class SalesforceConnector(TicketConnector):
    """Create Salesforce Case via REST API."""

    def __init__(self, domain: str, access_token: str):
        self.domain = domain.rstrip("/").replace("https://", "").replace("http://", "")
        self.access_token = access_token
        self.base_url = f"https://{self.domain}"
        self.api_version = "v58.0"

    @classmethod
    def get_if_configured(cls) -> Optional["SalesforceConnector"]:
        """Return a configured connector if Salesforce env vars are set."""
        s = get_settings()
        domain = (s.salesforce_domain or "").strip()
        token = (s.salesforce_access_token or "").strip()
        if not domain:
            return None
        if token:
            return cls(domain=domain, access_token=token)
        # Optional: obtain token via client credentials or password flow
        token = cls._get_token_password_flow(s) or cls._get_token_client_credentials(s)
        if not token:
            return None
        return cls(domain=domain, access_token=token)

    @staticmethod
    def _get_token_password_flow(s) -> Optional[str]:
        """OAuth2 username-password flow. Requires username + password (with security token)."""
        if not (s.salesforce_username and s.salesforce_password):
            return None
        try:
            import urllib.request
            import urllib.parse
            data = urllib.parse.urlencode({
                "grant_type": "password",
                "client_id": s.salesforce_client_id or "",
                "client_secret": s.salesforce_client_secret or "",
                "username": s.salesforce_username,
                "password": s.salesforce_password,
            }).encode()
            req = urllib.request.Request(
                f"https://{s.salesforce_domain}/services/oauth2/token",
                data=data,
                method="POST",
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                body = json.loads(resp.read().decode())
                return body.get("access_token")
        except Exception:
            return None

    @staticmethod
    def _get_token_client_credentials(s) -> Optional[str]:
        """OAuth2 client credentials flow (if supported by your Connected App)."""
        if not (s.salesforce_client_id and s.salesforce_client_secret):
            return None
        try:
            import urllib.request
            import urllib.parse
            data = urllib.parse.urlencode({
                "grant_type": "client_credentials",
                "client_id": s.salesforce_client_id,
                "client_secret": s.salesforce_client_secret,
            }).encode()
            req = urllib.request.Request(
                f"https://{s.salesforce_domain}/services/oauth2/token",
                data=data,
                method="POST",
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                body = json.loads(resp.read().decode())
                return body.get("access_token")
        except Exception:
            return None

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
        """Create a Case in Salesforce. Returns Case Id and URL to the record."""
        try:
            import urllib.request
            payload = {
                "Subject": subject[:255],
                "Description": description[:32000] if description else None,
                "Origin": "Agent D Review",
                "Status": "New",
            }
            if asset_id:
                payload["Subject"] = f"[{asset_id}] {payload['Subject']}"[:255]
            # Optional custom fields if your org has them:
            # payload["Asset_Id__c"] = asset_id
            # payload["Plant_Id__c"] = plant_id
            # payload["Root_Cause__c"] = root_cause
            body = json.dumps({k: v for k, v in payload.items() if v is not None}).encode()
            url = f"{self.base_url}/services/data/{self.api_version}/sobjects/Case"
            req = urllib.request.Request(
                url,
                data=body,
                method="POST",
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/json",
                },
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                result = json.loads(resp.read().decode())
                case_id = result.get("id", "")
                case_url = f"{self.base_url}/lightning/r/Case/{case_id}/view" if case_id else None
                return TicketResult(
                    ticket_id=case_id,
                    url=case_url,
                    title=subject,
                    body=description,
                )
        except Exception as e:
            raise RuntimeError(f"Salesforce create Case failed: {e}") from e
