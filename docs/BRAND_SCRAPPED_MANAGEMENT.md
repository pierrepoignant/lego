# Brand Scrapped Management Feature

## Overview

The Brand Scrapped Management feature provides a web interface to manage and map scraped brand names from Amazon to official brand records in your database.

## Access

**URL**: `http://localhost:5003/brand-scrapped`

The page is accessible from the main navigation menu under **🏢 Brands → 🏷️ Brand Scrapped**

## Features

### 1. **Statistics Dashboard**
- **Total Scrapped Brands**: Total number of unique brand names extracted from Amazon
- **Mapped to Brands**: Brands that have been linked to official brand records
- **Not Mapped**: Brands that need attention (unmapped)

### 2. **Search & Filtering**
- **Search by name**: Find specific brand names quickly
- **Filter by mapping status**:
  - **All**: Show all brand_scrapped entries
  - **Mapped**: Show only brands that are already linked to the brand table
  - **Unmapped**: Show only brands that need to be mapped

### 3. **Brand Mapping Actions**

#### Edit/Update Mapping
Each row has a dropdown that allows you to:
- Select an existing brand from the brand table
- Click "Update Mapping" to link the scraped brand to the selected official brand
- The mapping updates the `brand_id` field in the `brand_scrapped` table

#### Create New Brand
For unmapped brands, you can:
- Click "Create New Brand" button
- This creates a new entry in the `brand` table using the scraped brand name
- Automatically links the brand_scrapped entry to the newly created brand

### 4. **Data Display**

Each row shows:
- **ID**: The brand_scrapped record ID
- **Scrapped Brand Name**: The brand name as extracted from Amazon
- **Mapped Brand**: The official brand name (if mapped)
- **Status**: Badge showing "Mapped" (green) or "Unmapped" (red)
- **ASINs**: Count of ASINs associated with this scraped brand name
- **Actions**: Edit form with dropdown and buttons

## Use Cases

### Scenario 1: Link Existing Brand
When a scraped brand name matches or relates to an existing brand:
1. Use the dropdown to select the correct brand from the list
2. Click "Update Mapping"
3. The scrapped brand is now linked to the official brand

### Scenario 2: Create New Brand
When a scraped brand represents a new brand not in your system:
1. Click "Create New Brand"
2. Confirm the creation
3. A new brand is created and automatically linked

### Scenario 3: Handle Variations
When scraped names have variations (e.g., "AquaPaw" vs "Aquapaw"):
1. Search for the brand using the search box
2. Map both variations to the same official brand if needed
3. This normalizes brand references across your database

## Technical Details

### Routes
- `GET /brand-scrapped`: Display the management page
- `POST /brand-scrapped/update/<scrapped_id>`: Update brand mapping
- `POST /brand-scrapped/create-brand/<scrapped_id>`: Create new brand from scrapped entry

### Database Changes
- Updates `brand_scrapped.brand_id` when mapping brands
- Creates new records in `brand` table when using "Create New Brand"
- Maintains referential integrity with foreign key constraints

### SQL Schema
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

## Benefits

1. **Data Quality**: Normalize brand names across your database
2. **Visibility**: See which scraped brands need attention
3. **Efficiency**: Quickly map brands without SQL queries
4. **Audit Trail**: Track which scraped brands map to which official brands
5. **ASIN Insights**: See how many ASINs use each scraped brand name

## Screenshots & UI Elements

The interface follows the existing LEGO Apps design system:
- **Purple gradient cards** for statistics
- **Modern table** with hover effects
- **Color-coded badges** for status
- **Inline forms** for quick updates
- **Responsive design** that works on all screen sizes

## Tips

- Use the **search** feature to find similar brand names
- Focus on **unmapped** brands first (use the filter)
- Check the **ASIN count** to prioritize high-impact brands
- The dropdown is **searchable** - start typing to find brands quickly
- Brand names are **case-sensitive** - ensure consistency when creating new brands

## Related Documentation

- [Brand Scrapped Table README](../database/BRAND_SCRAPPED_TABLE_README.md)
- [Database README](../database/DATABASE_README.md)
- [Flask App Documentation](../README.md)

