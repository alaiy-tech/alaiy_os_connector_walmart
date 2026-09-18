# Copyright (c) 2026, Alaiy and contributors
# For license information, please see license.txt
"""
Shared row shape so cross-platform Ask Alaiy tools (e.g. "Walmart GMV vs
Amazon GMV this week") work without per-channel branching. Matches the
Amazon connector's column names exactly, per issue #300.
"""

# Walmart order line statuses -> the issue's 3-value normalized set.
_STATUS_MAP = {
    "Created": "pending",
    "Acknowledged": "pending",
    "Shipped": "shipped",
    "Delivered": "shipped",
    "Cancelled": "cancelled",
    "Refund": "cancelled",
}


def normalize_status(walmart_status):
    return _STATUS_MAP.get(walmart_status, "pending")


def order_line_to_row(order, line):
    """One Walmart order line -> one shared-shape row. `order` is the raw
    /v3/orders order object, `line` one entry of its orderLines.orderLine."""
    charges = line.get("charges", {}).get("charge", [])
    if isinstance(charges, dict):
        charges = [charges]
    revenue = sum(
        float(c.get("chargeAmount", {}).get("amount", 0) or 0)
        for c in charges
        if c.get("chargeType") == "PRODUCT"
    )

    order_line_status = ""
    status_entries = line.get("orderLineStatuses", {}).get("orderLineStatus", [])
    if isinstance(status_entries, dict):
        status_entries = [status_entries]
    if status_entries:
        order_line_status = status_entries[-1].get("status", "")

    qty = line.get("orderLineQuantity", {})

    return {
        "channel": "walmart",
        "order_id": order.get("purchaseOrderId"),
        "sku": line.get("item", {}).get("sku"),
        "product_name": line.get("item", {}).get("productName"),
        "line_number": line.get("lineNumber"),
        "quantity": int(qty.get("amount", 0) or 0),
        "revenue": round(revenue, 2),
        "status": normalize_status(order_line_status),
        "created_at": order.get("orderDate"),
    }


def order_to_rows(order):
    """Every line item on one order -> a list of shared-shape rows."""
    lines = order.get("orderLines", {}).get("orderLine", [])
    if isinstance(lines, dict):
        lines = [lines]
    return [order_line_to_row(order, line) for line in lines]
