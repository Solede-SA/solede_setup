// Copyright (c) 2025, Solede SA and contributors
// For license information, please see license.txt

const MODULE_PATH = "solede_setup.solede_setup.doctype.supplier_group_importer.supplier_group_importer";
const ROOT_LABEL = "All Supplier Groups";

frappe.ui.form.on("Supplier Group Importer", {
	onload: function (frm) {
		frm.set_value("import_file", "");
	},

	refresh: function (frm) {
		frm.disable_save();

		// Show existing count
		solede_setup.importer.show_existing_count(frm, {
			count_method: `${MODULE_PATH}.get_existing_count`,
			message: "There are {0} existing Supplier Groups that will be deleted on import.",
		});

		if (frm.doc.import_file) {
			frappe.run_serially([
				() => solede_setup.importer.generate_tree_preview(frm, {
					root_label: ROOT_LABEL,
					tree_method: `${MODULE_PATH}.get_supplier_groups`,
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
});

var create_import_button = function (frm) {
	solede_setup.importer.create_import_button(frm, {
		count_method: `${MODULE_PATH}.get_existing_count`,
		import_method: `${MODULE_PATH}.import_supplier_groups`,
		warning_message: "<b>Warning:</b> {0} existing Supplier Groups will be deleted.",
		confirm_message: "This will delete ALL existing Supplier Groups and create new ones from the file. Continue?",
		freeze_message: "Creating Supplier Groups...",
		success_message: "Supplier Groups imported successfully",
	});
};
