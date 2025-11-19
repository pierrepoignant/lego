-- Add brand_scrapped and brand_imported columns to the asin table

ALTER TABLE asin 
ADD COLUMN brand_scrapped VARCHAR(255) DEFAULT NULL COMMENT 'Brand name extracted from Amazon scraping',
ADD COLUMN brand_imported INT DEFAULT 0 COMMENT 'Flag indicating if brand has been imported (0=no, 1=yes)';

-- Add index for better query performance when filtering by brand_scrapped
CREATE INDEX idx_brand_scrapped ON asin(brand_scrapped);





