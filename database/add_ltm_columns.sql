-- Add LTM (Last Twelve Months) columns to the asin table
-- LTM = Nov 2024 - Oct 2025

ALTER TABLE asin 
ADD COLUMN ltm_revenues DECIMAL(15, 2) DEFAULT 0 COMMENT 'Last 12 months revenues (Nov 2024 - Oct 2025)',
ADD COLUMN ltm_brand_ebitda DECIMAL(10, 2) DEFAULT 0 COMMENT 'Last 12 months brand EBITDA %',
ADD COLUMN ltm_stock_value DECIMAL(15, 2) DEFAULT 0 COMMENT 'Last 12 months stock value',
ADD COLUMN ltm_updated_at TIMESTAMP NULL COMMENT 'When LTM metrics were last calculated';

-- Add index for better query performance
CREATE INDEX idx_ltm_revenues ON asin(ltm_revenues DESC);

