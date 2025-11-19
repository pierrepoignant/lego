# Streamlit Dashboard Optimization Update

**Date:** November 17, 2025

## Summary

Updated `streamlit_app.py` to use the pre-aggregated financial summary tables instead of querying the raw `financials` table directly. This brings the Streamlit dashboards in line with the Flask app optimizations and dramatically improves performance.

## Changes Made

### Functions Updated in `streamlit_app.py`

1. **`get_metrics()`**
   - **Before:** Queried `financials` table directly
   - **After:** Queries `financials_summary_monthly_brand` table
   - **Benefit:** Faster metric list retrieval

2. **`get_marketplaces()`**
   - **Before:** Queried `financials` table directly
   - **After:** Queries `financials_summary_monthly_brand` table (excluding 'ALL' aggregate)
   - **Benefit:** Faster marketplace list retrieval

3. **`get_financial_data()`** (v3 → v4)
   - **Before:** Complex query joining `financials` → `asin` → `brand` tables (68M+ rows)
   - **After:** Direct query to `financials_summary_monthly_brand` table (~10-50K rows)
   - **Benefit:** Massive performance improvement for Performance Comparison dashboard
   - **Key improvement:** Now uses pre-aggregated `total_value` field and 'ALL' marketplace aggregate

4. **`get_brand_exploration_data()`**
   - **Before:** Joined `brand` → `asin` → `financials` with complex aggregations
   - **After:** Joins `brand` → `financials_summary_monthly_brand` with simple aggregations
   - **Benefit:** Faster Brand Exploration page loads
   - **Key improvement:** Uses marketplace='ALL' aggregate to avoid double-counting

5. **`get_category_exploration_data()`**
   - **Before:** Joined `financials` → `asin` → `brand` → `category` with aggregations
   - **After:** Queries `financials_summary_monthly_category` table directly
   - **Benefit:** Fastest possible category exploration
   - **Key improvement:** Uses dedicated category summary table optimized for this exact use case

## Performance Impact

### Expected Improvements
- **Before:** Dashboard load time: 30-120+ seconds (depending on filters)
- **After:** Dashboard load time: <1 second 🚀

### Query Complexity Reduction
- **Raw financials queries:** Scanning 68M+ rows with multiple joins
- **Summary table queries:** Scanning 10-50K rows (brand) or 500-2K rows (category)
- **Result:** ~1000x reduction in data scanned

## Summary Table Architecture

```
┌─────────────────────┐
│  financials table   │  ← Raw data (68M rows) - used by flask_app
│  (68M+ rows)        │    Only for very specific queries
└──────────┬──────────┘
           │
           │ Daily refresh (refresh_summary_tables.sql)
           ▼
┌──────────────────────────────────────┐
│ financials_summary_monthly_asin_...  │  ← ASIN level (1-2M rows)
└──────────┬───────────────────────────┘    Used for detailed drill-downs
           │
           │ Aggregates by brand
           ▼
┌──────────────────────────────────────┐
│ financials_summary_monthly_brand     │  ← Brand level (10-50K rows)
└──────────┬───────────────────────────┘    Used by streamlit_app.py
           │                                 and flask_app.py
           │ Aggregates by category
           ▼
┌──────────────────────────────────────┐
│ financials_summary_monthly_category  │  ← Category level (500-2K rows)
└──────────────────────────────────────┘    Used by category exploration
```

## Other Files Checked

- ✅ **flask_app.py** - Already using summary tables (previously optimized)
- ✅ **scrape_asins.py** - Already using summary tables
- ✅ **compute_ltm_metrics.py** - Already using summary tables
- ℹ️ **summary_report.py** - Still uses raw `financials` (intentional - it's a DB stats utility, not a dashboard)
- ℹ️ **deployment_dashboard.py** - Doesn't query any financial tables (it's a DevOps dashboard)

## Maintenance Notes

1. **Summary tables must be refreshed regularly** using:
   ```bash
   mysql -u root -p lego < database/refresh_summary_tables.sql
   ```
   Or via the Python script:
   ```bash
   python database/refresh_summaries.py
   ```

2. **Cache clearing:** Users may need to clear Streamlit cache to see updated data:
   - Use the "🔄 Clear Cache" button in the sidebar
   - Or restart the Streamlit app

3. **Data consistency:** All dashboards now query from the same source (summary tables), ensuring consistent data across Flask and Streamlit dashboards.

## Testing Recommendations

1. Test all three dashboard views:
   - Performance Comparison
   - Brand Exploration
   - Category Exploration

2. Test with various filters:
   - Different brands
   - Different categories
   - Different marketplaces
   - Multiple metrics

3. Verify data consistency between Flask and Streamlit dashboards

4. Monitor query performance in production

## Rollback Plan

If issues arise, revert the following functions in `streamlit_app.py`:
- `get_metrics()` - line 114
- `get_marketplaces()` - line 124
- `get_financial_data()` - line 134
- `get_brand_exploration_data()` - line 348
- `get_category_exploration_data()` - line 422

The git history contains the previous working versions.

