# External API Configuration (Salesforce, etc.)

When Agent D approves a review, you can optionally create a Salesforce Case to push the ticket to an external system. This document explains how to configure it.

---

## Can Free Users Create Connected Apps?

**Yes.** Common scenarios:

- **Developer Edition**: Free signup, supports API, Connected App, full Setup menu. Best for personal development; recommended for creating Connected Apps.
- **Trial**: Usually supports API and Connected App, similar to production.
- **Minimal free (e.g. Salesforce CRM Free)**: May lack Setup or API. If you don't see "App Manager", register a [Developer Edition](https://developer.salesforce.com/signup) and follow the steps below.

Register Developer Edition: [developer.salesforce.com/signup](https://developer.salesforce.com/signup). Fill in email, name, etc., then log in to use Setup and App Manager.

---

## How to Create a Connected App (Step by Step)

1. **Go to Setup**  
   After logging in, click the **gear icon** (top right) → **Setup**.

2. **Open App Manager**  
   In the left **Quick Find** box, type **App Manager**, press Enter.

3. **New Connected App**  
   Click **New Connected App** (top right).

4. **Basic Info**  
   - **Connected App Name**: Required, e.g. `Agent D` or `My Ticket App`.  
   - **API Name**: Auto-generated, usually leave as-is.  
   - **Contact Email**: Your email.  
   - **Description**, **Logo**: Optional.

5. **Enable OAuth**  
   Check **Enable OAuth Settings**. Then:  
   - **Callback URL**: Required; use `https://localhost` or `https://login.salesforce.com` (this project's password flow does not rely on callback).  
   - **Selected OAuth Scopes**: Add at least:  
     - **Access and manage your data (api)**  
     - **Perform requests at any time (refresh_token, offline_access)**  
   Click **Add** to move them to the right.

6. **Other Options**  
   - **Require Secret for Web Server Flow**: Keep checked (generates Consumer Secret).  
   - **Require Secret for Refresh Token Flow**: Optional.  
   - Leave other defaults.

7. **Save and Wait**  
   Click **Save**, then **Continue**.  
   Salesforce may take **2–10 minutes** before the app is active. You need Consumer Key/Secret after that.

8. **Get Consumer Key and Consumer Secret**  
   - In **App Manager**, find your app, click **▼** → **Manage**.  
   - In **API (Enable OAuth Settings)** you'll see **Consumer Key** (`SALESFORCE_CLIENT_ID`).  
   - **Consumer Secret** shows as *****; click **Click to reveal** and copy (`SALESFORCE_CLIENT_SECRET`).  
   - If no **Manage**, click the app name to open details.

9. **Configure Project**  
   Add Consumer Key, Consumer Secret, domain, username, and password+Security Token to `.env` as in "Method B" below.

---

## Configuration Methods

Choose one: **Method A** is fastest (domain + token only); **Method B** is better for long-term use (Connected App auto-refreshes token).

---

### Method A: Access Token Only (Fastest)

**Step 1: Get your Salesforce domain**

1. Log in to Salesforce (e.g. `https://xxx.my.salesforce.com`).
2. The domain is the part after `https://` and before the first `/`.
3. Example: `https://mycompany.my.salesforce.com/lightning/...` → domain: `mycompany.my.salesforce.com`.
4. In project root `.env`, add:
   ```env
   SALESFORCE_DOMAIN=mycompany.my.salesforce.com
   ```

**Step 2: Get Security Token**

1. Log in → top right **avatar** (or gear) → **Settings**.
2. Left menu: **Personal** → **Reset My Security Token**.
3. Click **Reset My Security Token**; Salesforce emails the new token.
4. Copy the token (alphanumeric, no spaces).

**Step 3: Exchange for Access Token**

Use curl or Postman:

```bash
curl -X POST "https://YOUR_DOMAIN/services/oauth2/token" \
  -d "grant_type=password" \
  -d "client_id=YOUR_CONSUMER_KEY" \
  -d "client_secret=YOUR_CONSUMER_SECRET" \
  -d "username=YOUR_EMAIL" \
  -d "password=YOUR_PASSWORD_YOUR_SECURITY_TOKEN"
```

If you don't have a Connected App yet, complete Method B steps 1–2 first. The response JSON contains `access_token`.

**Step 4: Add to .env**

```env
SALESFORCE_DOMAIN=mycompany.my.salesforce.com
SALESFORCE_ACCESS_TOKEN=paste_your_access_token_here
```

Restart Agent D. In Review Queue, approve a request and check "Create Salesforce Case"; a Case should be created in Salesforce.

---

### Method B: Connected App + Username/Password (Recommended)

**Step 1: Create Connected App**

1. Log in → **Setup** → **App Manager** → **New Connected App**.
2. **Connected App Name**: e.g. `Agent D Ticket`.
3. **API Name**: Auto-generated.
4. Check **Enable OAuth Settings**.
5. **Callback URL**: `https://localhost`.
6. **Selected OAuth Scopes**: Add `Access and manage your data (api)` and `Perform requests at any time (refresh_token, offline_access)`.
7. Click **Save**; wait 2–10 minutes.

**Step 2: Get Consumer Key and Consumer Secret**

1. In App Manager, find your app → **Manage**.
2. Copy **Consumer Key** and **Consumer Secret** (click **Click to reveal** for Secret).

**Step 3: Get Security Token (if needed)**

Same as Method A Step 2: **Settings** → **Personal** → **Reset My Security Token**.

**Step 4: Fill .env**

```env
SALESFORCE_DOMAIN=mycompany.my.salesforce.com
SALESFORCE_CLIENT_ID=your_consumer_key
SALESFORCE_CLIENT_SECRET=your_consumer_secret
SALESFORCE_USERNAME=your_login_email
SALESFORCE_PASSWORD=your_password_your_security_token
```

Note: `SALESFORCE_PASSWORD` = login password + Security Token concatenated (no space). Example: password `Abc123`, token `xyz789` → `Abc123xyz789`.

Do **not** set `SALESFORCE_ACCESS_TOKEN`; the app will obtain it automatically.

---

### Method C: Client Credentials Flow

If **Enable Client Credentials Flow** is checked in the Connected App, you only need domain + Consumer Key + Consumer Secret.

**Important**: You must set **Run As User** in the Connected App. Edit the app → **Client Credentials Flow** → set **Run As User** → Save. Otherwise you'll get `no client credentials user enabled`.

```env
SALESFORCE_DOMAIN=yourcompany.my.salesforce.com
SALESFORCE_CLIENT_ID=your_consumer_key
SALESFORCE_CLIENT_SECRET=your_consumer_secret
```

Leave `SALESFORCE_ACCESS_TOKEN`, `SALESFORCE_USERNAME`, `SALESFORCE_PASSWORD` unset.

---

### Verify Configuration

1. Ensure `.env` has one of:
   - Method A: `SALESFORCE_DOMAIN` + `SALESFORCE_ACCESS_TOKEN`
   - Method B: `SALESFORCE_DOMAIN` + `SALESFORCE_CLIENT_ID` + `SALESFORCE_CLIENT_SECRET` + `SALESFORCE_USERNAME` + `SALESFORCE_PASSWORD`
2. Restart Agent D.
3. In Review Queue, approve a record, check "Create Salesforce Case", submit.
4. In Salesforce **Cases** list, you should see the new Case; local `tickets` table will have a row.

If errors occur: ensure domain has no `https://`, password includes Security Token, and Connected App has had time to activate.

---

### Flow Comparison

| Connected App Setting | Meaning | Script |
|-----------------------|---------|--------|
| **Enable Client Credentials Flow** | Use Client ID + Secret only; requires Run As User. | `grant_type=client_credentials` |
| **Enable Authorization Code and Credentials Flow** | Browser login flow; script cannot test. | N/A |

**Username-Password Flow** requires org setting "Allow OAuth Username-Password Flows" + App enabled; script tries `grant_type=password`.

Run `python scripts/test_salesforce_connection.py` to test both flows.

---

### Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `no client credentials user enabled` | Client Credentials on but no Run As User | Edit App → Client Credentials Flow → set Run As User |
| `authentication failure` (Password) | Username/password failed | ① PASSWORD = password + Security Token (no space) ② App allows Username-Password ③ USERNAME = full email |
| `invalid_client` | Wrong Client ID or Secret | Verify Consumer Key / Consumer Secret |

---

## 1. Config Variables (.env)

| Variable | Description |
|----------|-------------|
| `SALESFORCE_DOMAIN` | Instance domain (no https://) |
| `SALESFORCE_ACCESS_TOKEN` | Pre-obtained token (for quick setup) |
| `SALESFORCE_CLIENT_ID` | Connected App Consumer Key |
| `SALESFORCE_CLIENT_SECRET` | Connected App Consumer Secret |
| `SALESFORCE_USERNAME` | Username (Password flow) |
| `SALESFORCE_PASSWORD` | Password + Security Token (Password flow) |

- **Minimum**: `SALESFORCE_DOMAIN` + `SALESFORCE_ACCESS_TOKEN` to create Cases on approve.
- **If not configured**: "Create Salesforce Case" will not call Salesforce; only local approval is recorded.

---

## 2. Getting Access Token (Quick Setup)

1. Log in → **Settings** → **Personal** → **Reset My Security Token**.
2. Use Postman or curl with OAuth2 password flow; get `access_token` from response.
3. Put it in `.env` as `SALESFORCE_ACCESS_TOKEN`.

---

## 3. Connected App (Production)

1. **Setup** → **App Manager** → **New Connected App**.
2. Check **Enable OAuth Settings**.
3. **Callback URL**: `https://localhost` or your app callback.
4. **OAuth Scopes**: At least `Access and manage your data (api)`, `Perform requests at any time (refresh_token, offline_access)`.
5. Save; get **Consumer Key** and **Consumer Secret**.
6. For **Password flow**: Set `SALESFORCE_USERNAME`, `SALESFORCE_PASSWORD` (password + Security Token). Leave `SALESFORCE_ACCESS_TOKEN` unset for auto token refresh.

---

## 4. Behavior

- **Frontend**: Review Queue approve modal has "Create Salesforce Case" checkbox; when checked, request includes `create_salesforce_case: true`.
- **Backend**: Only when `create_salesforce_case=True` and `get_ticket_connector()` returns a connector will Salesforce be called.
- **Case content**: Subject, Description from diagnosis root_cause, asset_id, plant_id, and approval notes. On success, a row is inserted into `tickets` and optionally RAG index.

---

## 5. Extending to Other Ticket Systems

To integrate Jira or a custom ticket API:

1. Add a module under `shared_lib/integrations/` implementing `TicketConnector` (see `base.py` `create_case`).
2. Add config in `shared_lib/config.py`.
3. In `shared_lib/integrations/__init__.py` `get_ticket_connector()`, return the appropriate connector.

Agent D's approve flow only depends on `get_ticket_connector()` and `create_case(...)`; it does not care which system is used.
