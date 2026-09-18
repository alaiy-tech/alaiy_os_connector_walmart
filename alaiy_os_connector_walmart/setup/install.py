# Copyright (c) 2026, Alaiy and contributors
# For license information, please see license.txt
"""
Install / migrate plumbing shared by every Alaiy OS connector:

  after_install            -> one-time cleanup on `bench install-app`
  sync_connector_registry  -> (re)register in OS Connector Registry (every migrate)
"""

import frappe


def after_install():
    """
    Called once after `bench install-app`. Clear any stale encrypted Password
    field that may have been written under a different site encryption key
    (e.g. from a prior failed install), which otherwise surfaces as a
    'Failed to decrypt key' error on first load.
    """
    frappe.db.set_single_value("Walmart Connector Settings", "walmart_client_secret", "")
    frappe.db.set_single_value("Walmart Connector Settings", "walmart_access_token", "")
    frappe.db.commit()


def sync_connector_registry():
    """
    Register or update this connector's row in alaiy_os's OS Connector Registry.
    Called from hooks.py -> after_migrate on every bench migrate. Idempotent.
    """
    _fix_settings_as_single()

    if not frappe.db.exists("DocType", "OS Connector Registry"):
        return

    from alaiy_os_connector_walmart.connector_meta import connector_meta

    connector_id = connector_meta["connector_id"]

    if frappe.db.exists("OS Connector Registry", connector_id):
        doc = frappe.get_doc("OS Connector Registry", connector_id)
    else:
        doc = frappe.new_doc("OS Connector Registry")

    # Fields owned by the running system, never overwritten from static meta.
    RUNTIME_FIELDS = {"connection_status", "last_tested_at"}

    if doc.is_new():
        for key, val in connector_meta.items():
            if hasattr(doc, key):
                doc.set(key, val)
        doc.insert(ignore_permissions=True)
    else:
        for key, val in connector_meta.items():
            if key not in RUNTIME_FIELDS and hasattr(doc, key):
                doc.set(key, val)
        doc.save(ignore_permissions=True)

    frappe.db.commit()
    _update_alaiy_os_sidebar()


def _update_alaiy_os_sidebar():
    """
    Re-run alaiy_os's workspace/sidebar provisioning so this connector's Logs
    link and Connectors entry (settings button + card) appear right after it
    registers, instead of waiting for the next full bench migrate.
    """
    try:
        from alaiy_os.setup.install import (
            create_or_update_workspace_sidebar,
            create_or_update_os_settings_workspace,
            create_or_update_os_settings_workspace_sidebar,
        )
        create_or_update_workspace_sidebar()
        create_or_update_os_settings_workspace()
        create_or_update_os_settings_workspace_sidebar()
        frappe.db.commit()
    except Exception:
        frappe.log_error(
            title="Walmart connector: sidebar update failed",
            message=frappe.get_traceback(),
        )


def _fix_settings_as_single():
    """
    Force issingle=1 on the settings doctype. Frappe does not auto-convert an
    existing DocType from table-based to Single via bench migrate, so patch it
    directly every deploy.
    """
    frappe.db.sql(
        "UPDATE `tabDocType` SET issingle=1 "
        "WHERE name='Walmart Connector Settings' AND issingle=0"
    )
    frappe.db.commit()
