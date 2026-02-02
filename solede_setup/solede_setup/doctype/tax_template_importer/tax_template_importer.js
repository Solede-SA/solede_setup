// Copyright (c) 2025, Solede SA and contributors
// For license information, please see license.txt

const MODULE_PATH = "solede_setup.solede_setup.doctype.tax_template_importer.tax_template_importer";

frappe.ui.form.on("Tax Template Importer", {
	onload: function (frm) {
		frm.set_value("company", "");
		frm.set_value("import_file", "");
	},

	refresh: function (frm) {
		frm.disable_save();
		frm.set_df_property("import_file_section", "hidden", frm.doc.company ? 0 : 1);

		// Show existing count when company is selected (with detailed breakdown)
		if (frm.doc.company) {
			frappe.call({
				method: `${MODULE_PATH}.get_existing_count`,
				args: { company: frm.doc.company },
				callback: function (r) {
					let count = r.message ? r.message.count : 0;
					if (count > 0) {
						let sales = r.message.sales || 0;
						let purchase = r.message.purchase || 0;
						let item = r.message.item || 0;
						frm.set_intro(__(
							"There are {0} existing Tax Templates for {1} that will be deleted on import ({2} Sales, {3} Purchase, {4} Item).",
							[count, frm.doc.company, sales, purchase, item]
						), "yellow");
					} else {
						frm.set_intro("");
					}
				}
			});
		} else {
			frm.set_intro("");
		}

		if (frm.doc.import_file && frm.doc.company) {
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

	company: function (frm) {
		frm.trigger("refresh");
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
						let sales = r.message.sales || 0;
						let purchase = r.message.purchase || 0;
						let item = r.message.item || 0;
						confirm_msg = __("<b>Warning:</b> {0} existing Tax Templates will be deleted ({1} Sales, {2} Purchase, {3} Item).", [existing_count, sales, purchase, item]) + "<br><br>";
					}

					confirm_msg += __("This will delete ALL existing Sales, Purchase, and Item Tax Templates for company {0} and create new ones. Continue?", [frm.doc.company]);

					frappe.confirm(confirm_msg, function () {
						frappe.call({
							method: `${MODULE_PATH}.import_tax_templates`,
							args: {
								file_name: frm.doc.import_file,
								company: frm.doc.company,
							},
							freeze: true,
							freeze_message: __("Creating Tax Templates..."),
							callback: function (r) {
								if (!r.exc) {
									frm.page.set_indicator(__("Import Successful"), "blue");
									frappe.show_alert({
										message: __("Tax Templates imported successfully"),
										indicator: "green",
									});
									solede_setup.importer.create_reset_button(frm);
								}
							},
						});
					});
				}
			});
		})
		.addClass("btn btn-primary");
};

var generate_preview = function (frm) {
	$(frm.fields_dict["preview_html"].wrapper).empty();

	return frappe.call({
		method: `${MODULE_PATH}.get_preview_data`,
		args: {
			file_name: frm.doc.import_file,
			company: frm.doc.company,
		},
		callback: function (r) {
			if (r.message && r.message.length) {
				let html = "";

				r.message.forEach(function (template) {
					let badge_color =
						template.template_type === "Sales"
							? "blue"
							: template.template_type === "Purchase"
							? "orange"
							: "green";
					let default_badge = template.is_default
						? `<span class="badge badge-success ml-2">${__("Default")}</span>`
						: "";

					html += `
						<div class="card mb-3">
							<div class="card-header">
								<span class="badge badge-${badge_color}">${template.template_type}</span>
								<strong class="ml-2">${template.template_title}</strong>
								${default_badge}
							</div>
							<div class="card-body p-0">
								<table class="table table-bordered mb-0">
									<thead>
										<tr>`;

					if (template.template_type === "Item") {
						html += `
											<th>${__("Account")}</th>
											<th>${__("Rate")}</th>`;
					} else {
						html += `
											<th>${__("Charge Type")}</th>
											<th>${__("Account")}</th>
											<th>${__("Rate")}</th>
											<th>${__("Description")}</th>`;
					}

					html += `
										</tr>
									</thead>
									<tbody>`;

					template.taxes.forEach(function (tax) {
						if (template.template_type === "Item") {
							html += `
								<tr>
									<td>${tax.account_head}</td>
									<td>${tax.rate}%</td>
								</tr>`;
						} else {
							html += `
								<tr>
									<td>${tax.charge_type || ""}</td>
									<td>${tax.account_head}</td>
									<td>${tax.rate}%</td>
									<td>${tax.description || ""}</td>
								</tr>`;
						}
					});

					html += `
									</tbody>
								</table>
							</div>
						</div>`;
				});

				$(frm.fields_dict["preview_html"].wrapper).html(html);
			}
		},
	});
};
