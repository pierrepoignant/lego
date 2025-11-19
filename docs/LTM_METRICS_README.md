# LTM (Last Twelve Months) Metrics System

## Overview

This system pre-computes financial metrics for both **ASINs and Brands** to improve page load performance. Instead of calculating metrics on-the-fly, we store pre-computed values in the database using the optimized summary tables.

**LTM Period**: November 2024 - October 2025

## Metrics Computed

### For ASINs
1. **ltm_revenues** - Total Net revenue for the LTM period (from `financials_summary_monthly_asin_marketplace`)
2. **ltm_brand_ebitda** - Brand EBITDA percentage: (CM3 / Net revenue) × 100 (from `financials_summary_monthly_asin_marketplace`)
3. **stock_value** - Total inventory/stock value for the LTM period (from `stock` table)

### For Brands
1. **ltm_revenues** - Total Net revenue across all ASINs for the LTM period (from `financials_summary_monthly_brand`)
2. **ltm_brand_ebitda** - Brand EBITDA percentage: (CM3 / Net revenue) × 100 (from `financials_summary_monthly_brand`)
3. **stock_value** - Total inventory/stock value across all ASINs for the LTM period (from `stock` table)

## Setup Instructions

### 1. Add Database Columns

Run the SQL migrations to add the new columns to both the `asin` and `brand` tables:

```bash
# For ASINs
mysql -u [username] -p [database] < database/add_ltm_columns.sql

# For Brands  
mysql -u [username] -p [database] < database/add_brand_ltm_columns.sql
```

Or manually:

```sql
source database/add_ltm_columns.sql
source database/add_brand_ltm_columns.sql
```

### 2. Initial Computation

Run the computation script to populate the LTM metrics for all ASINs and Brands:

```bash
python3 compute_ltm_metrics.py
```

This will:
- Process all ASINs in the database (using `financials_summary_monthly_asin_marketplace` for revenues/EBITDA)
- Process all Brands in the database (using `financials_summary_monthly_brand` for revenues/EBITDA)
- Get stock data directly from the `stock` table (aggregated by asin_id and brand_id)
- Calculate LTM metrics from pre-aggregated data (FAST!)
- Update the `asin` and `brand` tables with computed values
- Show progress and summary statistics

**Expected runtime**: ~30-60 seconds for 43,000+ ASINs and 400+ brands (uses optimized queries!)

**Note**: Stock data comes from the `stock` table, not from financials. The stock table has its own `value` field that represents inventory value.

### 3. Regular Updates

You should run the computation script regularly to keep metrics up-to-date:

**Option A: Manual**
```bash
python3 compute_ltm_metrics.py
```

**Option B: Cron Job (Recommended)**

Add to your crontab to run daily at 2 AM:

```bash
# Edit crontab
crontab -e

# Add this line:
0 2 * * * cd /path/to/lego && python3 compute_ltm_metrics.py >> logs/ltm_metrics.log 2>&1
```

**Option C: After Data Import**

Run after importing new financial data:

```bash
# Import your data
python3 database/import_financials.py

# Then recompute metrics
python3 compute_ltm_metrics.py
```

## Performance Improvements

### Before (Slow)
- Query computed Oct 2025 revenue on-the-fly using JOINs and SUM aggregations
- **Page load**: 5-10+ seconds for brands with many ASINs
- Database load: High

### After (Fast)
- Query reads pre-computed values directly from `asin` table
- **Page load**: <1 second
- Database load: Minimal

## Updated Features

### Brand ASIN Page
The `/brand/<id>/asins` page now displays:
- **LTM Revenue** - Total revenue for Nov 2024 - Oct 2025
- **LTM EBITDA %** - Profitability margin (color-coded: green = positive, red = negative)
- **LTM Stock** - Inventory value

ASINs are ordered by **LTM Revenue** (highest first) instead of single month revenue.

## Troubleshooting

### Issue: Script fails with "column doesn't exist"
**Solution**: Run the SQL migration first to add the columns

```bash
mysql -u [username] -p [database] < database/add_ltm_columns.sql
```

### Issue: All metrics show $0 or 0%
**Solution**: Check if financial data exists for the LTM period (Nov 2024 - Oct 2025)

```sql
SELECT COUNT(*) FROM financials 
WHERE (YEAR(month) = 2024 AND MONTH(month) >= 11)
   OR (YEAR(month) = 2025 AND MONTH(month) <= 10);
```

### Issue: Metrics are outdated
**Solution**: Run the computation script again

```bash
python3 compute_ltm_metrics.py
```

Check when metrics were last updated:

```sql
SELECT 
    COUNT(*) as total_asins,
    MAX(ltm_updated_at) as last_update,
    MIN(ltm_updated_at) as oldest_update
FROM asin
WHERE ltm_updated_at IS NOT NULL;
```

## Monitoring

### Check Computation Status

```sql
-- ASINs with computed metrics
SELECT COUNT(*) FROM asin WHERE ltm_revenues > 0;

-- Total LTM revenue
SELECT SUM(ltm_revenues) as total FROM asin;

-- Top 10 ASINs by revenue
SELECT asin, ltm_revenues, ltm_brand_ebitda 
FROM asin 
ORDER BY ltm_revenues DESC 
LIMIT 10;

-- Last update time
SELECT MAX(ltm_updated_at) as last_computed FROM asin;
```

## Files

- `database/add_ltm_columns.sql` - SQL migration to add columns
- `compute_ltm_metrics.py` - Python script to compute and update metrics
- `flask_app.py` - Updated to use pre-computed values
- `templates/brand_asins.html` - Updated to display LTM metrics

## Notes

- The LTM period is fixed (Nov 2024 - Oct 2025)
- Metrics are only as current as your financial data
- Recompute after importing new financial data
- The script can be run multiple times safely (it updates existing values)

