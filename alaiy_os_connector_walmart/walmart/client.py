# Copyright (c) 2026, Alaiy and contributors
# For license information, please see license.txt
"""
HTTP client for the Walmart Marketplace API.

Auth is OAuth 2.0 client credentials (POST /v3/token, Basic auth with
client_id:client_secret) -- access token TTL is 15 minutes per Walmart's own
Token API docs. Cached on Walmart Connector Settings so it survives past one
client instance, refreshed 60s before expiry rather than on a hard TTL check
to absorb request latency.

Every call after auth needs WM_SEC.ACCESS_TOKEN / WM_QOS.CORRELATION_ID /
WM_SVC.NAME / Accept headers; WM_CONSUMER.CHANNEL.TYPE is only sent when the
seller has been issued one (confirmed optional -- omitted entirely when blank
rather than sent empty, since Walmart validates it as a real registered GUID
when present).
"""

import uuid

import frappe
import requests

API_BASE = "https://marketplace.walmartapis.com/v3"
TOKEN_URL = f"{API_BASE}/token"

_MAX_ATTEMPTS = 4
_BACKOFF_BASE_SECONDS = 2
_MAX_WAIT_SECONDS = 30
_TOKEN_REFRESH_SKEW_SECONDS = 60


class WalmartAPIError(Exception):
    """Raised when the API returns an error the caller cannot retry past."""


class WalmartClient:
    def __init__(self, workspace_client_id=None, workspace_client_secret=None):
        settings = frappe.get_single("Walmart Connector Settings")
        self.client_id = (
            workspace_client_id
            or settings.walmart_client_id
            or frappe.conf.get("walmart_client_id")
        )
        self.client_secret = (
            workspace_client_secret
            or (settings.get_password("walmart_client_secret") if settings.walmart_client_secret else None)
            or frappe.conf.get("walmart_client_secret")
        )
        if not self.client_id or not self.client_secret:
            raise RuntimeError(
                "Walmart connector is not configured (no Client ID / Secret on "
                "Walmart Connector Settings and no pooled walmart_client_id / "
                "walmart_client_secret in site_config.json)."
            )
        self.channel_type = settings.walmart_channel_type or frappe.conf.get("walmart_channel_type")
        self._settings = settings
        self._session = requests.Session()

    # ------------------------------------------------------------------
    # OAuth token cache
    # ------------------------------------------------------------------
    def _access_token(self):
        import datetime as _dt

        expires_at = self._settings.walmart_token_expires_at
        if expires_at:
            skew = _dt.timedelta(seconds=_TOKEN_REFRESH_SKEW_SECONDS)
            if frappe.utils.now_datetime() < (expires_at - skew):
                cached = self._settings.get_password("walmart_access_token")
                if cached:
                    return cached
        return self._refresh_token()

    def _refresh_token(self):
        resp = self._session.post(
            TOKEN_URL,
            auth=(self.client_id, self.client_secret),
            data={"grant_type": "client_credentials"},
            headers={
                "Accept": "application/json",
                "WM_SVC.NAME": "Walmart Marketplace",
                "WM_QOS.CORRELATION_ID": str(uuid.uuid4()),
            },
            timeout=30,
        )
        if resp.status_code >= 400:
            raise WalmartAPIError(f"Token request failed: HTTP {resp.status_code}: {resp.text[:500]}")
        data = resp.json()
        token = data.get("access_token")
        expires_in = data.get("expires_in", 900)
        if not token:
            raise WalmartAPIError(f"Token response missing access_token: {data}")

        expires_at = frappe.utils.add_to_date(frappe.utils.now_datetime(), seconds=expires_in)
        frappe.db.set_value(
            "Walmart Connector Settings",
            None,
            {"walmart_access_token": token, "walmart_token_expires_at": expires_at},
        )
        frappe.db.commit()
        self._settings.reload()
        return token

    def _headers(self):
        headers = {
            "WM_SEC.ACCESS_TOKEN": self._access_token(),
            "WM_QOS.CORRELATION_ID": str(uuid.uuid4()),
            "WM_SVC.NAME": "Walmart Marketplace",
            "Accept": "application/json",
        }
        if self.channel_type:
            headers["WM_CONSUMER.CHANNEL.TYPE"] = self.channel_type
        return headers

    # ------------------------------------------------------------------
    # Request plumbing
    # ------------------------------------------------------------------
    def _request(self, method, path, params=None, json_body=None, timeout=30):
        url = f"{API_BASE}/{path.lstrip('/')}"
        last_error = None

        for attempt in range(_MAX_ATTEMPTS):
            if attempt:
                import time

                time.sleep(min(_BACKOFF_BASE_SECONDS**attempt, _MAX_WAIT_SECONDS))
            try:
                resp = self._session.request(
                    method, url, headers=self._headers(), params=params, json=json_body, timeout=timeout,
                )
            except requests.exceptions.RequestException as e:
                last_error = str(e)
                continue

            if resp.status_code == 401 and attempt == 0:
                # Token may have been invalidated server-side before our
                # cached expiry -- force one refresh and retry once.
                self._refresh_token()
                continue
            if resp.status_code == 429:
                last_error = "Rate limited (429)"
                continue
            if resp.status_code >= 500:
                last_error = f"HTTP {resp.status_code}: {resp.text[:200]}"
                continue
            if resp.status_code >= 400:
                raise WalmartAPIError(f"HTTP {resp.status_code}: {resp.text[:500]}")

            if not resp.content:
                return {}
            try:
                return resp.json()
            except ValueError:
                raise WalmartAPIError(f"Response was not JSON: {resp.text[:200]}")

        raise WalmartAPIError(f"Request to {path} failed after {_MAX_ATTEMPTS} attempts: {last_error}")

    def get(self, path, params=None, timeout=30):
        return self._request("GET", path, params=params, timeout=timeout)

    def post(self, path, json_body=None, timeout=30):
        return self._request("POST", path, json_body=json_body, timeout=timeout)
