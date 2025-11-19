# Brand Scrapped Table

## Overview

The `brand_scrapped` table stores unique brand names that have been extracted from Amazon product scraping. This table helps normalize and track the relationship between scraped brand names and the official brand names in the `brand` table.

## Table Structure

```sql
CREATE TABLE `brand_scrapped` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `name` VARCHAR(255) NOT NULL,
  `brand_id` INT DEFAULT NULL,
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`),
  KEY `brand_id` (`brand_id`),
  CONSTRAINT `brand_scrapped_ibfk_1` FOREIGN KEY (`brand_id`) REFERENCES `brand` (`id`)
)
```

### Columns

- **id**: Auto-incrementing primary key
- **name**: Unique brand name as scraped from Amazon (from `asin.brand_scrapped`)
- **brand_id**: Foreign key reference to the `brand` table
- **created_at**: Timestamp of record creation

## Purpose

This table serves multiple purposes:

1. **Normalization**: Stores unique scraped brand names without duplication
2. **Mapping**: Links scraped brand names to official brand records via `brand_id`
3. **Data Quality**: Helps identify discrepancies between scraped and official brand names
4. **Analysis**: Enables queries to understand brand name variations

## Data Population

The table is populated with distinct `brand_scrapped` values from the `asin` table. When multiple ASINs have the same scrapped brand name but different `brand_id` values, the migration uses the most common `brand_id` as a smart default.

### Current Statistics

- **Total brands**: 254 unique scraped brand names
- **Exact matches**: 209 brands where scraped name matches official brand name
- **Different names**: 45 brands where scraped name differs from official name

### Examples of Name Variations

| Scrapped Name | Official Brand Name | Match |
|---------------|---------------------|-------|
| 2 Lb. Depot | 2 Lb. Depot | ✓ |
| 2WAYZ | 2wayz | ≠ (case) |
| A-Team Performance | A Team | ≠ (format) |
| Aquapaw | AquaPaw | ≠ (case) |
| Aqulius | Impresa | ≠ (different) |

## Migration

### To Create and Populate the Table

Run the migration script:

```bash
python apply_brand_scrapped_table_migration.py
```

This script will:
1. Create the `brand_scrapped` table
2. Populate it with unique brand names from `asin.brand_scrapped`
3. Link each scraped brand name to the most appropriate `brand_id`
4. Display statistics about the migration

### SQL Files

- **`create_brand_scrapped_table.sql`**: Raw SQL for table creation and population
- **`apply_brand_scrapped_table_migration.py`**: Python script for safe migration with checks

## Usage Examples

### Find all ASINs with a specific scraped brand

```sql
SELECT a.*
FROM asin a
INNER JOIN brand_scrapped bs ON a.brand_scrapped = bs.name
WHERE bs.name = 'Activ Life';
```

### Find brand name discrepancies

```sql
SELECT 
    bs.name AS scrapped_name,
    b.brand AS official_name,
    COUNT(*) AS asin_count
FROM brand_scrapped bs
LEFT JOIN brand b ON bs.brand_id = b.id
WHERE bs.name != b.brand
GROUP BY bs.name, b.brand
ORDER BY asin_count DESC;
```

### Count ASINs per scraped brand

```sql
SELECT 
    bs.name,
    bs.brand_id,
    b.brand AS official_brand,
    COUNT(a.id) AS asin_count
FROM brand_scrapped bs
LEFT JOIN brand b ON bs.brand_id = b.id
LEFT JOIN asin a ON a.brand_scrapped = bs.name
GROUP BY bs.name, bs.brand_id, b.brand
ORDER BY asin_count DESC;
```

## Related Tables

- **asin**: Contains `brand_scrapped` column with raw scraped brand names
- **brand**: Contains official brand information
- **financials**: Links to ASINs that have scraped brand data

## Notes

- The `name` column has a UNIQUE constraint to prevent duplicates
- The `brand_id` can be NULL if a scraped brand hasn't been matched to an official brand
- The migration intelligently selects the most common `brand_id` when multiple mappings exist
- Case sensitivity and formatting differences are preserved in the scraped names

