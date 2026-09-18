# Copyright (c) 2026, Alaiy and contributors
# For license information, please see license.txt
"""
Reachability check for the saved credentials. Wired into the registry via
connector_meta["test_method"] and called by the "Test Connection" button.
Always returns {"success": bool, "message": str} -- never raises to the caller.
"""

import frappe


@frappe.whitelist()
def test_connection():
    from alaiy_os_connector_walmart.walmart.client import WalmartAPIError, WalmartClient

    try:
        client = WalmartClient()
    except RuntimeError as e:
        return {"success": False, "message": str(e)}

    try:
        # The token endpoint itself is the real auth check -- it rejects a
        # bad Client ID / Secret with its own 401/403 and costs nothing on
        # the data APIs, unlike calling GET /v3/items just to see if it 200s.
        client._refresh_token()
        return {"success": True, "message": "Connected successfully."}
    except WalmartAPIError as e:
        msg = str(e)
        if "401" in msg:
            return {"success": False, "message": "Authentication failed -- check your Client ID / Secret."}
        if "403" in msg:
            return {"success": False, "message": "Access forbidden -- verify your Walmart API permissions."}
        return {"success": False, "message": msg[:200]}
    except Exception as e:
        return {"success": False, "message": str(e)[:200]}
