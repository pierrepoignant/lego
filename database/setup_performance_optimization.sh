#!/bin/bash
#
# Setup Script for Dashboard Performance Optimization
# ===================================================
# This script sets up the summary tables for faster dashboard performance
#
# Usage:
#   ./setup_performance_optimization.sh
#

set -e  # Exit on error

echo "========================================================================"
echo "Dashboard Performance Optimization Setup"
echo "========================================================================"
echo ""

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Check if config.ini exists
CONFIG_FILE="../config.ini"
if [ ! -f "$CONFIG_FILE" ]; then
    echo "ERROR: config.ini not found at $CONFIG_FILE"
    echo "Please create a config.ini file with database credentials"
    exit 1
fi

# Read database credentials from config.ini
# Use awk to properly parse the [database] section only
DB_HOST=$(awk -F= '/^\[database\]/{flag=1; next} /^\[/{flag=0} flag && /^host/{gsub(/^[ \t]+|[ \t]+$/, "", $2); print $2; exit}' $CONFIG_FILE)
DB_PORT=$(awk -F= '/^\[database\]/{flag=1; next} /^\[/{flag=0} flag && /^port/{gsub(/^[ \t]+|[ \t]+$/, "", $2); print $2; exit}' $CONFIG_FILE)
DB_USER=$(awk -F= '/^\[database\]/{flag=1; next} /^\[/{flag=0} flag && /^user/{gsub(/^[ \t]+|[ \t]+$/, "", $2); print $2; exit}' $CONFIG_FILE)
DB_PASSWORD=$(awk -F= '/^\[database\]/{flag=1; next} /^\[/{flag=0} flag && /^password/{gsub(/^[ \t]+|[ \t]+$/, "", $2); print $2; exit}' $CONFIG_FILE)
DB_NAME=$(awk -F= '/^\[database\]/{flag=1; next} /^\[/{flag=0} flag && /^database/{gsub(/^[ \t]+|[ \t]+$/, "", $2); print $2; exit}' $CONFIG_FILE)

# Set defaults if not found
DB_HOST=${DB_HOST:-127.0.0.1}
DB_PORT=${DB_PORT:-3306}
DB_USER=${DB_USER:-root}
DB_NAME=${DB_NAME:-lego}

echo "Database Configuration:"
echo "  Host: $DB_HOST"
echo "  Port: $DB_PORT"
echo "  User: $DB_USER"
echo "  Database: $DB_NAME"
echo ""

# Test database connection
echo "Testing database connection..."
mysql -h "$DB_HOST" -P "$DB_PORT" -u "$DB_USER" -p"$DB_PASSWORD" -e "SELECT 1" > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to connect to database"
    echo "Please check your config.ini credentials"
    exit 1
fi
echo "✓ Database connection successful"
echo ""

# Step 1: Create summary tables
echo "========================================================================"
echo "Step 1: Creating Summary Tables"
echo "========================================================================"
echo ""
echo "This will create three summary tables:"
echo "  - financials_summary_monthly_asin_marketplace"
echo "  - financials_summary_monthly_brand"
echo "  - financials_summary_monthly_category"
echo ""
read -p "Continue? (y/n) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted"
    exit 1
fi

mysql -h "$DB_HOST" -P "$DB_PORT" -u "$DB_USER" -p"$DB_PASSWORD" "$DB_NAME" < create_summary_tables.sql
echo ""
echo "✓ Summary tables created"
echo ""

# Step 2: Populate summary tables
echo "========================================================================"
echo "Step 2: Populating Summary Tables"
echo "========================================================================"
echo ""
echo "This will populate the summary tables with your existing data."
echo "This may take 5-15 minutes for large datasets (68M+ rows)."
echo ""
read -p "Continue? (y/n) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Skipped. You can run this later with: python3 refresh_summaries.py"
    exit 0
fi

echo ""
python3 refresh_summaries.py
echo ""

# Step 3: Verify setup
echo "========================================================================"
echo "Step 3: Verifying Setup"
echo "========================================================================"
echo ""

# Check row counts
mysql -h "$DB_HOST" -P "$DB_PORT" -u "$DB_USER" -p"$DB_PASSWORD" "$DB_NAME" -e "
SELECT 
    'financials_summary_monthly_asin_marketplace' as table_name,
    COUNT(*) as row_count,
    MIN(month) as earliest_month,
    MAX(month) as latest_month
FROM financials_summary_monthly_asin_marketplace
UNION ALL
SELECT 
    'financials_summary_monthly_brand' as table_name,
    COUNT(*) as row_count,
    MIN(month) as earliest_month,
    MAX(month) as latest_month
FROM financials_summary_monthly_brand
UNION ALL
SELECT 
    'financials_summary_monthly_category' as table_name,
    COUNT(*) as row_count,
    MIN(month) as earliest_month,
    MAX(month) as latest_month
FROM financials_summary_monthly_category;
"

echo ""
echo "✓ Setup verification complete"
echo ""

# Step 4: Setup instructions
echo "========================================================================"
echo "Setup Complete! 🚀"
echo "========================================================================"
echo ""
echo "Next Steps:"
echo ""
echo "1. Restart your Flask application:"
echo "   cd .."
echo "   ./deploy_lego.sh"
echo ""
echo "2. Test the dashboard - it should now load in <1 second!"
echo ""
echo "3. Set up a daily cron job to refresh the summary tables:"
echo "   crontab -e"
echo ""
echo "   Add this line to run daily at 3 AM:"
echo "   0 3 * * * cd $SCRIPT_DIR && python3 refresh_summaries.py >> /tmp/lego_summary_refresh.log 2>&1"
echo ""
echo "4. Read the documentation for more details:"
echo "   cat PERFORMANCE_OPTIMIZATION.md"
echo ""
echo "========================================================================"

