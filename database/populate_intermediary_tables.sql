-- ================================================================
-- Populate Summary Tables Script
-- ================================================================
-- This script populates the three pre-aggregated summary tables
-- Run this after creating the tables or to refresh the data
-- 
-- Execution time: ~15-20 minutes for 68M rows (first run)
-- ================================================================

SET @start_time = NOW();
SELECT CONCAT('Starting summary table population at ', @start_time) as status;

-- ================================================================
-- Step 1: Populate financials_summary_monthly_asin_marketplace
-- ================================================================
-- Aggregate from raw financials table (68M rows) to ASIN level
-- ================================================================

SELECT '1/3: Populating ASIN+Marketplace monthly summary...' as status;
SELECT 'This will take 10-15 minutes...' as note;

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

SELECT CONCAT('✓ Inserted ', ROW_COUNT(), ' rows into ASIN summary table') as status;

-- ================================================================
-- Step 2: Populate financials_summary_monthly_brand
-- ================================================================
-- Aggregate from ASIN table to brand level (much faster!)
-- Creates both per-marketplace AND 'ALL' marketplace aggregates
-- ================================================================

SELECT '2/3: Populating Brand monthly summary...' as status;
SELECT 'This will take 2-3 minutes...' as note;

TRUNCATE TABLE `financials_summary_monthly_brand`;

-- Insert per-marketplace aggregates
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

SELECT CONCAT('✓ Inserted ', ROW_COUNT(), ' per-marketplace rows') as status;

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

SELECT CONCAT('✓ Inserted ', ROW_COUNT(), ' ALL-marketplace rows') as status;

-- ================================================================
-- Step 3: Populate financials_summary_monthly_category
-- ================================================================
-- Aggregate from brand table to category level (very fast!)
-- ================================================================

SELECT '3/3: Populating Category monthly summary...' as status;

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
WHERE marketplace = 'ALL'  -- Use ALL marketplace to avoid double-counting
  AND category_id IS NOT NULL
GROUP BY 
    category_id,
    month,
    metric;

SELECT CONCAT('✓ Inserted ', ROW_COUNT(), ' rows into category summary') as status;

-- ================================================================
-- Show completion stats
-- ================================================================

SET @end_time = NOW();
SET @duration = TIMESTAMPDIFF(SECOND, @start_time, @end_time);

SELECT '' as separator;
SELECT '========================================' as completion;
SELECT 'Summary Tables Population Complete!' as status;
SELECT '========================================' as completion;
SELECT '' as separator;

SELECT 
    @duration as duration_seconds,
    ROUND(@duration / 60, 2) as duration_minutes,
    @start_time as started_at,
    @end_time as completed_at;

-- Show final row counts for verification
SELECT '' as separator;
SELECT 'Final Row Counts:' as verification;
SELECT '' as separator;

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

SELECT '' as separator;
SELECT '✓ All summary tables populated successfully!' as final_status;
SELECT 'Next step: Restart Flask app and test dashboard' as next_action;

