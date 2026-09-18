# Copyright (c) 2026, Alaiy and contributors
# For license information, please see license.txt
"""Whitelisted orders tool calls for Ask Alaiy."""

import frappe

from alaiy_os_connector_walmart.walmart import orders as _orders


@frappe.whitelist()
def get_orders(created_after=None, status=None, limit=20, next_cursor=None):
    return _orders.get_orders(
        created_after=created_after, status=status, limit=int(limit), next_cursor=next_cursor,
    )


@frappe.whitelist()
def get_order_by_id(purchase_order_id):
    return _orders.get_order_by_id(purchase_order_id)
