-- Add ltm_cm3 column to asin and brand tables

-- Add to asin table
ALTER TABLE asin 
ADD COLUMN ltm_cm3 DECIMAL(15,2) DEFAULT NULL COMMENT 'Last Twelve Months CM3 (sum of CM3 for Nov 2024 - Oct 2025)';

-- Add index for performance
CREATE INDEX idx_asin_ltm_cm3 ON asin(ltm_cm3);

-- Add to brand table
ALTER TABLE brand 
ADD COLUMN ltm_cm3 DECIMAL(15,2) DEFAULT NULL COMMENT 'Last Twelve Months CM3 (sum of CM3 for Nov 2024 - Oct 2025)';

-- Add index for performance
CREATE INDEX idx_brand_ltm_cm3 ON brand(ltm_cm3);

