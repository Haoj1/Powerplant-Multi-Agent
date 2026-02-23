"""
Salesforce Case connector for Agent D approve flow.

Auth:
- Preferred: SALESFORCE_DOMAIN + SALESFORCE_CLIENT_ID + SALESFORCE_CLIENT_SECRET + SALESFORCE_USERNAME + SALESFORCE_PASSWORD
  (Password flow, where SALESFORCE_PASSWORD = login password + Security Token)
- Optional: SALESFORCE_DOMAIN + SALESFORCE_ACCESS_TOKEN (use pre-obtained token)
- Optional: SALESFORCE_DOMAIN + SALESFORCE_CLIENT_ID + SALESFORCE_CLIENT_SECRET (Client Credentials Flow, if Run As User is set in Connected App)
"""

import json
from typing import Optional, Any

from ..config import get_settings
from .base import TicketConnector, TicketResult


def _clean_domain(raw: Optional[str]) -> str:
  """Normalize Salesforce domain: strip scheme and trailing slash."""
  if not raw:
    return ""
  d = raw.strip()
  d = d.replace("https://", "").replace("http://", "")
  return d.rstrip("/")


class SalesforceConnector(TicketConnector):
  """Create Salesforce Case via REST API."""

  def __init__(self, domain: str, access_token: str):
    clean = _clean_domain(domain)
    self.domain = clean
    self.access_token = access_token
    self.base_url = f"https://{self.domain}"
    self.api_version = "v58.0"

  @classmethod
  def get_if_configured(cls) -> Optional["SalesforceConnector"]:
    """Return a configured connector if Salesforce env vars are set."""
    s = get_settings()
    domain = _clean_domain(s.salesforce_domain)
    token = (s.salesforce_access_token or "").strip()
    if not domain:
      return None
    # 1) Use pre-configured access_token
    if token:
      return cls(domain=domain, access_token=token)
    # 2) Try Password Flow (USERNAME + PASSWORD with Security Token)
    token = cls._get_token_password_flow(s, domain) or cls._get_token_client_credentials(s, domain)
    if not token:
      return None
    return cls(domain=domain, access_token=token)

  @staticmethod
  def _get_token_password_flow(s, domain: str) -> Optional[str]:
    """OAuth2 username-password flow. Requires username + password (with security token)."""
    if not (s.salesforce_username and s.salesforce_password):
      return None
    try:
      import urllib.request
      import urllib.parse

      data = urllib.parse.urlencode(
        {
          "grant_type": "password",
          "client_id": s.salesforce_client_id or "",
          "client_secret": s.salesforce_client_secret or "",
          "username": s.salesforce_username,
          "password": s.salesforce_password,
        }
      ).encode()
      req = urllib.request.Request(
        f"https://{domain}/services/oauth2/token",
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
  def _get_token_client_credentials(s, domain: str) -> Optional[str]:
    """OAuth2 client credentials flow (if supported by your Connected App)."""
    if not (s.salesforce_client_id and s.salesforce_client_secret):
      return None
    try:
      import urllib.request
      import urllib.parse

      data = urllib.parse.urlencode(
        {
          "grant_type": "client_credentials",
          "client_id": s.salesforce_client_id,
          "client_secret": s.salesforce_client_secret,
        }
      ).encode()
      req = urllib.request.Request(
        f"https://{domain}/services/oauth2/token",
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
    priority: str = "",
    **kwargs: Any,
  ) -> TicketResult:
    """Create a Case in Salesforce. Returns Case Id and URL to the record."""
    try:
      import urllib.request

      payload = {
        "Subject": subject[:255],
        "Description": description[:32000] if description else None,
        "Origin": kwargs.get("origin") or "Web",
        "Status": kwargs.get("status") or "New",
      }
      if priority:
        payload["Priority"] = priority[:40]
      if kwargs.get("type"):
        payload["Type"] = str(kwargs["type"])[:40]
      if kwargs.get("reason"):
        payload["Reason"] = str(kwargs["reason"])[:40]
      if asset_id and not (payload.get("Subject") or "").strip().startswith("["):
        payload["Subject"] = f"[{asset_id}] {payload['Subject']}"[:255]
      # Optional custom fields if your org has them; uncomment & adjust API names as needed:
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

  def query_cases(
    self,
    asset_id: Optional[str] = None,
    keywords: Optional[str] = None,
    created_since: Optional[str] = None,
    limit: int = 20,
  ) -> list:
    """Query Cases and return list of dicts with id, url, subject, status, priority, created_date."""
    import urllib.request
    import urllib.parse
    from datetime import datetime

    def _escape(val: str) -> str:
      return (val or "").replace("\\", "\\\\").replace("'", "\\'")

    def _fmt_dt(ts: str) -> str:
      if not ts:
        return ""
      try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
      except Exception:
        return ts

    where = []
    if asset_id:
      like = _escape(str(asset_id))
      where.append(f"(Subject LIKE '%{like}%' OR Subject LIKE '%[{like}]%')")
    if keywords:
      for kw in str(keywords).split():
        k = _escape(kw.strip())
        if k:
          where.append(f"(Subject LIKE '%{k}%' OR Description LIKE '%{k}%')")
    if created_since:
      sf = _fmt_dt(created_since)
      if sf:
        where.append(f"CreatedDate >= {sf}")

    where_sql = " WHERE " + " AND ".join(where) if where else ""
    soql = (
      "SELECT Id, Subject, Status, Priority, Origin, CreatedDate "
      f"FROM Case{where_sql} ORDER BY CreatedDate DESC LIMIT {max(1, min(limit, 50))}"
    )
    try:
      params = urllib.parse.urlencode({"q": soql})
      url = f"{self.base_url}/services/data/{self.api_version}/query?{params}"
      req = urllib.request.Request(
        url,
        headers={
          "Authorization": f"Bearer {self.access_token}",
          "Content-Type": "application/json",
        },
      )
      with urllib.request.urlopen(req, timeout=15) as resp:
        body = json.loads(resp.read().decode())
    except Exception as e:
      raise RuntimeError(f"Salesforce query failed: {e}") from e

    records = body.get("records", [])
    out = []
    for r in records:
      cid = r.get("Id", "")
      out.append({
        "id": cid,
        "url": f"{self.base_url}/lightning/r/Case/{cid}/view" if cid else None,
        "subject": r.get("Subject", ""),
        "status": r.get("Status", ""),
        "priority": r.get("Priority", ""),
        "created_date": r.get("CreatedDate", ""),
      })
    return out

  def get_case_picklists(self) -> dict:
    """
    Fetch Case object picklist values for Status, Priority, Origin, Type, Reason.
    Returns { status: [...], priority: [...], origin: [...], type: [...], reason: [...] }.
    Falls back to empty list for fields not found or on error.
    """
    import urllib.request

    result = {
      "status": [],
      "priority": [],
      "origin": [],
      "type": [],
      "reason": [],
    }
    try:
      url = f"{self.base_url}/services/data/{self.api_version}/sobjects/Case/describe"
      req = urllib.request.Request(
        url,
        headers={
          "Authorization": f"Bearer {self.access_token}",
          "Content-Type": "application/json",
        },
      )
      with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode())
    except Exception:
      return result

    fields_map = {f.get("name", ""): f for f in data.get("fields", [])}
    for api_name, key in [
      ("Status", "status"),
      ("Priority", "priority"),
      ("Origin", "origin"),
      ("Type", "type"),
      ("Reason", "reason"),
    ]:
      f = fields_map.get(api_name)
      if not f or f.get("type") != "picklist":
        continue
      vals = f.get("picklistValues") or []
      result[key] = [v["value"] for v in vals if v.get("active", True) and v.get("value")]

    return result

