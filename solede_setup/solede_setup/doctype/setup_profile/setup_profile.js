// Copyright (c) 2025, Solede SA and contributors
// For license information, please see license.txt

frappe.ui.form.on("Setup Profile", {
	refresh: function (frm) {
		// Mostra/nascondi bottone cleanup in base alla company selezionata
		frm.set_df_property("cleanup_all", "hidden", !frm.doc.cleanup_company);
	},

	cleanup_company: function (frm) {
		frm.trigger("refresh");
	},

	cleanup_all: function (frm) {
		if (!frm.doc.cleanup_company) {
			frappe.msgprint(__("Please select a Company first"));
			return;
		}

		// Dialog di conferma con opzioni
		let d = new frappe.ui.Dialog({
			title: __("Cleanup All Data"),
			fields: [
				{
					fieldtype: "HTML",
					options: `<div class="alert alert-danger">
						<strong>${__("Warning!")}</strong><br>
						${__("This will permanently delete all data for company")} <strong>${frm.doc.cleanup_company}</strong>:
						<ul>
							<li>GL Entry</li>
							<li>Stock Ledger Entry</li>
							<li>Cost Centers</li>
							<li>Warehouses</li>
							<li>Tax Templates (Sales, Purchase, Item)</li>
						</ul>
						${__("This action cannot be undone!")}
					</div>`,
				},
				{
					fieldtype: "Check",
					fieldname: "also_cleanup_global",
					label: __("Also cleanup global data (Item Groups, Territories, Customer Groups, Supplier Groups, Mode of Payment, Payment Terms)"),
				},
				{
					fieldtype: "Section Break",
				},
				{
					fieldtype: "Data",
					fieldname: "confirm_text",
					label: __('Type "DELETE" to confirm'),
					reqd: 1,
				},
			],
			primary_action_label: __("Delete All"),
			primary_action: function () {
				let values = d.get_values();
				if (values.confirm_text !== "DELETE") {
					frappe.msgprint(__('Please type "DELETE" to confirm'));
					return;
				}

				d.hide();

				frappe.call({
					method: "solede_setup.solede_setup.doctype.setup_profile.setup_profile.cleanup_all_data",
					args: { company: frm.doc.cleanup_company },
					freeze: true,
					freeze_message: __("Deleting company data..."),
					callback: function (r) {
						if (r.message) {
							let msg = __("Company data cleanup completed") + ":<br><br>";
							for (let [doctype, count] of Object.entries(r.message.deleted)) {
								msg += `<strong>${doctype}</strong>: ${count}<br>`;
							}

							if (values.also_cleanup_global) {
								// Also cleanup global data
								frappe.call({
									method: "solede_setup.solede_setup.doctype.setup_profile.setup_profile.cleanup_global_data",
									freeze: true,
									freeze_message: __("Deleting global data..."),
									callback: function (r2) {
										if (r2.message) {
											msg += "<br>" + __("Global data cleanup completed") + ":<br><br>";
											for (let [doctype, count] of Object.entries(r2.message.deleted)) {
												msg += `<strong>${doctype}</strong>: ${count}<br>`;
											}
										}
										frappe.msgprint({
											title: __("Cleanup Complete"),
											indicator: "green",
											message: msg,
										});
									},
								});
							} else {
								frappe.msgprint({
									title: __("Cleanup Complete"),
									indicator: "green",
									message: msg,
								});
							}
						}
					},
				});
			},
		});

		d.show();
	},
});
