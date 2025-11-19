-- ================================================================
-- Update LTM and L3M Metrics in ASIN and BRAND Tables
-- ================================================================
-- LTM Period: November 2024 - October 2025 (12 months)
-- L3M Period: August 2025 - October 2025 (3 months)
-- ================================================================

SET @start_time = NOW();
SELECT 'Starting LTM and L3M metrics update...' as status;

-- ================================================================
-- PART 1: UPDATE ASIN TABLE METRICS
-- ================================================================

-- ================================================================
-- 1. Update LTM Revenues (ASIN)
-- ================================================================
SELECT '1/13: Updating ASIN LTM Revenues...' as status;

UPDATE asin a
LEFT JOIN (
    SELECT 
        f.asin_id,
        SUM(f.value) as ltm_revenue
    FROM financials f
    WHERE LOWER(f.metric) = 'net revenue'
      AND (
          (YEAR(f.month) = 2024 AND MONTH(f.month) >= 11) OR
          (YEAR(f.month) = 2025 AND MONTH(f.month) <= 10)
      )
    GROUP BY f.asin_id
) rev ON a.id = rev.asin_id
SET a.ltm_revenues = COALESCE(rev.ltm_revenue, 0),
    a.ltm_updated_at = NOW();

SELECT CONCAT('✓ Updated ltm_revenues for ', ROW_COUNT(), ' ASINs') as result;

-- ================================================================
-- 2. Update LTM Units (ASIN)
-- ================================================================
SELECT '2/13: Updating ASIN LTM Units...' as status;

UPDATE asin a
LEFT JOIN (
    SELECT 
        f.asin_id,
        SUM(f.value) as ltm_units_val
    FROM financials f
    WHERE LOWER(f.metric) = 'net units'
      AND (
          (YEAR(f.month) = 2024 AND MONTH(f.month) >= 11) OR
          (YEAR(f.month) = 2025 AND MONTH(f.month) <= 10)
      )
    GROUP BY f.asin_id
) units ON a.id = units.asin_id
SET a.ltm_units = COALESCE(units.ltm_units_val, 0),
    a.ltm_updated_at = NOW();

SELECT CONCAT('✓ Updated ltm_units for ', ROW_COUNT(), ' ASINs') as result;

-- ================================================================
-- 3. Update LTM CM3 (ASIN)
-- ================================================================
SELECT '3/13: Updating ASIN LTM CM3...' as status;

UPDATE asin a
LEFT JOIN (
    SELECT 
        f.asin_id,
        SUM(f.value) as ltm_cm3_val
    FROM financials f
    WHERE LOWER(f.metric) = 'cm3'
      AND (
          (YEAR(f.month) = 2024 AND MONTH(f.month) >= 11) OR
          (YEAR(f.month) = 2025 AND MONTH(f.month) <= 10)
      )
    GROUP BY f.asin_id
) cm3 ON a.id = cm3.asin_id
SET a.ltm_cm3 = COALESCE(cm3.ltm_cm3_val, 0),
    a.ltm_updated_at = NOW();

SELECT CONCAT('✓ Updated ltm_cm3 for ', ROW_COUNT(), ' ASINs') as result;

-- ================================================================
-- 4. Update LTM Brand EBITDA % (ASIN)
-- ================================================================
SELECT '4/13: Updating ASIN LTM Brand EBITDA %...' as status;

UPDATE asin a
LEFT JOIN (
    SELECT 
        f.asin_id,
        SUM(CASE WHEN LOWER(f.metric) = 'net revenue' THEN f.value ELSE 0 END) as ltm_revenue,
        SUM(CASE WHEN LOWER(f.metric) = 'cm3' THEN f.value ELSE 0 END) as ltm_cm3
    FROM financials f
    WHERE (LOWER(f.metric) = 'net revenue' OR LOWER(f.metric) = 'cm3')
      AND (
          (YEAR(f.month) = 2024 AND MONTH(f.month) >= 11) OR
          (YEAR(f.month) = 2025 AND MONTH(f.month) <= 10)
      )
    GROUP BY f.asin_id
    HAVING ltm_revenue > 0
) ebitda ON a.id = ebitda.asin_id
SET a.ltm_brand_ebitda = CASE 
    WHEN ebitda.ltm_revenue > 0 THEN (ebitda.ltm_cm3 / ebitda.ltm_revenue * 100)
    ELSE 0
END,
    a.ltm_updated_at = NOW();

SELECT CONCAT('✓ Updated ltm_brand_ebitda for ', ROW_COUNT(), ' ASINs') as result;

-- ================================================================
-- 5. Update LTM Stock Value (ASIN)
-- ================================================================
SELECT '5/13: Updating ASIN LTM Stock Value...' as status;

UPDATE asin a
LEFT JOIN (
    SELECT 
        s.asin_id,
        SUM(s.value) as ltm_stock_val
    FROM stock s
    WHERE (
          (YEAR(s.month) = 2024 AND MONTH(s.month) >= 11) OR
          (YEAR(s.month) = 2025 AND MONTH(s.month) <= 10)
      )
      AND s.asin_id IS NOT NULL
    GROUP BY s.asin_id
) stock ON a.id = stock.asin_id
SET a.stock_value = COALESCE(stock.ltm_stock_val, 0),
    a.ltm_updated_at = NOW();

SELECT CONCAT('✓ Updated stock_value for ', ROW_COUNT(), ' ASINs') as result;

-- ================================================================
-- 6. Update LTM Stock Units (ASIN)
-- ================================================================
SELECT '6/13: Updating ASIN LTM Stock Units...' as status;

UPDATE asin a
LEFT JOIN (
    SELECT 
        s.asin_id,
        SUM(s.quantity) as stock_units_val
    FROM stock s
    WHERE (
          (YEAR(s.month) = 2024 AND MONTH(s.month) >= 11) OR
          (YEAR(s.month) = 2025 AND MONTH(s.month) <= 10)
      )
      AND s.asin_id IS NOT NULL
    GROUP BY s.asin_id
) stock_units ON a.id = stock_units.asin_id
SET a.stock_units = COALESCE(stock_units.stock_units_val, 0),
    a.ltm_updated_at = NOW();

SELECT CONCAT('✓ Updated stock_units for ', ROW_COUNT(), ' ASINs') as result;

-- ================================================================
-- 7. Update L3M Units (ASIN) - Aug, Sep, Oct 2025
-- ================================================================
SELECT '7/13: Updating ASIN L3M Units...' as status;

UPDATE asin a
LEFT JOIN (
    SELECT 
        f.asin_id,
        SUM(f.value) as l3m_units_val
    FROM financials f
    WHERE LOWER(f.metric) = 'net units'
      AND YEAR(f.month) = 2025 
      AND MONTH(f.month) IN (8, 9, 10)
    GROUP BY f.asin_id
) l3m_units ON a.id = l3m_units.asin_id
SET a.l3m_units = COALESCE(l3m_units.l3m_units_val, 0),
    a.ltm_updated_at = NOW();

SELECT CONCAT('✓ Updated l3m_units for ', ROW_COUNT(), ' ASINs') as result;

-- ================================================================
-- 8. Update L3M Revenues (ASIN) - Aug, Sep, Oct 2025
-- ================================================================
SELECT '8/13: Updating ASIN L3M Revenues...' as status;

UPDATE asin a
LEFT JOIN (
    SELECT 
        f.asin_id,
        SUM(f.value) as l3m_revenues_val
    FROM financials f
    WHERE LOWER(f.metric) = 'net revenue'
      AND YEAR(f.month) = 2025 
      AND MONTH(f.month) IN (8, 9, 10)
    GROUP BY f.asin_id
) l3m_rev ON a.id = l3m_rev.asin_id
SET a.l3m_revenues = COALESCE(l3m_rev.l3m_revenues_val, 0),
    a.ltm_updated_at = NOW();

SELECT CONCAT('✓ Updated l3m_revenues for ', ROW_COUNT(), ' ASINs') as result;

-- ================================================================
-- 9. Update L3M CM3 (ASIN) - Aug, Sep, Oct 2025
-- ================================================================
SELECT '9/13: Updating ASIN L3M CM3...' as status;

UPDATE asin a
LEFT JOIN (
    SELECT 
        f.asin_id,
        SUM(f.value) as l3m_cm3_val
    FROM financials f
    WHERE LOWER(f.metric) = 'cm3'
      AND YEAR(f.month) = 2025 
      AND MONTH(f.month) IN (8, 9, 10)
    GROUP BY f.asin_id
) l3m_cm3 ON a.id = l3m_cm3.asin_id
SET a.l3m_cm3 = COALESCE(l3m_cm3.l3m_cm3_val, 0),
    a.ltm_updated_at = NOW();

SELECT CONCAT('✓ Updated l3m_cm3 for ', ROW_COUNT(), ' ASINs') as result;

-- ================================================================
-- PART 2: UPDATE BRAND TABLE METRICS
-- ================================================================

-- ================================================================
-- 10. Update LTM Revenues (BRAND)
-- ================================================================
SELECT '10/13: Updating BRAND LTM Revenues...' as status;

UPDATE brand b
LEFT JOIN (
    SELECT 
        a.brand_id,
        SUM(a.ltm_revenues) as brand_ltm_revenue
    FROM asin a
    WHERE a.brand_id IS NOT NULL
    GROUP BY a.brand_id
) rev ON b.id = rev.brand_id
SET b.ltm_revenues = COALESCE(rev.brand_ltm_revenue, 0),
    b.ltm_updated_at = NOW();

SELECT CONCAT('✓ Updated ltm_revenues for ', ROW_COUNT(), ' brands') as result;

-- ================================================================
-- 11. Update LTM Units (BRAND)
-- ================================================================
SELECT '11/13: Updating BRAND LTM Units...' as status;

UPDATE brand b
LEFT JOIN (
    SELECT 
        a.brand_id,
        SUM(a.ltm_units) as brand_ltm_units
    FROM asin a
    WHERE a.brand_id IS NOT NULL
    GROUP BY a.brand_id
) units ON b.id = units.brand_id
SET b.ltm_units = COALESCE(units.brand_ltm_units, 0),
    b.ltm_updated_at = NOW();

SELECT CONCAT('✓ Updated ltm_units for ', ROW_COUNT(), ' brands') as result;

-- ================================================================
-- 12. Update LTM CM3 (BRAND)
-- ================================================================
SELECT '12/13: Updating BRAND LTM CM3...' as status;

UPDATE brand b
LEFT JOIN (
    SELECT 
        a.brand_id,
        SUM(a.ltm_cm3) as brand_ltm_cm3
    FROM asin a
    WHERE a.brand_id IS NOT NULL
    GROUP BY a.brand_id
) cm3 ON b.id = cm3.brand_id
SET b.ltm_cm3 = COALESCE(cm3.brand_ltm_cm3, 0),
    b.ltm_updated_at = NOW();

SELECT CONCAT('✓ Updated ltm_cm3 for ', ROW_COUNT(), ' brands') as result;

-- ================================================================
-- 13. Update LTM Brand EBITDA % (BRAND)
-- ================================================================
SELECT '13/13: Updating BRAND LTM Brand EBITDA %...' as status;

UPDATE brand b
SET b.ltm_brand_ebitda = CASE 
    WHEN b.ltm_revenues > 0 THEN (b.ltm_cm3 / b.ltm_revenues * 100)
    ELSE 0
END,
    b.ltm_updated_at = NOW()
WHERE b.ltm_revenues IS NOT NULL;

SELECT CONCAT('✓ Updated ltm_brand_ebitda for ', ROW_COUNT(), ' brands') as result;

-- ================================================================
-- 14. Update LTM Stock Value (BRAND)
-- ================================================================
SELECT '14/13: Updating BRAND LTM Stock Value...' as status;

UPDATE brand b
LEFT JOIN (
    SELECT 
        a.brand_id,
        SUM(a.stock_value) as brand_stock
    FROM asin a
    WHERE a.brand_id IS NOT NULL
    GROUP BY a.brand_id
) stock ON b.id = stock.brand_id
SET b.stock_value = COALESCE(stock.brand_stock, 0),
    b.ltm_updated_at = NOW();

SELECT CONCAT('✓ Updated stock_value for ', ROW_COUNT(), ' brands') as result;

-- ================================================================
-- 15. Update LTM Stock Units (BRAND)
-- ================================================================
SELECT '15/13: Updating BRAND LTM Stock Units...' as status;

UPDATE brand b
LEFT JOIN (
    SELECT 
        a.brand_id,
        SUM(a.stock_units) as brand_stock_units
    FROM asin a
    WHERE a.brand_id IS NOT NULL
    GROUP BY a.brand_id
) stock_units ON b.id = stock_units.brand_id
SET b.stock_units = COALESCE(stock_units.brand_stock_units, 0),
    b.ltm_updated_at = NOW();

SELECT CONCAT('✓ Updated stock_units for ', ROW_COUNT(), ' brands') as result;

-- ================================================================
-- 16. Update L3M Units (BRAND)
-- ================================================================
SELECT '16/13: Updating BRAND L3M Units...' as status;

UPDATE brand b
LEFT JOIN (
    SELECT 
        a.brand_id,
        SUM(a.l3m_units) as brand_l3m_units
    FROM asin a
    WHERE a.brand_id IS NOT NULL
    GROUP BY a.brand_id
) l3m_units ON b.id = l3m_units.brand_id
SET b.l3m_units = COALESCE(l3m_units.brand_l3m_units, 0),
    b.ltm_updated_at = NOW();

SELECT CONCAT('✓ Updated l3m_units for ', ROW_COUNT(), ' brands') as result;

-- ================================================================
-- 17. Update L3M Revenues (BRAND)
-- ================================================================
SELECT '17/13: Updating BRAND L3M Revenues...' as status;

UPDATE brand b
LEFT JOIN (
    SELECT 
        a.brand_id,
        SUM(a.l3m_revenues) as brand_l3m_revenues
    FROM asin a
    WHERE a.brand_id IS NOT NULL
    GROUP BY a.brand_id
) l3m_rev ON b.id = l3m_rev.brand_id
SET b.l3m_revenues = COALESCE(l3m_rev.brand_l3m_revenues, 0),
    b.ltm_updated_at = NOW();

SELECT CONCAT('✓ Updated l3m_revenues for ', ROW_COUNT(), ' brands') as result;

-- ================================================================
-- 18. Update L3M CM3 (BRAND)
-- ================================================================
SELECT '18/13: Updating BRAND L3M CM3...' as status;

UPDATE brand b
LEFT JOIN (
    SELECT 
        a.brand_id,
        SUM(a.l3m_cm3) as brand_l3m_cm3
    FROM asin a
    WHERE a.brand_id IS NOT NULL
    GROUP BY a.brand_id
) l3m_cm3 ON b.id = l3m_cm3.brand_id
SET b.l3m_cm3 = COALESCE(l3m_cm3.brand_l3m_cm3, 0),
    b.ltm_updated_at = NOW();

SELECT CONCAT('✓ Updated l3m_cm3 for ', ROW_COUNT(), ' brands') as result;

-- ================================================================
-- Show completion stats
-- ================================================================

SET @end_time = NOW();
SET @duration = TIMESTAMPDIFF(SECOND, @start_time, @end_time);

SELECT '========================================' as completion;
SELECT 'LTM and L3M Metrics Update Complete!' as status;
SELECT '========================================' as line;

SELECT 
    @duration as duration_seconds,
    ROUND(@duration / 60, 2) as duration_minutes,
    @start_time as started_at,
    @end_time as completed_at;

-- Show summary statistics
SELECT 'ASIN Summary Statistics:' as summary;

SELECT 
    COUNT(*) as total_asins,
    COUNT(CASE WHEN ltm_revenues > 0 THEN 1 END) as asins_with_revenue,
    COUNT(CASE WHEN ltm_units > 0 THEN 1 END) as asins_with_units,
    COUNT(CASE WHEN ltm_cm3 > 0 THEN 1 END) as asins_with_cm3,
    COUNT(CASE WHEN l3m_revenues > 0 THEN 1 END) as asins_with_l3m_revenue,
    COUNT(CASE WHEN l3m_units > 0 THEN 1 END) as asins_with_l3m_units,
    SUM(ltm_revenues) as total_ltm_revenue,
    SUM(ltm_units) as total_ltm_units,
    SUM(ltm_cm3) as total_ltm_cm3,
    SUM(l3m_revenues) as total_l3m_revenue,
    SUM(l3m_units) as total_l3m_units,
    SUM(l3m_cm3) as total_l3m_cm3,
    AVG(ltm_brand_ebitda) as avg_ltm_ebitda,
    SUM(stock_value) as total_stock_value,
    SUM(stock_units) as total_stock_units
FROM asin;

SELECT 'BRAND Summary Statistics:' as summary;

SELECT 
    COUNT(*) as total_brands,
    COUNT(CASE WHEN ltm_revenues > 0 THEN 1 END) as brands_with_revenue,
    COUNT(CASE WHEN ltm_units > 0 THEN 1 END) as brands_with_units,
    COUNT(CASE WHEN l3m_revenues > 0 THEN 1 END) as brands_with_l3m_revenue,
    SUM(ltm_revenues) as total_ltm_revenue,
    SUM(ltm_units) as total_ltm_units,
    SUM(ltm_cm3) as total_ltm_cm3,
    SUM(l3m_revenues) as total_l3m_revenue,
    SUM(l3m_units) as total_l3m_units,
    SUM(l3m_cm3) as total_l3m_cm3,
    AVG(ltm_brand_ebitda) as avg_ltm_ebitda,
    SUM(stock_value) as total_stock_value,
    SUM(stock_units) as total_stock_units
FROM brand;

SELECT '✓ All LTM and L3M metrics updated successfully!' as final_status;
SELECT 'ASINs and brands with ltm_updated_at timestamp have been processed' as note;
