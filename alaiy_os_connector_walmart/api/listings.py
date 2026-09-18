# Copyright (c) 2026, Alaiy and contributors
# For license information, please see license.txt
"""Whitelisted listings tool calls for Ask Alaiy, plus the connector card's
manual refresh / status entry points."""

import frappe

from alaiy_os_connector_walmart.walmart import listings as _listings
from alaiy_os_connector_walmart.walmart.sync_log import get_or_create_log, run_logged


@frappe.whitelist()
def get_listings(status=None, limit=20, next_cursor=None):
    """The real Walmart Items API has no `limit` param -- it returns up to
    200 items per page. `limit` here just slices that page down for callers
    that asked for fewer, per issue #300's tool signature."""
    page = _listings.get_listings(status=status, next_cursor=next_cursor)
    limit = int(limit)
    page["items"] = page["items"][:limit]
    return page


@frappe.whitelist()
def get_listing_by_sku(sku):
    return _listings.get_listing_by_sku(sku)


@frappe.whitelist()
def trigger_listings_refresh():
    """Manually enqueue a listings cache refresh."""
    log = get_or_create_log("listings", "manual")
    frappe.enqueue(
        "alaiy_os_connector_walmart.api.listings.run_listings_refresh",
        queue="long",
        timeout=600,
        trigger="manual",
        log_name=log.name,
    )
    return {"queued": True, "log_name": log.name}


def run_listings_refresh(trigger, log_name):
    def worker(log):
        processed = 0
        cursor = None
        while True:
            page = _listings.get_listings(next_cursor=cursor)
            processed += len(page["items"])
            cursor = page.get("nextCursor")
            if not cursor:
                break
        return {"items_processed": processed}

    run_logged("listings", trigger, log_name, worker)


@frappe.whitelist()
def get_sync_status(sync_type=None):
    """Most recent Walmart Sync Log rows, newest first."""
    filters = {}
    if sync_type and sync_type not in ("categories", "items"):
        filters["sync_type"] = sync_type
    return frappe.get_all(
        "Walmart Sync Log",
        filters=filters,
        fields=[
            "name", "sync_type", "trigger", "status",
            "started_at", "finished_at",
            "items_processed", "items_created", "items_updated", "items_failed",
            "error_message",
        ],
        order_by="started_at desc",
        limit=5,
    )
