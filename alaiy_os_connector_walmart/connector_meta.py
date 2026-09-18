# Copyright (c) 2026, Alaiy and contributors
# For license information, please see license.txt
"""
Single source of truth for this connector's registration metadata.
Consumed by setup/install.py -> upserted into alaiy_os's OS Connector Registry.
"""

connector_meta = {
    "connector_id": "walmart",
    "connector_name": "Walmart Marketplace",
    "connector_app": "alaiy_os_connector_walmart",
    "connector_type": "channel",
    "description": "Walmart Marketplace listings, orders and sales via the Walmart Marketplace API.",
    "icon": "shopping-cart",
    "icon_url": "",
    "settings_doctype": "Walmart Connector Settings",
    "test_method": "alaiy_os_connector_walmart.api.test_connection.test_connection",
    # Walmart tools are on-demand (Ask Alaiy queries live data, no background
    # pull/push engine for v0) -- both registry slots point at the same
    # listings refresh so the connector card has something to trigger.
    "sync_categories_method": "alaiy_os_connector_walmart.api.listings.trigger_listings_refresh",
    "sync_items_method": "alaiy_os_connector_walmart.api.listings.trigger_listings_refresh",
    "sync_status_method": "alaiy_os_connector_walmart.api.listings.get_sync_status",
    "sync_categories_label": "Refresh Listings",
    "sync_items_label": "Refresh Listings",
    "is_enabled": 0,
    "connection_status": "untested",
}
