# Solede Setup

A Frappe/ERPNext app for bulk importing master data from CSV/Excel files. Simplifies the initial setup of ERPNext by allowing you to import tree structures (Cost Centers, Warehouses, Item Groups, etc.) and flat lists (Modes of Payment, Payment Terms, Tax Templates) in bulk.

## Features

### Tree Structure Importers
Import hierarchical data with parent-child relationships:

- **Cost Center Importer** - Import cost centers with custom IDs
- **Warehouse Importer** - Import warehouses with custom IDs
- **Item Group Importer** - Import item group hierarchy
- **Territory Importer** - Import sales territories
- **Customer Group Importer** - Import customer group hierarchy
- **Supplier Group Importer** - Import supplier group hierarchy
- **Chart of Accounts Importer** - Import account hierarchy (uses ERPNext's built-in importer)

### Flat List Importers
Import non-hierarchical master data:

- **Mode of Payment Importer** - Import payment modes with default accounts
- **Payment Terms Importer** - Import payment terms templates
- **Tax Template Importer** - Import Sales, Purchase, and Item Tax Templates

### Key Features

- **Preview before import** - See a tree visualization of your data before importing
- **Existing data warning** - Shows count of existing records that will be deleted
- **Custom ID support** - Use your own IDs for Cost Centers and Warehouses (automatically appends company abbreviation)
- **Template download** - Download CSV/Excel templates with sample data
- **Validation** - Validates file structure and parent references before import

### Setup Wizard Integration

Solede Setup can intercept and control ERPNext's setup wizard to skip default data creation, allowing you to import your own master data instead.

**Setup Profile** allows you to:
- Skip creation of default Item Groups, Territories, Customer Groups, etc.
- Skip default Tax Templates, Payment Terms, and Modes of Payment
- Skip country-specific fixtures
- Track all documents created during setup
- Clean up unwanted default data after setup

## Installation

### Prerequisites
- Frappe Bench
- ERPNext installed

### Install via Bench

```bash
# Navigate to your bench directory
cd frappe-bench

# Get the app from GitHub
bench get-app https://github.com/Solede-SA/solede_setup.git

# Install on your site
bench --site your-site.local install-app solede_setup

# Run migrations
bench --site your-site.local migrate

# Clear cache
bench --site your-site.local clear-cache
```

## Usage

### Accessing the Importers

1. Navigate to the **Solede Setup** workspace in ERPNext
2. You'll see all available importers organized by category:
   - **Tree Importers** - For hierarchical data
   - **List Importers** - For flat data
   - **Configuration** - Setup Profile

### Importing Tree Structures (e.g., Cost Centers)

1. Open **Cost Center Importer** from the workspace
2. Select the **Company** (required for Cost Centers and Warehouses)
3. Click **Download Template** to get a CSV/Excel template
4. Fill in the template with your data:

| ID | Cost Center Name | Parent Cost Center | Is Group |
|----|------------------|-------------------|----------|
| ROOT001 | Main Cost Center | | 1 |
| SALES001 | Sales | ROOT001 | 1 |
| SALES-IT | Sales Italy | SALES001 | 0 |
| SALES-EU | Sales Europe | SALES001 | 0 |
| ADMIN001 | Administration | ROOT001 | 0 |

5. Upload the file using the **Import File** field
6. Review the tree preview to verify the structure
7. Click **Import** to create the records

**Note:** For Cost Centers and Warehouses, the document name will be `ID - CompanyAbbr` (e.g., "SALES001 - TC")

### Importing Flat Lists (e.g., Payment Terms)

1. Open **Payment Terms Importer** from the workspace
2. Click **Download Template** to get a sample template
3. Fill in the template:

| Payment Term Name | Description | Due Date Based On | Credit Days | Credit Months | Invoice Portion |
|-------------------|-------------|-------------------|-------------|---------------|-----------------|
| Net 30 | Payment due in 30 days | Day(s) after invoice date | 30 | 0 | 100 |
| Net 60 | Payment due in 60 days | Day(s) after invoice date | 60 | 0 | 100 |

4. Upload and click **Import**

### Importing Tax Templates

1. Open **Tax Template Importer** from the workspace
2. Select the **Company**
3. Download the template - it has three sheets:
   - **Sales Taxes** - For Sales Taxes and Charges Template
   - **Purchase Taxes** - For Purchase Taxes and Charges Template
   - **Item Taxes** - For Item Tax Template
4. Fill in each sheet as needed
5. Upload and import

### Using Setup Profile with Setup Wizard

If you want to prevent ERPNext from creating default master data during the initial setup wizard, configure a Setup Profile **before** running the wizard.

#### Step 1: Install the App (Before Running Setup Wizard)

If setting up a new site, install the app before completing the setup wizard:

```bash
# Create new site
bench new-site your-site.local

# Install ERPNext
bench --site your-site.local install-app erpnext

# Install Solede Setup BEFORE completing the wizard
bench --site your-site.local install-app solede_setup
bench --site your-site.local migrate
```

#### Step 2: Activate a Setup Profile

The app comes with pre-configured profiles. List available profiles and activate one:

```bash
# List all available profiles
bench --site your-site.local list-setup-profiles

# Show details of a specific profile
bench --site your-site.local show-setup-profile "CH Clean Start"

# Activate a profile
bench --site your-site.local set-setup-profile "CH Clean Start"
```

**Pre-configured profiles:**

| Profile | Description |
|---------|-------------|
| `CH Clean Start` | Swiss profile: removes all ERPNext defaults for a clean start |
| `IT Clean Start` | Italian profile: removes defaults but keeps country fixtures for e-invoicing |
| `Keep All Defaults` | Keeps all ERPNext default data (no cleanup) |

#### Step 3: Complete the Setup Wizard

Return to the setup wizard tab. You'll see a banner indicating the active Setup Profile. Complete the wizard normally - the app will skip creating the default data you configured.

#### Step 4: Import Your Custom Data

After the wizard completes:
1. Navigate to the **Solede Setup** workspace
2. Use the importers to load your custom master data
3. View **Setup Log** to see what was created during setup

#### Setup Profile Options

| Option | Description |
|--------|-------------|
| `skip_default_item_groups` | Don't create default Item Groups (All Item Groups, Products, etc.) |
| `skip_default_territories` | Don't create default Territories (All Territories, etc.) |
| `skip_default_customer_groups` | Don't create default Customer Groups |
| `skip_default_supplier_groups` | Don't create default Supplier Groups |
| `skip_default_mode_of_payment` | Don't create default Modes of Payment (Cash, Bank Transfer, etc.) |
| `skip_default_tax_templates` | Don't create default Tax Templates |
| `skip_default_payment_terms` | Don't create default Payment Terms |
| `skip_default_stock_entry_types` | Don't create default Stock Entry Types |
| `skip_default_price_lists` | Don't create default Price Lists |
| `skip_default_uom` | Don't create default Units of Measure |
| `skip_country_fixtures` | Don't create country-specific default data |

## Template Formats

### Tree Structure Template (4 columns)
| Column | Description |
|--------|-------------|
| ID | Unique identifier (used as document name) |
| Name | Display name |
| Parent ID | ID of the parent record (empty for root) |
| Is Group | 1 = group/folder, 0 = leaf |

### Mode of Payment Template
| Column | Description |
|--------|-------------|
| Mode of Payment | Name of the payment mode |
| Type | Cash, Bank, or General |
| Default Account | Account code (optional) |

### Payment Terms Template
| Column | Description |
|--------|-------------|
| Payment Term Name | Unique name |
| Description | Description text |
| Due Date Based On | Day(s) after invoice date, Day(s) after the end of the invoice month, or Month(s) after the end of the invoice month |
| Credit Days | Number of days |
| Credit Months | Number of months |
| Invoice Portion | Percentage (0-100), default 100 |

## Important Notes

1. **Data Replacement**: Importing will **DELETE ALL EXISTING** records of that type for the selected company (or globally for non-company-specific data) and create new ones from the file.

2. **GL Entry Protection**: For Cost Centers, if GL Entries exist with cost centers, you must enable "Force Delete GL Entries" to proceed (this will permanently delete those transactions).

3. **Parent References**: In tree structures, parent IDs must exist in the same file. The import processes parents before children automatically.

4. **Company Abbreviation**: For Cost Centers and Warehouses, the company abbreviation is automatically appended to the ID (e.g., "SALES001" becomes "SALES001 - TC").

## Contributing

This app uses `pre-commit` for code formatting and linting. Please [install pre-commit](https://pre-commit.com/#installation) and enable it for this repository:

```bash
cd apps/solede_setup
pre-commit install
```

Pre-commit is configured to use the following tools for checking and formatting your code:

- ruff
- eslint
- prettier
- pyupgrade

## License

AGPL-3.0

## Author

Solede SA
