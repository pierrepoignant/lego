# LEGO Database Management

This project provides tools to manage a MySQL database for LEGO product and financial data.

## Project Structure

### Core Utilities
- **`db_utils.py`** - Shared database connection and utility functions

### Database Management Scripts
- **`init_database.py`** - Initialize database schema (creates tables only, no data import)
- **`manage_data.py`** - Command-line tool to manage data (flush, import)
- **`check_database.py`** - Check current database state and record counts

### Data Import Modules
- **`import_infinite.py`** - Import module for infinite.csv format
- **`import_razor.py`** - Import module for razor.csv format

### Legacy Scripts
- **`create_database.py`** - Original all-in-one script (now replaced by init_database.py + manage_data.py)

## Database Schema

The database consists of the following main tables:

1. **`category`** - Product categories (hierarchical)
2. **`brand`** - Brand information (includes `group` field to track data source: 'infinite' or 'razor')
3. **`brand_scrapped`** - Brand names extracted from Amazon scraping (links to `brand` table)
4. **`asin`** - Product ASINs with associated product IDs (includes `brand_scrapped` field from scraping)
5. **`financials`** - Financial metrics by ASIN, marketplace, metric, and month
6. **`stock`** - Inventory data by ASIN, location, and month
7. **`location`** - Location information for stock tracking

## Quick Start

### 1. Initialize Database

First time setup - creates the database and tables:

```bash
python init_database.py
```

**Note:** If you have an existing database from before recent schema changes, run the appropriate migration scripts:

```bash
# Add brand_scrapped and brand_imported columns to asin table
python apply_brand_columns_migration.py

# Create and populate the brand_scrapped table
python apply_brand_scrapped_table_migration.py

# Add brand group field (older migration)
python migrate_add_brand_group.py
```

### 2. Import Data

Import data from CSV files:

```bash
# Import infinite.csv
python manage_data.py import-infinite

# Import razor.csv
python manage_data.py import-razor

# Flush existing financial data and import fresh
python manage_data.py flush import-infinite
python manage_data.py flush import-razor
```

### 3. Check Database

View current database state:

```bash
python check_database.py
```

## Data File Formats

### infinite.csv Format

- Delimiter: semicolon (`;`)
- Row 1: Metric names (repeating headers)
- Row 2: Column headers (Product ID, Brand, MP, Status, then month names)
- Data rows: Product information + financial metrics by month

Columns:
- **Product ID** - Internal product identifier
- **Brand** - Brand name
- **MP** - Marketplace (e.g., US, DE, FR, IT)
- **Status** - Product status (e.g., Ongoing)
- Financial columns with metrics like: Net units, Net revenue, Net COGS, CM1, FBA fees, CM2, SEM costs, Promo fees, CM3

### razor.csv Format

- Delimiter: semicolon (`;`)
- Row 1: Metric names (repeating headers)
- Row 2: Column headers (ASIN, Brand Name, Marketplace, then month names)
- Data rows: Product information + financial metrics by month

Columns:
- **ASIN** (Column 1) - Amazon Standard Identification Number
- **Brand Name** (Column 2) - Brand name
- **Marketplace** (Column 3) - Marketplace code
- Financial columns with metrics like: Net Units, Net Revenue, COGS, CM1, Referral Fees, Fulfillment Fee, Other platform fees, CM2, Marketing, CM3

## Command Reference

### manage_data.py Commands

```bash
# Flush all financial data (keeps brands and ASINs)
python manage_data.py flush

# Import from infinite.csv
python manage_data.py import-infinite

# Import from razor.csv
python manage_data.py import-razor

# Chain commands (executed in order)
python manage_data.py flush import-infinite
python manage_data.py flush import-razor
python manage_data.py import-infinite import-razor
```

## Notes

- **Flushing** removes only financial data from the `financials` table
- **Brands and ASINs** are preserved when flushing
- **Importing** creates new brands and ASINs as needed
- **Duplicate ASINs** are handled gracefully (updates existing records)
- All financial values are stored as `DECIMAL(15, 2)`

## Requirements

- Python 3.6+
- MySQL Server
- PyMySQL library

```bash
pip install pymysql
```

## Database Configuration

The database connection uses these default settings (can be modified in `db_utils.py`):

- Host: `127.0.0.1`
- Port: `3306`
- User: `root`
- Password: `` (empty)
- Database: `lego`

