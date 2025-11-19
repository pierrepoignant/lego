-- ================================================================
-- Refresh Summary Tables Script
-- ================================================================
-- This script populates/refreshes the pre-aggregated summary tables
-- Run this script:
--   - Initially after creating the summary tables
--   - Daily via cron job (recommended: 2-3 AM)
--   - After bulk imports of financial data
-- 
-- Execution time: ~5-10 minutes for 68M rows (first run)
--                 ~1-2 minutes for incremental updates
-- ================================================================

SET @start_time = NOW();
SELECT CONCAT('Starting summary table refresh at ', @start_time) as status;

-- ================================================================
-- 1. Refresh: financials_summary_monthly_asin_marketplace
-- ================================================================
-- This is the base summary - aggregate from raw financials to ASIN+marketplace level
-- Truncate and rebuild (faster than incremental on first run)
-- ================================================================

SELECT '1/3: Refreshing ASIN+Marketplace monthly summary...' as status;

TRUNCATE TABLE `financials_summary_monthly_asin_marketplace`;

INSERT INTO `financials_summary_monthly_asin_marketplace` 
    (asin_id, brand_id, category_id, marketplace, month, metric, value)
SELECT 
    f.asin_id,
    a.brand_id,
    b.category_id,
    f.marketplace,
    f.month,
    f.metric,
    SUM(f.value) as total_value
FROM financials f
INNER JOIN asin a ON f.asin_id = a.id
INNER JOIN brand b ON a.brand_id = b.id
WHERE (b.`group` IS NULL OR b.`group` != 'stock')
GROUP BY 
    f.asin_id,
    a.brand_id,
    b.category_id,
    f.marketplace,
    f.month,
    f.metric;

SELECT CONCAT('   - Inserted ', ROW_COUNT(), ' rows into asin+marketplace summary') as status;

-- ================================================================
-- 2. Refresh: financials_summary_monthly_brand
-- ================================================================
-- Aggregate by brand from the ASIN summary (much faster than from raw financials)
-- We create two versions: by marketplace AND an 'ALL' marketplace aggregate
-- ================================================================

SELECT '2/3: Refreshing Brand monthly summary...' as status;

TRUNCATE TABLE `financials_summary_monthly_brand`;

-- Insert by-marketplace aggregates
INSERT INTO `financials_summary_monthly_brand` 
    (brand_id, category_id, month, marketplace, metric, total_value, asin_count)
SELECT 
    brand_id,
    category_id,
    month,
    marketplace,
    metric,
    SUM(value) as total_value,
    COUNT(DISTINCT asin_id) as asin_count
FROM financials_summary_monthly_asin_marketplace
GROUP BY 
    brand_id,
    category_id,
    month,
    marketplace,
    metric;

SELECT CONCAT('   - Inserted ', ROW_COUNT(), ' by-marketplace rows') as status;

-- Insert 'ALL' marketplace aggregates (sum across all marketplaces)
INSERT INTO `financials_summary_monthly_brand` 
    (brand_id, category_id, month, marketplace, metric, total_value, asin_count)
SELECT 
    brand_id,
    category_id,
    month,
    'ALL' as marketplace,
    metric,
    SUM(value) as total_value,
    COUNT(DISTINCT asin_id) as asin_count
FROM financials_summary_monthly_asin_marketplace
GROUP BY 
    brand_id,
    category_id,
    month,
    metric;

SELECT CONCAT('   - Inserted ', ROW_COUNT(), ' ALL-marketplace rows') as status;

-- ================================================================
-- 3. Refresh: financials_summary_monthly_category
-- ================================================================
-- Aggregate by category from the brand summary
-- ================================================================

SELECT '3/3: Refreshing Category monthly summary...' as status;

TRUNCATE TABLE `financials_summary_monthly_category`;

INSERT INTO `financials_summary_monthly_category` 
    (category_id, month, metric, total_value, brand_count, asin_count)
SELECT 
    category_id,
    month,
    metric,
    SUM(total_value) as total_value,
    COUNT(DISTINCT brand_id) as brand_count,
    SUM(asin_count) as asin_count
FROM financials_summary_monthly_brand
WHERE marketplace = 'ALL'  -- Use the ALL marketplace aggregate to avoid double-counting
  AND category_id IS NOT NULL
GROUP BY 
    category_id,
    month,
    metric;

SELECT CONCAT('   - Inserted ', ROW_COUNT(), ' rows into category summary') as status;

-- ================================================================
-- Show completion stats
-- ================================================================

SET @end_time = NOW();
SET @duration = TIMESTAMPDIFF(SECOND, @start_time, @end_time);

SELECT 
    'Summary table refresh completed!' as status,
    @duration as duration_seconds,
    ROUND(@duration / 60, 2) as duration_minutes,
    @start_time as started_at,
    @end_time as completed_at;

-- Show row counts
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

