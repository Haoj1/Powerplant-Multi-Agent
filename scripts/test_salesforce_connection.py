#!/usr/bin/env python3
"""
Test Salesforce connection using .env credentials.
Run from project root: python scripts/test_salesforce_connection.py

Two flows (both are tried in order):
  1. Client Credentials Flow  = Connected App 里 "Enable Client Credentials Flow"
     → 只用 CLIENT_ID + CLIENT_SECRET，需在 App 里设 Run As User
  2. Username-Password Flow   = 组织设置 "Allow OAuth Username-Password Flows" + App 允许
     → 用 USERNAME + PASSWORD(密码+Security Token) + CLIENT_ID + CLIENT_SECRET

"Enable Authorization Code and Credentials Flow" 是授权码流程（需浏览器登录），脚本无法自动试。
"""
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

# Load .env
try:
    from dotenv import load_dotenv
    load_dotenv(project_root / ".env")
except ImportError:
    pass

def _try_token(url, data, label):
    """Try token endpoint with given form data. Returns (success, token_or_error_msg)."""
    import urllib.request
    import urllib.error
    import json
    try:
        req = urllib.request.Request(url, data=data, method="POST", headers={"Content-Type": "application/x-www-form-urlencoded"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            out = json.loads(resp.read().decode())
            tok = out.get("access_token")
            if tok:
                return True, tok
            return False, f"response had no access_token: {list(out.keys())}"
    except urllib.error.HTTPError as e:
        err_body = e.read().decode() if e.fp else ""
        try:
            err_json = json.loads(err_body)
            return False, f"HTTP {e.code} – {err_json.get('error', '')}: {err_json.get('error_description', err_body[:150])}"
        except Exception:
            return False, f"HTTP {e.code} – {err_body[:200]}"
    except Exception as ex:
        return False, str(ex)

def main():
    print("Testing Salesforce connection...")
    print()

    try:
        from shared_lib.integrations import get_ticket_connector
    except Exception as e:
        print(f"Could not load integrations: {e}")
        return 1

    # Show what's configured (names only)
    from shared_lib.config import get_settings
    s = get_settings()
    have_domain = bool((s.salesforce_domain or "").strip())
    have_token = bool((s.salesforce_access_token or "").strip())
    have_client = bool((s.salesforce_client_id or "").strip() and (s.salesforce_client_secret or "").strip())
    have_user = bool((s.salesforce_username or "").strip() and (s.salesforce_password or "").strip())
    if have_domain:
        print(f"  SALESFORCE_DOMAIN: set ({len(s.salesforce_domain or '')} chars)")
    else:
        print("  SALESFORCE_DOMAIN: not set")
    print(f"  SALESFORCE_ACCESS_TOKEN: {'set' if have_token else 'not set'}")
    print(f"  SALESFORCE_CLIENT_ID + SECRET: {'set' if have_client else 'not set'}")
    print(f"  SALESFORCE_USERNAME + PASSWORD: {'set' if have_user else 'not set'}")
    print()

    import urllib.parse
    import json

    conn = get_ticket_connector()
    token_from_script = None

    if not conn and have_domain and (have_client or have_user):
        domain = (s.salesforce_domain or "").strip().replace("https://", "").replace("http://", "")
        url = f"https://{domain}/services/oauth2/token"
        print("Trying both flows (script will try each and show result):")
        print()

        # [1/2] Enable Client Credentials Flow (Connected App)
        if have_client:
            print("[1/2] Enable Client Credentials Flow (grant_type=client_credentials)")
            data = urllib.parse.urlencode({
                "grant_type": "client_credentials",
                "client_id": s.salesforce_client_id or "",
                "client_secret": s.salesforce_client_secret or "",
            }).encode()
            ok, msg = _try_token(url, data, "Client Credentials")
            if ok:
                print("  -> OK, token obtained.")
                token_from_script = msg
            else:
                print(f"  -> Failed: {msg}")
            print()

        # [2/2] Username-Password Flow (Allow OAuth Username-Password + App 允许)
        if have_user and have_client:
            print("[2/2] Username-Password Flow (grant_type=password)")
            data = urllib.parse.urlencode({
                "grant_type": "password",
                "client_id": s.salesforce_client_id or "",
                "client_secret": s.salesforce_client_secret or "",
                "username": s.salesforce_username or "",
                "password": s.salesforce_password or "",
            }).encode()
            ok, msg = _try_token(url, data, "Password")
            if ok:
                print("  -> OK, token obtained.")
                if not token_from_script:
                    token_from_script = msg
            else:
                print(f"  -> Failed: {msg}")
            print()

    if not conn and not token_from_script:
        print("Salesforce is not configured or both flows failed.")
        print("Set SALESFORCE_DOMAIN and either:")
        print("  - SALESFORCE_ACCESS_TOKEN, or")
        print("  - SALESFORCE_CLIENT_ID + SALESFORCE_CLIENT_SECRET (Client Credentials), or")
        print("  - SALESFORCE_CLIENT_ID + SALESFORCE_CLIENT_SECRET + SALESFORCE_USERNAME + SALESFORCE_PASSWORD")
        return 1

    # Use connector's token or the one we got from script
    access_token = (conn.access_token if conn else None) or token_from_script
    if not access_token:
        return 1

    if token_from_script and not conn:
        print("(Token obtained by script; connector did not init – check get_ticket_connector order.)")
    print("Verifying token with Salesforce API...")

    base_url = f"https://{(s.salesforce_domain or '').strip().replace('https://', '').replace('http://', '')}"
    try:
        import urllib.request
        import urllib.error
        url = f"{base_url}/services/oauth2/userinfo"
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {access_token}"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = resp.read().decode()
            if resp.status == 200:
                print("OK – Connected successfully. Token is valid.")
                # Show which flow provided the token (connector tries Password first, then Client Credentials)
                if have_client and not have_token:
                    token_url = f"{base_url}/services/oauth2/token"
                    pw_ok, _ = _try_token(
                        token_url,
                        urllib.parse.urlencode({
                            "grant_type": "password",
                            "client_id": s.salesforce_client_id or "",
                            "client_secret": s.salesforce_client_secret or "",
                            "username": s.salesforce_username or "",
                            "password": s.salesforce_password or "",
                        }).encode(),
                        "",
                    ) if have_user else (False, None)
                    cc_ok, _ = _try_token(
                        token_url,
                        urllib.parse.urlencode({
                            "grant_type": "client_credentials",
                            "client_id": s.salesforce_client_id or "",
                            "client_secret": s.salesforce_client_secret or "",
                        }).encode(),
                        "",
                    )
                    if pw_ok and not cc_ok:
                        print("(Token was obtained via Password Flow — connector tries Password first.)")
                    elif cc_ok and not pw_ok:
                        print("(Token was obtained via Client Credentials Flow.)")
                    elif pw_ok and cc_ok:
                        print("(Token was obtained via Password Flow — connector tries Password first, then Client Credentials.)")
                    else:
                        print("(Could not re-detect which flow; token was obtained by get_ticket_connector.)")
                return 0
            print(f"Unexpected status {resp.status}: {body[:200]}")
            return 1
    except urllib.error.HTTPError as e:
        print(f"API error: {e.code} {e.reason}")
        try:
            err_body = e.read().decode()
            print(err_body[:400])
        except Exception:
            pass
        return 1
    except Exception as e:
        print(f"Connection failed: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
