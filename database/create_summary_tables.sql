-- ================================================================
-- Summary Tables for Dashboard Performance Optimization
-- ================================================================
-- This script creates pre-aggregated summary tables to speed up
-- dashboard queries by avoiding joins on the 68M row financials table
-- ================================================================

-- Drop existing summary tables if they exist
DROP TABLE IF EXISTS `financials_summary_monthly_brand`;
DROP TABLE IF EXISTS `financials_summary_monthly_category`;
DROP TABLE IF EXISTS `financials_summary_monthly_asin_marketplace`;

-- ================================================================
-- 1. Monthly summary by brand (for dashboard and profitability pages)
-- ================================================================
CREATE TABLE `financials_summary_monthly_brand` (
  `id` int NOT NULL AUTO_INCREMENT,
  `brand_id` int NOT NULL,
  `category_id` int DEFAULT NULL,
  `month` date NOT NULL,
  `marketplace` varchar(10) DEFAULT 'ALL',
  `metric` varchar(100) NOT NULL,
  `total_value` decimal(18,2) DEFAULT 0,
  `asin_count` int DEFAULT 0,
  `updated_at` timestamp DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uniq_brand_month_marketplace_metric` (`brand_id`, `month`, `marketplace`, `metric`),
  KEY `idx_brand_metric_month` (`brand_id`, `metric`, `month`),
  KEY `idx_category_metric_month` (`category_id`, `metric`, `month`),
  KEY `idx_month_metric` (`month`, `metric`),
  KEY `idx_marketplace` (`marketplace`),
  CONSTRAINT `fk_summary_brand` FOREIGN KEY (`brand_id`) REFERENCES `brand` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_summary_category` FOREIGN KEY (`category_id`) REFERENCES `category` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
COMMENT='Pre-aggregated monthly financial metrics by brand for fast dashboard queries';

-- ================================================================
-- 2. Monthly summary by category (for categories dashboard)
-- ================================================================
CREATE TABLE `financials_summary_monthly_category` (
  `id` int NOT NULL AUTO_INCREMENT,
  `category_id` int NOT NULL,
  `month` date NOT NULL,
  `metric` varchar(100) NOT NULL,
  `total_value` decimal(18,2) DEFAULT 0,
  `brand_count` int DEFAULT 0,
  `asin_count` int DEFAULT 0,
  `updated_at` timestamp DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uniq_category_month_metric` (`category_id`, `month`, `metric`),
  KEY `idx_category_metric_month` (`category_id`, `metric`, `month`),
  KEY `idx_month_metric` (`month`, `metric`),
  CONSTRAINT `fk_cat_summary_category` FOREIGN KEY (`category_id`) REFERENCES `category` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
COMMENT='Pre-aggregated monthly financial metrics by category for fast dashboard queries';

-- ================================================================
-- 3. Monthly summary by ASIN and marketplace (for detailed drill-downs)
-- ================================================================
CREATE TABLE `financials_summary_monthly_asin_marketplace` (
  `id` int NOT NULL AUTO_INCREMENT,
  `asin_id` int NOT NULL,
  `brand_id` int NOT NULL,
  `category_id` int DEFAULT NULL,
  `marketplace` varchar(10) NOT NULL,
  `month` date NOT NULL,
  `metric` varchar(100) NOT NULL,
  `value` decimal(15,2) DEFAULT 0,
  `updated_at` timestamp DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uniq_asin_marketplace_month_metric` (`asin_id`, `marketplace`, `month`, `metric`),
  KEY `idx_brand_marketplace_month_metric` (`brand_id`, `marketplace`, `month`, `metric`),
  KEY `idx_category_marketplace_month_metric` (`category_id`, `marketplace`, `month`, `metric`),
  KEY `idx_month_metric` (`month`, `metric`),
  CONSTRAINT `fk_asin_summary_asin` FOREIGN KEY (`asin_id`) REFERENCES `asin` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_asin_summary_brand` FOREIGN KEY (`brand_id`) REFERENCES `brand` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_asin_summary_category` FOREIGN KEY (`category_id`) REFERENCES `category` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
COMMENT='Pre-aggregated monthly financial metrics by ASIN and marketplace for detailed analysis';

-- ================================================================
-- Create indexes on the financials table if they don't exist
-- ================================================================
-- This helps with the initial aggregation queries
-- Note: We use procedure to handle "IF NOT EXISTS" for indexes
DROP PROCEDURE IF EXISTS add_index_if_not_exists;

DELIMITER $$
CREATE PROCEDURE add_index_if_not_exists()
BEGIN
    -- Check and add idx_month_metric_marketplace
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.statistics 
        WHERE table_schema = DATABASE() 
        AND table_name = 'financials' 
        AND index_name = 'idx_month_metric_marketplace'
    ) THEN
        ALTER TABLE `financials` ADD INDEX `idx_month_metric_marketplace` (`month`, `metric`, `marketplace`);
    END IF;
    
    -- Check and add idx_metric_month
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.statistics 
        WHERE table_schema = DATABASE() 
        AND table_name = 'financials' 
        AND index_name = 'idx_metric_month'
    ) THEN
        ALTER TABLE `financials` ADD INDEX `idx_metric_month` (`metric`, `month`);
    END IF;
END$$

DELIMITER ;

CALL add_index_if_not_exists();
DROP PROCEDURE add_index_if_not_exists;

-- Show completion message
SELECT 'Summary tables created successfully!' as status;
SELECT 
    'Run refresh_summary_tables.sql to populate the summary tables' as next_step,
    'This will take several minutes on the first run' as note;

