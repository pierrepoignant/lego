-- ================================================================
-- Marketplace Reference Table
-- ================================================================
-- Creates a lookup table for marketplaces with proper country names
-- ================================================================

DROP TABLE IF EXISTS `marketplace`;

CREATE TABLE `marketplace` (
  `id` int NOT NULL AUTO_INCREMENT,
  `code` varchar(10) NOT NULL,
  `country_name` varchar(100) NOT NULL,
  `region` varchar(50) DEFAULT NULL,
  `currency` varchar(10) DEFAULT NULL,
  `active` tinyint(1) DEFAULT 1,
  `created_at` timestamp DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `code` (`code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
COMMENT='Reference table for Amazon marketplaces';

-- Populate with common Amazon marketplaces
INSERT INTO `marketplace` (code, country_name, region, currency) VALUES
-- North America
('US', 'United States', 'North America', 'USD'),
('CA', 'Canada', 'North America', 'CAD'),
('MX', 'Mexico', 'North America', 'MXN'),

-- Europe
('UK', 'United Kingdom', 'Europe', 'GBP'),
('DE', 'Germany', 'Europe', 'EUR'),
('FR', 'France', 'Europe', 'EUR'),
('IT', 'Italy', 'Europe', 'EUR'),
('ES', 'Spain', 'Europe', 'EUR'),
('NL', 'Netherlands', 'Europe', 'EUR'),
('SE', 'Sweden', 'Europe', 'SEK'),
('PL', 'Poland', 'Europe', 'PLN'),
('BE', 'Belgium', 'Europe', 'EUR'),

-- Asia Pacific
('JP', 'Japan', 'Asia Pacific', 'JPY'),
('AU', 'Australia', 'Asia Pacific', 'AUD'),
('SG', 'Singapore', 'Asia Pacific', 'SGD'),
('IN', 'India', 'Asia Pacific', 'INR'),

-- Middle East
('AE', 'United Arab Emirates', 'Middle East', 'AED'),
('SA', 'Saudi Arabia', 'Middle East', 'SAR'),
('TR', 'Turkey', 'Middle East', 'TRY'),

-- South America
('BR', 'Brazil', 'South America', 'BRL');

-- Show what was created
SELECT 'Marketplace reference table created!' as status;
SELECT COUNT(*) as marketplace_count FROM marketplace;
SELECT * FROM marketplace ORDER BY region, country_name;

