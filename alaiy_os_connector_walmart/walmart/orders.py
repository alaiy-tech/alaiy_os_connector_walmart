# Copyright (c) 2026, Alaiy and contributors
# For license information, please see license.txt
"""
Orders -- GET /v3/orders (list) and GET /v3/orders/{purchaseOrderId} (one).
Confirmed against developer.walmart.com/us-marketplace/docs/get-all-orders
and .../reference/getanorder: 200 = success, pagination via nextCursor,
createdStartDate / status are real query params on the list endpoint.
"""

from alaiy_os_connector_walmart.walmart.client import WalmartClient
from alaiy_os_connector_walmart.walmart.rows import order_to_rows


def get_orders(client=None, created_after=None, created_before=None, status=None,
                sku=None, customer_order_id=None, limit=20, next_cursor=None):
    """Recent orders, normalized to one row per line item (shared row shape).
    `status` is a real Walmart order status: Created / Acknowledged /
    Shipped / Delivered / Cancelled. Only orders from the last 180 days are
    retrievable, and a single query cannot return more than 20000 orders --
    both are Walmart's own limits, not something this client enforces."""
    client = client or WalmartClient()
    params = {"limit": min(limit, 200)}
    if created_after:
        params["createdStartDate"] = created_after
    if created_before:
        params["createdEndDate"] = created_before
    if status:
        params["status"] = status
    if sku:
        params["sku"] = sku
    if customer_order_id:
        params["customerOrderId"] = customer_order_id
    if next_cursor:
        params["nextCursor"] = next_cursor

    data = client.get("orders", params=params)
    order_list = data.get("list", {}).get("elements", {}).get("order", [])
    if isinstance(order_list, dict):
        order_list = [order_list]

    rows = []
    for order in order_list:
        rows.extend(order_to_rows(order))

    meta = data.get("list", {}).get("meta", {})
    return {
        "orders": rows,
        "totalCount": meta.get("totalCount"),
        "nextCursor": meta.get("nextCursor"),
    }


def get_order_by_id(purchase_order_id, client=None):
    client = client or WalmartClient()
    data = client.get(f"orders/{purchase_order_id}")
    order = data.get("order", data)
    return {
        "order_id": order.get("purchaseOrderId"),
        "customer_order_id": order.get("customerOrderId"),
        "order_date": order.get("orderDate"),
        "lines": order_to_rows(order),
        "raw": order,
    }
