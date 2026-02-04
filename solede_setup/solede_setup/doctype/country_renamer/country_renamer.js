// Copyright (c) 2025, Solede SA and contributors
// For license information, please see license.txt

const MODULE_PATH = "solede_setup.solede_setup.doctype.country_renamer.country_renamer";

frappe.ui.form.on("Country Renamer", {
	onload: function (frm) {
		frm.set_value("import_file", "");
	},

	refresh: function (frm) {
		frm.disable_save();

		// Add button to show all countries
		frm.add_custom_button(__("Show All Countries"), function () {
			show_all_countries();
		});

		if (frm.doc.import_file) {
			frappe.run_serially([
				() => generate_preview(frm),
				() => create_rename_button(frm),
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

var create_rename_button = function (frm) {
	frm.page.set_primary_action(__("Rename Countries"), function () {
		frappe.confirm(
			__("This will rename the countries as shown in the preview. Continue?"),
			function () {
				frappe.call({
					method: `${MODULE_PATH}.rename_countries`,
					args: { file_name: frm.doc.import_file },
					freeze: true,
					freeze_message: __("Renaming countries..."),
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
				let html = `<table class="table table-bordered">
					<thead>
						<tr>
							<th>${__("Current Name")}</th>
							<th>${__("New Name")}</th>
							<th>${__("Status")}</th>
						</tr>
					</thead>
					<tbody>`;

				r.message.forEach(function (row) {
					let status_class = row.exists ? "text-success" : "text-danger";
					html += `<tr>
						<td>${row.current_name}</td>
						<td>${row.new_name}</td>
						<td class="${status_class}">${row.status}</td>
					</tr>`;
				});

				html += `</tbody></table>`;
				$(frm.fields_dict["preview_html"].wrapper).html(html);
			}
		},
	});
};

var show_all_countries = function () {
	frappe.call({
		method: `${MODULE_PATH}.get_all_countries`,
		callback: function (r) {
			if (r.message && r.message.length) {
				let html = `<table class="table table-bordered table-sm">
					<thead>
						<tr>
							<th>Name</th>
							<th>Code</th>
						</tr>
					</thead>
					<tbody>`;

				r.message.forEach(function (c) {
					html += `<tr>
						<td>${c.name}</td>
						<td>${c.code || ""}</td>
					</tr>`;
				});

				html += `</tbody></table>`;

				frappe.msgprint({
					title: __("All Countries ({0})", [r.message.length]),
					message: html,
					wide: true,
				});
			}
		},
	});
};
