-- ================================================================
-- Create Forecast Tables for ASIN and Brand
-- ================================================================
-- Purpose: Store forecasted metrics (units and revenues) for next 12 months
-- Period: November 2025 - October 2026
-- ================================================================

SET @start_time = NOW();
SELECT 'Creating forecast tables...' as status;

-- ================================================================
-- 1. Create forecast_asin table
-- ================================================================
SELECT '1/2: Creating forecast_asin table...' as status;

CREATE TABLE IF NOT EXISTS `forecast_asin` (
    `id` INT NOT NULL AUTO_INCREMENT,
    `asin_id` INT NOT NULL,
    `metric` VARCHAR(50) NOT NULL,
    `month` DATE NOT NULL,
    `value` DECIMAL(15, 2) DEFAULT 0,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `unique_asin_metric_month` (`asin_id`, `metric`, `month`),
    KEY `idx_asin_id` (`asin_id`),
    KEY `idx_metric` (`metric`),
    KEY `idx_month` (`month`),
    CONSTRAINT `fk_forecast_asin_asin` FOREIGN KEY (`asin_id`) REFERENCES `asin` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

SELECT '✓ forecast_asin table created' as result;

-- ================================================================
-- 2. Create forecast_brand table
-- ================================================================
SELECT '2/2: Creating forecast_brand table...' as status;

CREATE TABLE IF NOT EXISTS `forecast_brand` (
    `id` INT NOT NULL AUTO_INCREMENT,
    `brand_id` INT NOT NULL,
    `metric` VARCHAR(50) NOT NULL,
    `month` DATE NOT NULL,
    `value` DECIMAL(15, 2) DEFAULT 0,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `unique_brand_metric_month` (`brand_id`, `metric`, `month`),
    KEY `idx_brand_id` (`brand_id`),
    KEY `idx_metric` (`metric`),
    KEY `idx_month` (`month`),
    CONSTRAINT `fk_forecast_brand_brand` FOREIGN KEY (`brand_id`) REFERENCES `brand` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

SELECT '✓ forecast_brand table created' as result;

-- ================================================================
-- Summary
-- ================================================================
SELECT CONCAT('Forecast tables created in ', TIMESTAMPDIFF(SECOND, @start_time, NOW()), ' seconds') as summary;

