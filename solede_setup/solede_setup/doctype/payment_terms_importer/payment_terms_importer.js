// Copyright (c) 2025, Solede SA and contributors
// For license information, please see license.txt

const MODULE_PATH = "solede_setup.solede_setup.doctype.payment_terms_importer.payment_terms_importer";

frappe.ui.form.on("Payment Terms Importer", {
	onload: function (frm) {
		frm.set_value("import_file", "");
	},

	refresh: function (frm) {
		frm.disable_save();

		// Show existing count
		solede_setup.importer.show_existing_count(frm, {
			count_method: `${MODULE_PATH}.get_existing_count`,
			message: "There are {0} existing Payment Terms that will be deleted on import.",
		});

		if (frm.doc.import_file) {
			frappe.run_serially([
				() => generate_preview(frm),
				() => create_import_button(frm),
				() => frm.set_df_property("preview_section", "hidden", 0),
			]);
		}

		frm.set_df_property(
			"preview_section",
			"hidden",
			$(frm.fields_dict["preview_html"].wrapper).html() != "" ? 0 : 1
		);
	},

	download_template: function (frm) {
		solede_setup.importer.show_download_dialog(`/api/method/${MODULE_PATH}.download_template`);
	},

	import_file: function (frm) {
		solede_setup.importer.handle_import_file_change(frm, "preview_html", "preview_section");
	},
});

var create_import_button = function (frm) {
	solede_setup.importer.create_import_button(frm, {
		count_method: `${MODULE_PATH}.get_existing_count`,
		import_method: `${MODULE_PATH}.import_payment_terms`,
		warning_message: "<b>Warning:</b> {0} existing Payment Terms will be deleted.",
		confirm_message: "This will delete ALL existing Payment Terms and create new ones from the file. Continue?",
		freeze_message: "Creating Payment Terms...",
		success_message: "Payment Terms imported successfully",
	});
};

var generate_preview = function (frm) {
	$(frm.fields_dict["preview_html"].wrapper).empty();

	return frappe.call({
		method: `${MODULE_PATH}.get_preview_data`,
		args: { file_name: frm.doc.import_file },
		callback: function (r) {
			if (r.message && r.message.length) {
				let html = `<table class="table table-bordered">
					<thead>
						<tr>
							<th>${__("Payment Term")}</th>
							<th>${__("Description")}</th>
							<th>${__("Due Date Based On")}</th>
							<th>${__("Credit Days")}</th>
							<th>${__("Invoice Portion %")}</th>
						</tr>
					</thead>
					<tbody>`;

				r.message.forEach(function (row) {
					html += `<tr>
						<td>${row.payment_term_name}</td>
						<td>${row.description || ""}</td>
						<td>${row.due_date_based_on}</td>
						<td>${row.credit_days}</td>
						<td>${row.invoice_portion}%</td>
					</tr>`;
				});

				html += `</tbody></table>`;
				$(frm.fields_dict["preview_html"].wrapper).html(html);
			}
		},
	});
};
