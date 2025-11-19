-- Add brand_scrapped_id column to the asin table to reference brand_scrapped table

ALTER TABLE asin 
ADD COLUMN brand_scrapped_id INT DEFAULT NULL COMMENT 'Foreign key to brand_scrapped table',
ADD KEY idx_brand_scrapped_id (brand_scrapped_id),
ADD CONSTRAINT asin_ibfk_brand_scrapped FOREIGN KEY (brand_scrapped_id) REFERENCES brand_scrapped(id);

-- Populate brand_scrapped_id from existing brand_scrapped names
UPDATE asin a
INNER JOIN brand_scrapped bs ON a.brand_scrapped = bs.name
SET a.brand_scrapped_id = bs.id
WHERE a.brand_scrapped IS NOT NULL;

