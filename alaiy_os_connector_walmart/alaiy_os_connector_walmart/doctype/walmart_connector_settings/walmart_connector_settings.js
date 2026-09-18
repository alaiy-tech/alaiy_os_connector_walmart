frappe.ui.form.on("Walmart Connector Settings", {
  refresh(frm) {
    frm.page.set_title(__("Walmart Settings"));

    // Mount the shared Alaiy OS connector status card + password reveal.
    alaiy_os.connector_card.mount(frm, "walmart");
    alaiy_os.connector_card.setup_password_reveal(
      frm,
      "walmart_client_secret",
      "walmart",
    );
    alaiy_os.connector_card.setup_password_reveal(
      frm,
      "walmart_access_token",
      "walmart",
    );

    frm.add_custom_button(
      __("Test Connection"),
      () => {
        frappe.call({
          // Go through the registry wrapper (not test_connection directly)
          // so a successful test also flips the "Connector Status" card at
          // the top of this form from "Not configured" to "Connected".
          method: "alaiy_os.api.connectors.test_connector",
          args: { connector_id: "walmart" },
          callback(r) {
            const res = r.message || {};
            frappe.show_alert(
              {
                message:
                  res.message ||
                  (res.success ? __("Connected") : __("Connection failed")),
                indicator: res.success ? "green" : "red",
              },
              res.success ? 5 : 7,
            );
            frm.reload_doc();
          },
        });
      },
      __("Actions"),
    );

    frm.add_custom_button(
      __("Refresh Listings"),
      () => {
        frappe.call({
          method: "alaiy_os_connector_walmart.api.listings.trigger_listings_refresh",
          callback: () =>
            frappe.show_alert(
              { message: __("Listings refresh queued"), indicator: "blue" },
              5,
            ),
        });
      },
      __("Actions"),
    );

    _render_token_status(frm);
  },
});

function _render_token_status(frm) {
  // Test Connection already refreshes the OAuth token and reloads this doc,
  // so the fields are always as fresh as the last real check.
  const expiresAt = frm.doc.walmart_token_expires_at;

  frm.dashboard.clear_headline();

  if (!expiresAt) {
    frm.dashboard.set_headline(
      __('No cached token yet -- click "Test Connection" to fetch one.'),
    );
    return;
  }

  const isExpired = frappe.datetime.now_datetime() > expiresAt;
  const indicator = isExpired ? "orange" : "green";
  const label = isExpired
    ? __("Token expired -- next call will refresh it")
    : __("Token valid until {0}", [frappe.datetime.comment_when(expiresAt)]);

  frm.dashboard.set_headline_alert(
    `<div class="row">
      <div class="col-xs-12">
        <span class="indicator-pill ${indicator}">
          <span>${label}</span>
        </span>
      </div>
    </div>`,
  );
}
