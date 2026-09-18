# Copyright (c) 2026, Alaiy and contributors
# For license information, please see license.txt
"""Whitelisted sales tool calls for Ask Alaiy."""

import frappe

from alaiy_os_connector_walmart.walmart import sales as _sales


@frappe.whitelist()
def get_sales_summary(start_date, end_date):
    return _sales.get_sales_summary(start_date, end_date)


@frappe.whitelist()
def get_revenue_by_sku(start_date, end_date):
    return _sales.get_revenue_by_sku(start_date, end_date)
