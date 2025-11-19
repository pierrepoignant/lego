-- ================================================================
-- Add L3M and LTM Units Columns to ASIN and BRAND Tables
-- ================================================================
-- L3M = Last 3 Months (Aug-Sep-Oct 2025)
-- LTM = Last 12 Months (Nov 2024 - Oct 2025)
-- ================================================================

SET @start_time = NOW();
SELECT 'Adding L3M and LTM Units columns...' as status;

-- ================================================================
-- 1. Add columns to ASIN table
-- ================================================================

SELECT '1/2: Adding columns to ASIN table...' as status;

-- Add L3M columns (only if they don't exist)
SET @dbname = DATABASE();
SET @tablename = 'asin';

SET @col_exists = (SELECT COUNT(*) FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=@dbname AND TABLE_NAME=@tablename AND COLUMN_NAME='l3m_units');
SET @sqlstmt = IF(@col_exists = 0, 'ALTER TABLE asin ADD COLUMN l3m_units DECIMAL(15, 2) DEFAULT 0 COMMENT ''Last 3 months units (Aug-Sep-Oct 2025)''', 'SELECT ''Column l3m_units already exists'' as info');
PREPARE stmt FROM @sqlstmt;
EXECUTE stmt;

SET @col_exists = (SELECT COUNT(*) FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=@dbname AND TABLE_NAME=@tablename AND COLUMN_NAME='l3m_revenues');
SET @sqlstmt = IF(@col_exists = 0, 'ALTER TABLE asin ADD COLUMN l3m_revenues DECIMAL(15, 2) DEFAULT 0 COMMENT ''Last 3 months revenues (Aug-Sep-Oct 2025)''', 'SELECT ''Column l3m_revenues already exists'' as info');
PREPARE stmt FROM @sqlstmt;
EXECUTE stmt;

SET @col_exists = (SELECT COUNT(*) FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=@dbname AND TABLE_NAME=@tablename AND COLUMN_NAME='l3m_cm3');
SET @sqlstmt = IF(@col_exists = 0, 'ALTER TABLE asin ADD COLUMN l3m_cm3 DECIMAL(15, 2) DEFAULT 0 COMMENT ''Last 3 months CM3 (Aug-Sep-Oct 2025)''', 'SELECT ''Column l3m_cm3 already exists'' as info');
PREPARE stmt FROM @sqlstmt;
EXECUTE stmt;

-- Add LTM units and stock units columns (only if they don't exist)
SET @col_exists = (SELECT COUNT(*) FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=@dbname AND TABLE_NAME=@tablename AND COLUMN_NAME='ltm_units');
SET @sqlstmt = IF(@col_exists = 0, 'ALTER TABLE asin ADD COLUMN ltm_units DECIMAL(15, 2) DEFAULT 0 COMMENT ''Last 12 months units (Nov 2024 - Oct 2025)''', 'SELECT ''Column ltm_units already exists'' as info');
PREPARE stmt FROM @sqlstmt;
EXECUTE stmt;

SET @col_exists = (SELECT COUNT(*) FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=@dbname AND TABLE_NAME=@tablename AND COLUMN_NAME='ltm_stock_units');
SET @sqlstmt = IF(@col_exists = 0, 'ALTER TABLE asin ADD COLUMN ltm_stock_units DECIMAL(15, 2) DEFAULT 0 COMMENT ''Last 12 months stock units (Nov 2024 - Oct 2025)''', 'SELECT ''Column ltm_stock_units already exists'' as info');
PREPARE stmt FROM @sqlstmt;
EXECUTE stmt;

SELECT '✓ ASIN columns added successfully!' as result;

-- ================================================================
-- 2. Add columns to BRAND table
-- ================================================================

SELECT '2/2: Adding columns to BRAND table...' as status;

-- Add L3M columns to brand table (only if they don't exist)
SET @tablename = 'brand';

SET @col_exists = (SELECT COUNT(*) FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=@dbname AND TABLE_NAME=@tablename AND COLUMN_NAME='l3m_units');
SET @sqlstmt = IF(@col_exists = 0, 'ALTER TABLE brand ADD COLUMN l3m_units DECIMAL(15, 2) DEFAULT 0 COMMENT ''Last 3 months units (Aug-Sep-Oct 2025)''', 'SELECT ''Column l3m_units already exists'' as info');
PREPARE stmt FROM @sqlstmt;
EXECUTE stmt;

SET @col_exists = (SELECT COUNT(*) FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=@dbname AND TABLE_NAME=@tablename AND COLUMN_NAME='l3m_revenues');
SET @sqlstmt = IF(@col_exists = 0, 'ALTER TABLE brand ADD COLUMN l3m_revenues DECIMAL(15, 2) DEFAULT 0 COMMENT ''Last 3 months revenues (Aug-Sep-Oct 2025)''', 'SELECT ''Column l3m_revenues already exists'' as info');
PREPARE stmt FROM @sqlstmt;
EXECUTE stmt;

SET @col_exists = (SELECT COUNT(*) FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=@dbname AND TABLE_NAME=@tablename AND COLUMN_NAME='l3m_cm3');
SET @sqlstmt = IF(@col_exists = 0, 'ALTER TABLE brand ADD COLUMN l3m_cm3 DECIMAL(15, 2) DEFAULT 0 COMMENT ''Last 3 months CM3 (Aug-Sep-Oct 2025)''', 'SELECT ''Column l3m_cm3 already exists'' as info');
PREPARE stmt FROM @sqlstmt;
EXECUTE stmt;

-- Add LTM units and stock units columns to brand (only if they don't exist)
SET @col_exists = (SELECT COUNT(*) FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=@dbname AND TABLE_NAME=@tablename AND COLUMN_NAME='ltm_units');
SET @sqlstmt = IF(@col_exists = 0, 'ALTER TABLE brand ADD COLUMN ltm_units DECIMAL(15, 2) DEFAULT 0 COMMENT ''Last 12 months units (Nov 2024 - Oct 2025)''', 'SELECT ''Column ltm_units already exists'' as info');
PREPARE stmt FROM @sqlstmt;
EXECUTE stmt;

SET @col_exists = (SELECT COUNT(*) FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=@dbname AND TABLE_NAME=@tablename AND COLUMN_NAME='ltm_stock_units');
SET @sqlstmt = IF(@col_exists = 0, 'ALTER TABLE brand ADD COLUMN ltm_stock_units DECIMAL(15, 2) DEFAULT 0 COMMENT ''Last 12 months stock units (Nov 2024 - Oct 2025)''', 'SELECT ''Column ltm_stock_units already exists'' as info');
PREPARE stmt FROM @sqlstmt;
EXECUTE stmt;

SELECT '✓ BRAND columns added successfully!' as result;

-- ================================================================
-- 3. Add indexes for better query performance
-- ================================================================

SELECT 'Adding indexes...' as status;

-- Add indexes only if they don't exist
SET @index_exists = (SELECT COUNT(*) FROM information_schema.STATISTICS WHERE TABLE_SCHEMA=@dbname AND TABLE_NAME='asin' AND INDEX_NAME='idx_asin_ltm_units');
SET @sqlstmt = IF(@index_exists = 0, 'CREATE INDEX idx_asin_ltm_units ON asin(ltm_units DESC)', 'SELECT ''Index idx_asin_ltm_units already exists'' as info');
PREPARE stmt FROM @sqlstmt;
EXECUTE stmt;

SET @index_exists = (SELECT COUNT(*) FROM information_schema.STATISTICS WHERE TABLE_SCHEMA=@dbname AND TABLE_NAME='asin' AND INDEX_NAME='idx_asin_l3m_revenues');
SET @sqlstmt = IF(@index_exists = 0, 'CREATE INDEX idx_asin_l3m_revenues ON asin(l3m_revenues DESC)', 'SELECT ''Index idx_asin_l3m_revenues already exists'' as info');
PREPARE stmt FROM @sqlstmt;
EXECUTE stmt;

SET @index_exists = (SELECT COUNT(*) FROM information_schema.STATISTICS WHERE TABLE_SCHEMA=@dbname AND TABLE_NAME='brand' AND INDEX_NAME='idx_brand_ltm_units');
SET @sqlstmt = IF(@index_exists = 0, 'CREATE INDEX idx_brand_ltm_units ON brand(ltm_units DESC)', 'SELECT ''Index idx_brand_ltm_units already exists'' as info');
PREPARE stmt FROM @sqlstmt;
EXECUTE stmt;

SET @index_exists = (SELECT COUNT(*) FROM information_schema.STATISTICS WHERE TABLE_SCHEMA=@dbname AND TABLE_NAME='brand' AND INDEX_NAME='idx_brand_l3m_revenues');
SET @sqlstmt = IF(@index_exists = 0, 'CREATE INDEX idx_brand_l3m_revenues ON brand(l3m_revenues DESC)', 'SELECT ''Index idx_brand_l3m_revenues already exists'' as info');
PREPARE stmt FROM @sqlstmt;
EXECUTE stmt;

SELECT '✓ Indexes added successfully!' as result;

-- ================================================================
-- Show completion
-- ================================================================

SET @end_time = NOW();
SET @duration = TIMESTAMPDIFF(SECOND, @start_time, @end_time);

SELECT '========================================' as completion;
SELECT 'L3M and LTM Units Columns Added Successfully!' as status;
SELECT '========================================' as line;

SELECT 
    @duration as duration_seconds,
    @start_time as started_at,
    @end_time as completed_at;

SELECT '✓ All columns and indexes added successfully!' as final_status;
SELECT 'Run update_ltm_metrics.py to populate the new columns' as next_step;

