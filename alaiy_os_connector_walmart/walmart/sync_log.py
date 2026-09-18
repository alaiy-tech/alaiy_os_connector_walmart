# Copyright (c) 2026, Alaiy and contributors
# For license information, please see license.txt
"""
Walmart Sync Log lifecycle -- same queued -> running -> success/failed
pattern every Alaiy OS connector uses (see
alaiy_os_connector_keepa/keepa/sync_log.py).
"""

import frappe
from frappe.utils import now_datetime


def get_or_create_log(sync_type, trigger, log_name=None):
    if log_name and frappe.db.exists("Walmart Sync Log", log_name):
        return frappe.get_doc("Walmart Sync Log", log_name)

    log = frappe.new_doc("Walmart Sync Log")
    log.sync_type = sync_type
    log.trigger = trigger
    log.status = "queued"
    log.insert(ignore_permissions=True)
    frappe.db.commit()
    return log


def _mark_running(log):
    log.status = "running"
    log.started_at = now_datetime()
    log.save(ignore_permissions=True)
    frappe.db.commit()


def _mark_finished(log, status, items_processed=0, items_created=0, items_updated=0,
                    items_failed=0, error_message=None):
    log.status = status
    log.finished_at = now_datetime()
    log.items_processed = items_processed
    log.items_created = items_created
    log.items_updated = items_updated
    log.items_failed = items_failed
    if error_message:
        log.error_message = error_message[:2000]
    log.save(ignore_permissions=True)
    frappe.db.commit()


def run_logged(sync_type, trigger, log_name, worker):
    """worker(log) must return a dict with items_processed/created/updated/failed."""
    log = get_or_create_log(sync_type, trigger, log_name)
    _mark_running(log)
    try:
        counts = worker(log) or {}
        _mark_finished(log, "success", **counts)
    except Exception:
        _mark_finished(log, "failed", error_message=frappe.get_traceback())
        frappe.log_error(
            title=f"Walmart connector: {sync_type} sync failed",
            message=frappe.get_traceback(),
        )
        raise
