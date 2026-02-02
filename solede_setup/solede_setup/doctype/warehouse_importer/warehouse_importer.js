// Copyright (c) 2025, Solede SA and contributors
// For license information, please see license.txt

const MODULE_PATH = "solede_setup.solede_setup.doctype.warehouse_importer.warehouse_importer";
const ROOT_LABEL = "All Warehouses";

frappe.ui.form.on("Warehouse Importer", {
	onload: function (frm) {
		frm.set_value("company", "");
		frm.set_value("import_file", "");
	},

	refresh: function (frm) {
		frm.disable_save();
		frm.set_df_property("import_file_section", "hidden", frm.doc.company ? 0 : 1);

		// Show existing count when company is selected
		solede_setup.importer.show_existing_count_with_company(frm, {
			count_method: `${MODULE_PATH}.get_existing_count`,
			message: "There are {0} existing Warehouses for {1} that will be deleted on import.",
		});

		if (frm.doc.import_file) {
			frappe.run_serially([
				() => solede_setup.importer.generate_tree_preview(frm, {
					root_label: ROOT_LABEL,
					tree_method: `${MODULE_PATH}.get_warehouses`,
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
		frm.trigger("refresh");
	},
});

var create_import_button = function (frm) {
	solede_setup.importer.create_import_button(frm, {
		count_method: `${MODULE_PATH}.get_existing_count`,
		import_method: `${MODULE_PATH}.import_warehouses`,
		warning_message: "<b>Warning:</b> {0} existing Warehouses will be deleted.",
		confirm_message: "This will delete ALL existing Warehouses for the selected company and create new ones. Continue?",
		freeze_message: "Creating Warehouses...",
		success_message: "Warehouses imported successfully",
		import_args: { company: frm.doc.company },
	});
};
