# Copyright (c) 2026, Alaiy and contributors
# For license information, please see license.txt
"""
Listings -- GET /v3/items (all SKUs) and GET /v3/items/{sku} (one item).
Confirmed against the real Items API OpenAPI spec (getAllItems / getAnItem):
200 = success, response items are under `itemResponse` (lowercase), fixed
page size of up to 200 per call, pagination via `nextCursor` only -- there is
no `limit` query param on this endpoint (that only exists on the separate
/v3/items/catalog/search endpoint). Status filter is `publishedStatus`
(INPROGRESS / PUBLISHED / UNPUBLISHED), a submission-pipeline state distinct
from `lifecycleStatus` (item's own lifecycle, e.g. ACTIVE) which the response
also carries but which is not a valid filter param.
"""

from alaiy_os_connector_walmart.walmart.client import WalmartClient


def get_listings(client=None, status=None, next_cursor=None):
    """All SKUs, optionally filtered by published status
    (INPROGRESS / PUBLISHED / UNPUBLISHED). Caller pages via the returned
    nextCursor -- up to 200 items per call, fixed by the API."""
    client = client or WalmartClient()
    params = {}
    if status:
        params["publishedStatus"] = status
    if next_cursor:
        params["nextCursor"] = next_cursor

    data = client.get("items", params=params)
    items = data.get("itemResponse", [])
    return {
        "items": [_item_row(i) for i in items],
        "totalItems": data.get("totalItems"),
        "nextCursor": data.get("nextCursor"),
    }


def get_listing_by_sku(sku, client=None):
    client = client or WalmartClient()
    data = client.get(f"items/{sku}")
    return _item_row(data)


def _item_row(item):
    price = item.get("price", {}) or {}
    unpublished_reasons = (item.get("unpublishedReasons") or {}).get("reason") or []
    if isinstance(unpublished_reasons, str):
        unpublished_reasons = [unpublished_reasons]
    return {
        "sku": item.get("sku"),
        "wpid": item.get("wpid"),
        "product_name": item.get("productName"),
        "product_type": item.get("productType"),
        "gtin": item.get("gtin"),
        "upc": item.get("upc"),
        "status": item.get("lifecycleStatus"),
        "published_status": item.get("publishedStatus"),
        # Why an UNPUBLISHED item isn't live -- empty for anything else.
        # This is the field that makes "list unpublished listings" actually
        # actionable instead of just a status label.
        "unpublished_reasons": unpublished_reasons,
        "price": price.get("amount"),
        "currency": price.get("currency"),
    }
