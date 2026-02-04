// Copyright (c) 2025, Solede SA and contributors
// For license information, please see license.txt

const MODULE_PATH = "solede_setup.solede_setup.doctype.country_importer.country_importer";

frappe.ui.form.on("Country Importer", {
	onload: function (frm) {
		frm.set_value("import_file", "");
	},

	refresh: function (frm) {
		frm.disable_save();

		// Show current countries count
		frappe.call({
			method: `${MODULE_PATH}.get_current_countries_count`,
			callback: function (r) {
				if (r.message !== undefined) {
					frm.set_intro(
						__("Current countries in database: {0}. Importing will DELETE all existing countries.", [r.message]),
						"yellow"
					);
				}
			},
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
	frm.page.set_primary_action(__("Import Countries"), function () {
		frappe.confirm(
			__("This will DELETE ALL existing countries and import the new ones from the file. This action cannot be undone. Continue?"),
			function () {
				frappe.call({
					method: `${MODULE_PATH}.import_countries`,
					args: { file_name: frm.doc.import_file },
					freeze: true,
					freeze_message: __("Deleting and importing countries..."),
					callback: function (r) {
						if (r.message) {
							let msg = r.message.message;
							if (r.message.errors && r.message.errors.length > 0) {
								msg += "<br><br><b>Errors:</b><ul>";
								r.message.errors.forEach(function (e) {
									msg += `<li>${e}</li>`;
								});
								msg += "</ul>";
							}
							frappe.msgprint({
								title: __("Result"),
								indicator: r.message.errors ? "orange" : "green",
								message: msg,
							});
							frm.reload_doc();
						}
					},
				});
			}
		);
	});
};

var generate_preview = function (frm) {
	$(frm.fields_dict["preview_html"].wrapper).empty();

	return frappe.call({
		method: `${MODULE_PATH}.get_preview_data`,
		args: { file_name: frm.doc.import_file },
		callback: function (r) {
			if (r.message && r.message.length) {
				let html = `<table class="table table-bordered table-sm">
					<thead>
						<tr>
							<th>${__("Name")}</th>
							<th>${__("Code")}</th>
							<th>${__("Date Format")}</th>
							<th>${__("Time Format")}</th>
							<th>${__("Time Zones")}</th>
						</tr>
					</thead>
					<tbody>`;

				r.message.forEach(function (row) {
					html += `<tr>
						<td>${row.name}</td>
						<td>${row.code || ""}</td>
						<td>${row.date_format || ""}</td>
						<td>${row.time_format || ""}</td>
						<td>${row.time_zones || ""}</td>
					</tr>`;
				});

				html += `</tbody></table>`;
				$(frm.fields_dict["preview_html"].wrapper).html(html);
			}
		},
	});
};
