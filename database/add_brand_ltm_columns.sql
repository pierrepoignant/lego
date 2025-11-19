-- Add LTM (Last Twelve Months) columns to the brand table
-- LTM = Nov 2024 - Oct 2025

ALTER TABLE brand 
ADD COLUMN ltm_revenues DECIMAL(15, 2) DEFAULT 0 COMMENT 'Last 12 months revenues (Nov 2024 - Oct 2025)',
ADD COLUMN ltm_brand_ebitda DECIMAL(10, 2) DEFAULT 0 COMMENT 'Last 12 months brand EBITDA %',
ADD COLUMN ltm_stock_value DECIMAL(15, 2) DEFAULT 0 COMMENT 'Last 12 months stock value',
ADD COLUMN ltm_updated_at TIMESTAMP NULL COMMENT 'When LTM metrics were last calculated';

-- Add index for better query performance
CREATE INDEX idx_brand_ltm_revenues ON brand(ltm_revenues DESC);

SELECT 'Brand LTM columns added successfully!' as message;

