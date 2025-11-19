-- ================================================================
-- Compute Overstock Values for ASINs and Brands
-- ================================================================
-- This script computes:
-- 1. stock_overstock_unit = stock_units - (6-month forecast sum)
-- 2. stock_overstock_value = stock_overstock_unit * unit_COGS
-- 
-- 6-month period: Nov 2025, Dec 2025, Jan 2026, Feb 2026, Mar 2026, Apr 2026
-- ================================================================

SET @start_time = NOW();
SELECT '========================================' as status;
SELECT 'Computing Overstock Values' as status;
SELECT '========================================' as status;

-- ================================================================
-- 1. Update ASIN Overstock Values
-- ================================================================

SELECT '1/2: Computing ASIN overstock values...' as status;

UPDATE asin a
LEFT JOIN (
    SELECT 
        asin_id,
        SUM(value) as forecast_6m_units
    FROM forecast_asin
    WHERE metric = 'Net units'
    AND month IN (
        '2025-11-01', '2025-12-01', '2026-01-01', 
        '2026-02-01', '2026-03-01', '2026-04-01'
    )
    GROUP BY asin_id
) f ON a.id = f.asin_id
SET 
    a.stock_overstock_unit = GREATEST(
        0,
        a.stock_units - COALESCE(f.forecast_6m_units, 0)
    ),
    a.stock_overstock_value = CASE
        WHEN a.stock_units > 0 AND a.stock_value > 0 
             AND (a.stock_units - COALESCE(f.forecast_6m_units, 0)) > 0
        THEN (a.stock_units - COALESCE(f.forecast_6m_units, 0)) * (a.stock_value / a.stock_units)
        ELSE 0
    END
WHERE a.brand_id IS NOT NULL;

SELECT CONCAT('✓ Updated ', ROW_COUNT(), ' ASINs') as result;

-- Show ASIN statistics
SELECT 'ASIN Statistics:' as summary;
SELECT 
    COUNT(*) as total_asins,
    SUM(CASE WHEN stock_units = 0 THEN 1 ELSE 0 END) as zero_stock,
    SUM(CASE WHEN stock_overstock_unit = 0 THEN 1 ELSE 0 END) as no_overstock,
    SUM(CASE WHEN stock_overstock_unit > 0 THEN 1 ELSE 0 END) as has_overstock,
    CONCAT('$', FORMAT(SUM(stock_overstock_value), 2)) as total_overstock_value
FROM asin
WHERE brand_id IS NOT NULL;

-- ================================================================
-- 2. Update Brand Overstock Values
-- ================================================================

SELECT '2/2: Computing brand overstock values...' as status;

UPDATE brand b
LEFT JOIN (
    SELECT 
        brand_id,
        SUM(value) as forecast_6m_units
    FROM forecast_brand
    WHERE metric = 'Net units'
    AND month IN (
        '2025-11-01', '2025-12-01', '2026-01-01', 
        '2026-02-01', '2026-03-01', '2026-04-01'
    )
    GROUP BY brand_id
) f ON b.id = f.brand_id
SET 
    b.stock_overstock_unit = GREATEST(
        0,
        b.stock_units - COALESCE(f.forecast_6m_units, 0)
    ),
    b.stock_overstock_value = CASE
        WHEN b.stock_units > 0 AND b.stock_value > 0 
             AND (b.stock_units - COALESCE(f.forecast_6m_units, 0)) > 0
        THEN (b.stock_units - COALESCE(f.forecast_6m_units, 0)) * (b.stock_value / b.stock_units)
        ELSE 0
    END;

SELECT CONCAT('✓ Updated ', ROW_COUNT(), ' brands') as result;

-- Show brand statistics
SELECT 'Brand Statistics:' as summary;
SELECT 
    COUNT(*) as total_brands,
    SUM(CASE WHEN stock_units = 0 THEN 1 ELSE 0 END) as zero_stock,
    SUM(CASE WHEN stock_overstock_unit = 0 THEN 1 ELSE 0 END) as no_overstock,
    SUM(CASE WHEN stock_overstock_unit > 0 THEN 1 ELSE 0 END) as has_overstock,
    CONCAT('$', FORMAT(SUM(stock_overstock_value), 2)) as total_overstock_value
FROM brand;

-- ================================================================
-- Completion Summary
-- ================================================================

SET @end_time = NOW();
SET @duration = TIMESTAMPDIFF(SECOND, @start_time, @end_time);

SELECT '========================================' as completion;
SELECT 'Overstock Computation Completed!' as status;
SELECT '========================================' as line;

SELECT 
    @duration as duration_seconds,
    @start_time as started_at,
    @end_time as completed_at;

SELECT '✓ All overstock values computed successfully!' as final_status;

