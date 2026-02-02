// Copyright (c) 2025, Solede SA and contributors
// For license information, please see license.txt

const MODULE_PATH = "solede_setup.solede_setup.doctype.cost_center_importer.cost_center_importer";
const ROOT_LABEL = "All Cost Centers";

frappe.ui.form.on("Cost Center Importer", {
	onload: function (frm) {
		frm.set_value("company", "");
		frm.set_value("import_file", "");
		frm.set_value("force_delete_gl_entries", 0);
	},

	refresh: function (frm) {
		frm.disable_save();
		frm.set_df_property("import_file_section", "hidden", frm.doc.company ? 0 : 1);

		// Show existing count when company is selected
		solede_setup.importer.show_existing_count_with_company(frm, {
			count_method: `${MODULE_PATH}.get_existing_count`,
			message: "There are {0} existing Cost Centers for {1} that will be deleted on import.",
		});

		if (frm.doc.import_file) {
			frappe.run_serially([
				() => solede_setup.importer.generate_tree_preview(frm, {
					root_label: ROOT_LABEL,
					tree_method: `${MODULE_PATH}.get_cost_centers`,
					preview_field: "chart_tree",
				}),
				() => create_import_button(frm),
				() => frm.set_df_property("chart_preview", "hidden", 0),
			]);
		}

		frm.set_df_property(
			"chart_preview",
			"hidden",
			$(frm.fields_dict["chart_tree"].wrapper).html() != "" ? 0 : 1
		);
	},

	download_template: function (frm) {
		solede_setup.importer.show_download_dialog(`/api/method/${MODULE_PATH}.download_template`);
	},

	import_file: function (frm) {
		solede_setup.importer.handle_import_file_change(frm, "chart_tree", "chart_preview");
	},

	company: function (frm) {
		// Reset force delete when company changes
		frm.set_value("force_delete_gl_entries", 0);
		frm.set_df_property("force_delete_gl_entries", "hidden", 1);

		if (frm.doc.company) {
			// Check if GL Entries with cost center exist for the company
			frappe.call({
				method: `${MODULE_PATH}.validate_company`,
				args: { company: frm.doc.company },
				callback: function (r) {
					if (r.message && r.message.has_gl_entries) {
						frm.set_df_property("force_delete_gl_entries", "hidden", 0);
						frappe.msgprint({
							title: __("Warning"),
							indicator: "orange",
							message: __(
								"{0} GL Entries with Cost Centers exist for this company. " +
								"To proceed with import, you must enable 'Force Delete GL Entries' " +
								"which will permanently delete these transactions.",
								[r.message.count]
							),
						});
					} else {
						frm.set_df_property("force_delete_gl_entries", "hidden", 1);
					}
					frm.trigger("refresh");
				},
			});
		}
	},
});

var create_import_button = function (frm) {
	frm.page
		.set_primary_action(__("Import"), function () {
			frappe.call({
				method: `${MODULE_PATH}.get_existing_count`,
				args: { company: frm.doc.company },
				callback: function (r) {
					let existing_count = r.message ? r.message.count : 0;
					let confirm_msg = "";

					if (existing_count > 0) {
						confirm_msg = __("<b>Warning:</b> {0} existing Cost Centers will be deleted.", [existing_count]) + "<br><br>";
					}

					confirm_msg += __("This will delete ALL existing Cost Centers for company {0} and create new ones.", [frm.doc.company]);

					if (frm.doc.force_delete_gl_entries) {
						confirm_msg += "<br><br><span class='text-danger'>" +
							__("WARNING: All GL Entries with Cost Centers will also be permanently deleted!") +
							"</span>";
					}

					confirm_msg += "<br><br>" + __("Continue?");

					frappe.confirm(confirm_msg, function () {
						frappe.call({
							method: `${MODULE_PATH}.import_cost_centers`,
							args: {
								file_name: frm.doc.import_file,
								company: frm.doc.company,
								force_delete_gl_entries: frm.doc.force_delete_gl_entries,
							},
							freeze: true,
							freeze_message: __("Creating Cost Centers..."),
							callback: function (r) {
								if (!r.exc) {
									frm.page.set_indicator(__("Import Successful"), "blue");
									frappe.show_alert({
										message: __("Cost Centers imported successfully"),
										indicator: "green",
									});
									solede_setup.importer.create_reset_button(frm);
								}
							},
						});
					});
				},
			});
		})
		.addClass("btn btn-primary");
};
