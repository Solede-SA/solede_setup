app_name = "solede_setup"
app_title = "Solede Setup"
app_publisher = "Solede SA"
app_description = "Configurazione automatica ERPNext con intercettazione automatismi setup"
app_email = "info@solede.com"
app_license = "agpl-3.0"

# Apps
# ------------------

required_apps = ["erpnext"]

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "solede_setup",
# 		"logo": "/assets/solede_setup/logo.png",
# 		"title": "Solede Setup",
# 		"route": "/solede_setup",
# 		"has_permission": "solede_setup.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/solede_setup/css/solede_setup.css"
app_include_js = [
    "/assets/solede_setup/js/setup_wizard.js",
    "/assets/solede_setup/js/importer_utils.js",
]

# include js, css files in header of web template
# web_include_css = "/assets/solede_setup/css/solede_setup.css"
# web_include_js = "/assets/solede_setup/js/solede_setup.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "solede_setup/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "solede_setup/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "solede_setup.utils.jinja_methods",
# 	"filters": "solede_setup.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "solede_setup.install.before_install"
after_install = "solede_setup.install.after_install"

# ============================================================================
# SOLEDE SETUP - INTERCEPT HOOKS
# ============================================================================

# Setup Wizard Hooks
# ------------------
# Aggiunge stage custom al wizard e intercetta il completamento

# JavaScript iniettato nel Setup Wizard (mostra avvisi se profilo attivo)
setup_wizard_requires = "assets/solede_setup/js/setup_wizard.js"

# Stage custom all'inizio del wizard (abilita tracking)
setup_wizard_stages = "solede_setup.setup.intercept.before_wizard_stage"

# Eseguito DOPO che tutti gli stage sono completati
setup_wizard_complete = "solede_setup.setup.intercept.post_wizard_cleanup"

# Uninstallation
# ------------

# before_uninstall = "solede_setup.uninstall.before_uninstall"
# after_uninstall = "solede_setup.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "solede_setup.utils.before_app_install"
# after_app_install = "solede_setup.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "solede_setup.utils.before_app_uninstall"
# after_app_uninstall = "solede_setup.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "solede_setup.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

override_doctype_class = {
    "Company": "solede_setup.overrides.company.CustomCompany",
    "Cost Center": "solede_setup.overrides.cost_center.CustomCostCenter",
    "Warehouse": "solede_setup.overrides.warehouse.CustomWarehouse",
}

# Fixtures
# --------
# Custom fields per supportare custom_id negli importer

fixtures = [
    {
        "dt": "Custom Field",
        "filters": [["module", "=", "Solede Setup"]]
    },
    {
        "dt": "Workspace",
        "filters": [["module", "=", "Solede Setup"]]
    }
]

# Document Events
# ---------------
# Hook on document methods and events
# Intercetta creazione di documenti durante il setup per tracciamento

doc_events = {
    # Company - punto critico dove ERPNext crea molti dati automatici
    "Company": {
        "after_insert": "solede_setup.setup.intercept.on_company_after_insert",
        "on_update": "solede_setup.setup.intercept.on_company_on_update",
    },
    # Accounting
    "Account": {
        "after_insert": "solede_setup.setup.intercept.on_account_after_insert",
    },
    "Cost Center": {
        "after_insert": "solede_setup.setup.intercept.on_cost_center_after_insert",
    },
    # Stock
    "Warehouse": {
        "after_insert": "solede_setup.setup.intercept.on_warehouse_after_insert",
    },
    "Item Group": {
        "after_insert": "solede_setup.setup.intercept.on_item_group_after_insert",
    },
    "Stock Entry Type": {
        "after_insert": "solede_setup.setup.intercept.on_stock_entry_type_after_insert",
    },
    "UOM": {
        "after_insert": "solede_setup.setup.intercept.on_uom_after_insert",
    },
    # HR
    "Department": {
        "after_insert": "solede_setup.setup.intercept.on_department_after_insert",
    },
    # CRM/Selling/Buying
    "Territory": {
        "after_insert": "solede_setup.setup.intercept.on_territory_after_insert",
    },
    "Customer Group": {
        "after_insert": "solede_setup.setup.intercept.on_customer_group_after_insert",
    },
    "Supplier Group": {
        "after_insert": "solede_setup.setup.intercept.on_supplier_group_after_insert",
    },
    # Taxes
    "Sales Taxes and Charges Template": {
        "after_insert": "solede_setup.setup.intercept.on_sales_tax_template_after_insert",
    },
    "Purchase Taxes and Charges Template": {
        "after_insert": "solede_setup.setup.intercept.on_purchase_tax_template_after_insert",
    },
    "Item Tax Template": {
        "after_insert": "solede_setup.setup.intercept.on_item_tax_template_after_insert",
    },
    # Payment
    "Mode of Payment": {
        "after_insert": "solede_setup.setup.intercept.on_mode_of_payment_after_insert",
    },
    "Price List": {
        "after_insert": "solede_setup.setup.intercept.on_price_list_after_insert",
    },
    "Payment Term": {
        "after_insert": "solede_setup.setup.intercept.on_payment_term_after_insert",
    },
    "Payment Terms Template": {
        "after_insert": "solede_setup.setup.intercept.on_payment_terms_template_after_insert",
    },
}

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"solede_setup.tasks.all"
# 	],
# 	"daily": [
# 		"solede_setup.tasks.daily"
# 	],
# 	"hourly": [
# 		"solede_setup.tasks.hourly"
# 	],
# 	"weekly": [
# 		"solede_setup.tasks.weekly"
# 	],
# 	"monthly": [
# 		"solede_setup.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "solede_setup.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "solede_setup.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "solede_setup.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["solede_setup.utils.before_request"]
# after_request = ["solede_setup.utils.after_request"]

# Job Events
# ----------
# before_job = ["solede_setup.utils.before_job"]
# after_job = ["solede_setup.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"solede_setup.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# Translation
# ------------
# List of apps whose translatable strings should be excluded from this app's translations.
# ignore_translatable_strings_from = []

