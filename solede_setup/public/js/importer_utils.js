/**
 * Solede Setup - Importer Utilities
 *
 * Shared functions for all importers to avoid code duplication.
 */

frappe.provide("solede_setup.importer");

/**
 * Show download template dialog.
 * @param {string} download_url - API endpoint for template download
 */
solede_setup.importer.show_download_dialog = function (download_url) {
	var d = new frappe.ui.Dialog({
		title: __("Download Template"),
		fields: [
			{
				label: "File Type",
				fieldname: "file_type",
				fieldtype: "Select",
				reqd: 1,
				options: ["Excel", "CSV"],
			},
		],
		primary_action: function () {
			let data = d.get_values();
			open_url_post(download_url, { file_type: data.file_type });
			d.hide();
		},
		primary_action_label: __("Download"),
	});
	d.show();
};

/**
 * Create reset button after successful import.
 * @param {object} frm - Frappe form object
 */
solede_setup.importer.create_reset_button = function (frm) {
	frm.page
		.set_primary_action(__("Reset"), function () {
			frm.page.clear_primary_action();
			frm.reload_doc();
		})
		.addClass("btn btn-primary");
};

/**
 * Handle import file field change.
 * @param {object} frm - Frappe form object
 * @param {string} preview_field - Name of the preview field (chart_tree or preview_html)
 * @param {string} preview_section - Name of the preview section
 */
solede_setup.importer.handle_import_file_change = function (frm, preview_field, preview_section) {
	if (!frm.doc.import_file) {
		frm.page.set_indicator("");
		frm.page.clear_primary_action();
		$(frm.fields_dict[preview_field].wrapper).empty();
		frm.set_df_property(preview_section, "hidden", 1);
	} else {
		frm.trigger("refresh");
	}
};

/**
 * Show existing count intro message.
 * @param {object} frm - Frappe form object
 * @param {object} config - Configuration object
 * @param {string} config.count_method - API method to get count
 * @param {string} config.message - Message template with {0} for count
 * @param {string} [config.company] - Company name (for company-specific doctypes)
 */
solede_setup.importer.show_existing_count = function (frm, config) {
	let args = config.company ? { company: config.company } : {};

	frappe.call({
		method: config.count_method,
		args: args,
		callback: function (r) {
			let count = r.message ? r.message.count : 0;
			if (count > 0) {
				frm.set_intro(__(config.message, [count]), "yellow");
			} else {
				frm.set_intro("");
			}
		},
	});
};

/**
 * Show existing count intro message for company-specific doctypes.
 * @param {object} frm - Frappe form object
 * @param {object} config - Configuration object
 * @param {string} config.count_method - API method to get count
 * @param {string} config.message - Message template with {0} for count, {1} for company
 */
solede_setup.importer.show_existing_count_with_company = function (frm, config) {
	if (frm.doc.company) {
		frappe.call({
			method: config.count_method,
			args: { company: frm.doc.company },
			callback: function (r) {
				let count = r.message ? r.message.count : 0;
				if (count > 0) {
					frm.set_intro(__(config.message, [count, frm.doc.company]), "yellow");
				} else {
					frm.set_intro("");
				}
			},
		});
	} else {
		frm.set_intro("");
	}
};

/**
 * Generate tree preview for NestedSet importers.
 * @param {object} frm - Frappe form object
 * @param {object} config - Configuration object
 * @param {string} config.root_label - Root node label
 * @param {string} config.tree_method - API method to get tree data
 * @param {string} config.preview_field - Name of the tree wrapper field
 */
solede_setup.importer.generate_tree_preview = function (frm, config) {
	let parent = __(config.root_label);
	$(frm.fields_dict[config.preview_field].wrapper).empty();

	return new frappe.ui.Tree({
		parent: $(frm.fields_dict[config.preview_field].wrapper),
		label: parent,
		expandable: true,
		method: config.tree_method,
		args: {
			file_name: frm.doc.import_file,
			parent: parent,
			doctype: frm.doctype,
		},
		onclick: function (node) {},
	});
};

/**
 * Create import button with confirmation dialog.
 * @param {object} frm - Frappe form object
 * @param {object} config - Configuration object
 * @param {string} config.count_method - API method to get existing count
 * @param {string} config.import_method - API method to perform import
 * @param {string} config.warning_message - Warning message template with {0} for count
 * @param {string} config.confirm_message - Confirmation message
 * @param {string} config.freeze_message - Freeze message during import
 * @param {string} config.success_message - Success message after import
 * @param {object} [config.import_args] - Additional arguments for import method
 */
solede_setup.importer.create_import_button = function (frm, config) {
	frm.page
		.set_primary_action(__("Import"), function () {
			let count_args = config.import_args || {};

			frappe.call({
				method: config.count_method,
				args: count_args,
				callback: function (r) {
					let existing_count = r.message ? r.message.count : 0;
					let confirm_msg = "";

					if (existing_count > 0) {
						confirm_msg = __(config.warning_message, [existing_count]) + "<br><br>";
					}

					confirm_msg += __(config.confirm_message);

					frappe.confirm(confirm_msg, function () {
						let import_args = Object.assign(
							{ file_name: frm.doc.import_file },
							config.import_args || {}
						);

						frappe.call({
							method: config.import_method,
							args: import_args,
							freeze: true,
							freeze_message: __(config.freeze_message),
							callback: function (r) {
								if (!r.exc) {
									frm.page.set_indicator(__("Import Successful"), "blue");
									frappe.show_alert({
										message: __(config.success_message),
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
