# Copyright (c) 2026, Alaiy and contributors
# For license information, please see license.txt
"""
Sales summary / revenue-by-SKU -- Walmart has no dedicated "sales summary"
endpoint (confirmed against the current Orders API docs), so this is a
service-layer aggregation over GET /v3/orders, walking nextCursor until the
whole date range is consumed. Cancelled lines are excluded from GMV, same as
they would be double-counted revenue otherwise.

Recon Report (financial reconciliation against Walmart's own settlement
figures) is explicitly out of scope for v0 per issue #300's Definition of
Done -- this aggregates operational order data, not settled/reconciled
financials.
"""

import datetime as _dt

from alaiy_os_connector_walmart.walmart.client import WalmartClient
from alaiy_os_connector_walmart.walmart.orders import get_orders

# Walmart's own documented ceilings on GET /v3/orders: only orders from the
# last 180 days are retrievable, and a single query cannot return more than
# 20000 orders. 100 pages of 200 orders each is exactly that ceiling -- not
# an arbitrary safety number.
_PAGE_LIMIT = 200
_MAX_PAGES = 100
_MAX_RANGE_DAYS = 180


class WalmartDateRangeError(Exception):
    """Raised when the requested range exceeds what /v3/orders can retrieve."""


def _validate_range(start_date, end_date):
    start = _dt.datetime.strptime(start_date[:10], "%Y-%m-%d").date()
    today = _dt.date.today()
    if (today - start).days > _MAX_RANGE_DAYS:
        raise WalmartDateRangeError(
            f"start_date {start_date} is more than {_MAX_RANGE_DAYS} days ago -- "
            "Walmart's Orders API only retrieves orders from the last 180 days."
        )
    if end_date:
        end = _dt.datetime.strptime(end_date[:10], "%Y-%m-%d").date()
        if end < start:
            raise WalmartDateRangeError(f"end_date {end_date} is before start_date {start_date}.")


def _all_rows(client, start_date, end_date):
    _validate_range(start_date, end_date)
    rows = []
    cursor = None
    for _ in range(_MAX_PAGES):
        page = get_orders(
            client=client, created_after=start_date, created_before=end_date,
            limit=_PAGE_LIMIT, next_cursor=cursor,
        )
        rows.extend(page["orders"])
        cursor = page.get("nextCursor")
        if not cursor:
            break
    return rows


def get_sales_summary(start_date, end_date, client=None):
    client = client or WalmartClient()
    rows = _all_rows(client, start_date, end_date)
    counted = [r for r in rows if r["status"] != "cancelled"]

    order_ids = {r["order_id"] for r in counted}
    gmv = round(sum(r["revenue"] for r in counted), 2)
    units = sum(r["quantity"] for r in counted)
    order_count = len(order_ids)

    return {
        "start_date": start_date,
        "end_date": end_date,
        "gmv": gmv,
        "units": units,
        "order_count": order_count,
        "avg_order_value": round(gmv / order_count, 2) if order_count else 0,
    }


def get_revenue_by_sku(start_date, end_date, client=None):
    client = client or WalmartClient()
    rows = _all_rows(client, start_date, end_date)
    counted = [r for r in rows if r["status"] != "cancelled"]

    by_sku = {}
    for r in counted:
        sku = r["sku"] or "UNKNOWN"
        entry = by_sku.setdefault(
            sku, {"sku": sku, "product_name": r.get("product_name"), "revenue": 0.0, "units": 0}
        )
        entry["revenue"] += r["revenue"]
        entry["units"] += r["quantity"]

    result = sorted(by_sku.values(), key=lambda e: e["revenue"], reverse=True)
    for entry in result:
        entry["revenue"] = round(entry["revenue"], 2)
    return {"start_date": start_date, "end_date": end_date, "by_sku": result}
