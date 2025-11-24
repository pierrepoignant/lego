-- Add main_image column to brand table
ALTER TABLE `brand` 
ADD COLUMN `main_image` VARCHAR(512) DEFAULT NULL AFTER `url`;

-- Add main_image column to top_asin_buckets table
ALTER TABLE `top_asin_buckets` 
ADD COLUMN `main_image` VARCHAR(512) DEFAULT NULL AFTER `color`;

