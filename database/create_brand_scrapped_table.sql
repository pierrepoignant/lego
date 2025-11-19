-- Create brand_scrapped table to store scraped brand names

DROP TABLE IF EXISTS `brand_scrapped`;

CREATE TABLE `brand_scrapped` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `name` VARCHAR(255) NOT NULL,
  `brand_id` INT DEFAULT NULL,
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`),
  KEY `brand_id` (`brand_id`),
  CONSTRAINT `brand_scrapped_ibfk_1` FOREIGN KEY (`brand_id`) REFERENCES `brand` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Insert distinct brand_scrapped values from asin table
-- For each unique brand_scrapped name, we'll use the most common brand_id associated with it
-- If there are ties, MIN(brand_id) will be used as a tiebreaker
INSERT INTO brand_scrapped (name, brand_id)
SELECT 
    brand_scrapped,
    SUBSTRING_INDEX(
        GROUP_CONCAT(brand_id ORDER BY brand_count DESC, brand_id ASC),
        ',',
        1
    ) AS brand_id
FROM (
    SELECT 
        brand_scrapped,
        brand_id,
        COUNT(*) as brand_count
    FROM asin
    WHERE brand_scrapped IS NOT NULL 
        AND brand_scrapped != ''
        AND brand_scrapped != 'null'
    GROUP BY brand_scrapped, brand_id
) AS brand_counts
GROUP BY brand_scrapped
ORDER BY brand_scrapped;

