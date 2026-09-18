# Copyright (c) 2026, Alaiy and contributors
# For license information, please see license.txt
"""
Row normalization and sales aggregation -- pure functions, no network,
no frappe DB. Run with:
  bench --site <site> run-tests --module alaiy_os_connector_walmart.tests.test_rows_and_sales
"""

import unittest
from unittest.mock import patch

from alaiy_os_connector_walmart.walmart.rows import normalize_status, order_to_rows
from alaiy_os_connector_walmart.walmart import sales


def _order(order_id, order_date, lines):
    return {
        "purchaseOrderId": order_id,
        "orderDate": order_date,
        "orderLines": {"orderLine": lines},
    }


def _line(sku, qty, price, status):
    return {
        "item": {"sku": sku},
        "orderLineQuantity": {"amount": qty},
        "charges": {"charge": [
            {"chargeType": "PRODUCT", "chargeAmount": {"amount": price}},
        ]},
        "orderLineStatuses": {"orderLineStatus": [{"status": status}]},
    }


class TestRows(unittest.TestCase):
    def test_status_normalization(self):
        self.assertEqual(normalize_status("Created"), "pending")
        self.assertEqual(normalize_status("Shipped"), "shipped")
        self.assertEqual(normalize_status("Delivered"), "shipped")
        self.assertEqual(normalize_status("Cancelled"), "cancelled")
        self.assertEqual(normalize_status("SomethingNew"), "pending")

    def test_order_to_rows_shared_shape(self):
        order = _order("PO1", "2026-09-18T10:00:00Z", [_line("SKU1", 2, 25.0, "Shipped")])
        rows = order_to_rows(order)
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["channel"], "walmart")
        self.assertEqual(row["order_id"], "PO1")
        self.assertEqual(row["sku"], "SKU1")
        self.assertEqual(row["quantity"], 2)
        self.assertEqual(row["revenue"], 50.0)
        self.assertEqual(row["status"], "shipped")


class TestSales(unittest.TestCase):
    def test_summary_excludes_cancelled(self):
        rows_page = {
            "orders": [
                {"order_id": "PO1", "sku": "A", "quantity": 1, "revenue": 100.0, "status": "shipped", "created_at": "2026-09-18"},
                {"order_id": "PO2", "sku": "B", "quantity": 1, "revenue": 50.0, "status": "cancelled", "created_at": "2026-09-18"},
            ],
            "nextCursor": None,
        }
        with patch("alaiy_os_connector_walmart.walmart.sales.get_orders", return_value=rows_page), \
             patch("alaiy_os_connector_walmart.walmart.client.WalmartClient") as mock_client:
            summary = sales.get_sales_summary("2026-09-01", "2026-09-18", client=mock_client())
        self.assertEqual(summary["gmv"], 100.0)
        self.assertEqual(summary["units"], 1)
        self.assertEqual(summary["order_count"], 1)
        self.assertEqual(summary["avg_order_value"], 100.0)

    def test_revenue_by_sku_aggregates_and_sorts(self):
        rows_page = {
            "orders": [
                {"order_id": "PO1", "sku": "A", "quantity": 1, "revenue": 10.0, "status": "shipped", "created_at": "2026-09-18"},
                {"order_id": "PO2", "sku": "B", "quantity": 2, "revenue": 40.0, "status": "shipped", "created_at": "2026-09-18"},
                {"order_id": "PO3", "sku": "A", "quantity": 1, "revenue": 10.0, "status": "shipped", "created_at": "2026-09-18"},
            ],
            "nextCursor": None,
        }
        with patch("alaiy_os_connector_walmart.walmart.sales.get_orders", return_value=rows_page), \
             patch("alaiy_os_connector_walmart.walmart.client.WalmartClient") as mock_client:
            result = sales.get_revenue_by_sku("2026-09-01", "2026-09-18", client=mock_client())
        self.assertEqual(result["by_sku"][0]["sku"], "B")
        self.assertEqual(result["by_sku"][0]["revenue"], 40.0)
        self.assertEqual(result["by_sku"][1]["sku"], "A")
        self.assertEqual(result["by_sku"][1]["revenue"], 20.0)
        self.assertEqual(result["by_sku"][1]["units"], 2)


if __name__ == "__main__":
    unittest.main()
