-- ================================================================
-- Rename Stock Columns and Add Overstock Columns
-- ================================================================
-- This script:
-- 1. Renames ltm_stock_value → stock_value
-- 2. Renames ltm_stock_units → stock_units
-- 3. Adds stock_overstock_value column
-- 4. Adds stock_overstock_unit column
-- For both ASIN and BRAND tables
-- ================================================================

SET @start_time = NOW();
SELECT 'Renaming stock columns and adding overstock columns...' as status;

-- ================================================================
-- 1. ASIN Table Updates
-- ================================================================

SELECT '1/2: Updating ASIN table...' as status;

-- Rename ltm_stock_value to stock_value
ALTER TABLE asin 
CHANGE COLUMN ltm_stock_value stock_value DECIMAL(15, 2) DEFAULT 0 COMMENT 'Stock value';

SELECT '✓ Renamed ltm_stock_value to stock_value in asin table' as result;

-- Rename ltm_stock_units to stock_units
ALTER TABLE asin 
CHANGE COLUMN ltm_stock_units stock_units DECIMAL(15, 2) DEFAULT 0 COMMENT 'Stock units';

SELECT '✓ Renamed ltm_stock_units to stock_units in asin table' as result;

-- Add stock_overstock_value column
SET @dbname = DATABASE();
SET @tablename = 'asin';
SET @col_exists = (SELECT COUNT(*) FROM information_schema.COLUMNS 
                   WHERE TABLE_SCHEMA=@dbname AND TABLE_NAME=@tablename 
                   AND COLUMN_NAME='stock_overstock_value');
SET @sqlstmt = IF(@col_exists = 0, 
    'ALTER TABLE asin ADD COLUMN stock_overstock_value DECIMAL(15, 2) DEFAULT 0 COMMENT ''Overstock value (overstock units * COGS)''', 
    'SELECT ''Column stock_overstock_value already exists'' as info');
PREPARE stmt FROM @sqlstmt;
EXECUTE stmt;

SELECT '✓ Added stock_overstock_value column to asin table' as result;

-- Add stock_overstock_unit column
SET @col_exists = (SELECT COUNT(*) FROM information_schema.COLUMNS 
                   WHERE TABLE_SCHEMA=@dbname AND TABLE_NAME=@tablename 
                   AND COLUMN_NAME='stock_overstock_unit');
SET @sqlstmt = IF(@col_exists = 0, 
    'ALTER TABLE asin ADD COLUMN stock_overstock_unit DECIMAL(15, 2) DEFAULT 0 COMMENT ''Overstock units (stock units - 6 month forecast)''', 
    'SELECT ''Column stock_overstock_unit already exists'' as info');
PREPARE stmt FROM @sqlstmt;
EXECUTE stmt;

SELECT '✓ Added stock_overstock_unit column to asin table' as result;

-- ================================================================
-- 2. BRAND Table Updates
-- ================================================================

SELECT '2/2: Updating BRAND table...' as status;

-- Rename ltm_stock_value to stock_value
ALTER TABLE brand 
CHANGE COLUMN ltm_stock_value stock_value DECIMAL(15, 2) DEFAULT 0 COMMENT 'Stock value';

SELECT '✓ Renamed ltm_stock_value to stock_value in brand table' as result;

-- Rename ltm_stock_units to stock_units
ALTER TABLE brand 
CHANGE COLUMN ltm_stock_units stock_units DECIMAL(15, 2) DEFAULT 0 COMMENT 'Stock units';

SELECT '✓ Renamed ltm_stock_units to stock_units in brand table' as result;

-- Add stock_overstock_value column
SET @tablename = 'brand';
SET @col_exists = (SELECT COUNT(*) FROM information_schema.COLUMNS 
                   WHERE TABLE_SCHEMA=@dbname AND TABLE_NAME=@tablename 
                   AND COLUMN_NAME='stock_overstock_value');
SET @sqlstmt = IF(@col_exists = 0, 
    'ALTER TABLE brand ADD COLUMN stock_overstock_value DECIMAL(15, 2) DEFAULT 0 COMMENT ''Overstock value (overstock units * COGS)''', 
    'SELECT ''Column stock_overstock_value already exists'' as info');
PREPARE stmt FROM @sqlstmt;
EXECUTE stmt;

SELECT '✓ Added stock_overstock_value column to brand table' as result;

-- Add stock_overstock_unit column
SET @col_exists = (SELECT COUNT(*) FROM information_schema.COLUMNS 
                   WHERE TABLE_SCHEMA=@dbname AND TABLE_NAME=@tablename 
                   AND COLUMN_NAME='stock_overstock_unit');
SET @sqlstmt = IF(@col_exists = 0, 
    'ALTER TABLE brand ADD COLUMN stock_overstock_unit DECIMAL(15, 2) DEFAULT 0 COMMENT ''Overstock units (stock units - 6 month forecast)''', 
    'SELECT ''Column stock_overstock_unit already exists'' as info');
PREPARE stmt FROM @sqlstmt;
EXECUTE stmt;

SELECT '✓ Added stock_overstock_unit column to brand table' as result;

-- ================================================================
-- Completion Summary
-- ================================================================

SET @end_time = NOW();
SET @duration = TIMESTAMPDIFF(SECOND, @start_time, @end_time);

SELECT '========================================' as completion;
SELECT 'Stock Columns Updated Successfully!' as status;
SELECT '========================================' as line;

SELECT 
    @duration as duration_seconds,
    @start_time as started_at,
    @end_time as completed_at;

SELECT '✓ All columns renamed and added successfully!' as final_status;
SELECT 'Run compute_overstock.py to populate the overstock columns' as next_step;

