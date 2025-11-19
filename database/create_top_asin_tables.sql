-- Create top_asin_buckets table
DROP TABLE IF EXISTS `top_asins`;
DROP TABLE IF EXISTS `top_asin_buckets`;

CREATE TABLE `top_asin_buckets` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(255) NOT NULL,
  `description` varchar(512) DEFAULT NULL,
  `color` varchar(7) DEFAULT '#667eea',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Create top_asins table
CREATE TABLE `top_asins` (
  `id` int NOT NULL AUTO_INCREMENT,
  `asin_id` int NOT NULL,
  `bucket_id` int NOT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_asin_bucket` (`asin_id`, `bucket_id`),
  KEY `asin_id` (`asin_id`),
  KEY `bucket_id` (`bucket_id`),
  CONSTRAINT `top_asins_ibfk_asin` FOREIGN KEY (`asin_id`) REFERENCES `asin` (`id`) ON DELETE CASCADE,
  CONSTRAINT `top_asins_ibfk_bucket` FOREIGN KEY (`bucket_id`) REFERENCES `top_asin_buckets` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;





