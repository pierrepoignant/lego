# Fill Sub-Categories Script

## Overview
This script automatically populates the `sub_category` field for brands that have it empty by analyzing their top-selling ASINs and extracting Amazon category information.

## What It Does

1. **Finds brands without sub-categories**: Queries all brands where `sub_category` is `NULL` or empty
2. **Identifies top ASINs**: For each brand, finds the top 20 ASINs by LTM (Last Twelve Months) revenues
3. **Extracts categories**: Pulls Amazon category information from:
   - The `amazon_category` field in the ASIN table
   - The `parse_json` field (scraped data) as a fallback
4. **Creates sub-category**: Concatenates up to 3 distinct categories with " / " separator
5. **Updates brand**: Saves the generated sub-category to the brand table

## Usage

### Run the Script

```bash
cd /Users/pierrepoignant/Coding/lego/database
python3 fill_subcats.py
```

### Expected Output

```
================================================================================
Fill Sub-Categories Script
================================================================================

✓ Connected to database

Found 150 brands without sub_category

Processing: Brand Name (ID: 123)
  📁 Analyzed top 20 ASINs (Top ASIN: B07DHH3JL2, Revenue: $45,230.50)
  📋 Sub-category: Home Décor / Door Mats / Outdoor Décor
  ✓ Updated!

Processing: Another Brand (ID: 124)
  📁 Analyzed top 20 ASINs (Top ASIN: B08XYZABC1, Revenue: $32,150.00)
  📋 Sub-category: Kitchen & Dining / Storage / Organization
  ✓ Updated!

...

================================================================================
✅ Complete!
   Updated: 145 brands
   Skipped: 5 brands (no data)
================================================================================
```

## How It Works

### Algorithm

1. **Query brands**:
```sql
SELECT id, brand 
FROM brand 
WHERE sub_category IS NULL OR sub_category = ''
```

2. **Get top 20 ASINs** (for each brand):
```sql
SELECT 
    a.id,
    a.asin,
    a.amazon_category,
    a.parse_json,
    a.ltm_revenues
FROM asin a
WHERE a.brand_id = ?
    AND a.ltm_revenues > 0
ORDER BY a.ltm_revenues DESC
LIMIT 20
```

3. **Extract categories**:
   - First try: `amazon_category` field (direct)
   - Second try: Parse from `parse_json` → `data.json[0].data.results[0].category_name`
   - Collect up to 3 **distinct** categories

4. **Update brand**:
```sql
UPDATE brand 
SET sub_category = ?
WHERE id = ?
```

## Example Results

| Brand | Top ASIN | Sub-Category Generated |
|-------|----------|------------------------|
| Juvale | B07DHH3JL2 | Outdoor Décor / Door Mats / Home Décor |
| Home Basics | B08XYZABC1 | Kitchen & Dining / Storage / Organization |
| Simple Modern | B08ABC1234 | Sports & Outdoors / Water Bottles / Drinkware |

## Display on Website

After running this script, sub-categories will appear on the main brand list page (http://127.0.0.1:5003/) below each brand name in italics:

```
📊 LEGO Brand Manager
┌─────────────────────────────────────────────┐
│  Brand Name                                 │
│  Outdoor Décor / Door Mats / Home Décor     │  ← Sub-category
└─────────────────────────────────────────────┘
```

## When to Run

- **After importing new brands**: When brands are added without sub-category information
- **After scraping ASINs**: Once you have revenue data and scraped category information
- **Periodically**: As a maintenance task to ensure all brands have sub-categories
- **After LTM updates**: When `ltm_revenues` are recalculated and top ASINs may change

## Troubleshooting

### No ASINs with revenue data
```
⚠️ No ASINs with revenue data found
```
**Solution**: Ensure ASINs for this brand have been scraped and have `ltm_revenues > 0`

### No category data found
```
⚠️ No category data found in top ASINs
```
**Solution**: 
- Check if ASINs have been scraped (need `parse_json` or `amazon_category`)
- Verify scraped data includes category information
- Manually set sub-category if needed

### Connection error
```
❌ Error: (2003, "Can't connect to MySQL server...")
```
**Solution**: 
- Verify database credentials in `config.ini`
- Check database is running and accessible
- Ensure VPN/network connection if using cloud database

## Related Files

- **Script**: `/Users/pierrepoignant/Coding/lego/database/fill_subcats.py`
- **Template**: `/Users/pierrepoignant/Coding/lego/templates/index.html` (displays sub-categories)
- **Flask Route**: `flask_app.py` → `index()` function (queries sub-categories)
- **Database**: `brand.sub_category` field (VARCHAR(255))

## Integration with LTM Metrics

This script works well with the LTM metrics system:
- Uses `ltm_revenues` to identify top ASINs
- Can be run after `update_ltm_metrics.py`
- Ensures sub-categories reflect current top-performing products

## Automation

To run automatically after LTM updates, add to your cron job:

```bash
# Daily at 3:30 AM (after LTM update at 3:00 AM)
30 3 * * * cd /Users/pierrepoignant/Coding/lego/database && python3 fill_subcats.py >> /tmp/lego_fill_subcats.log 2>&1
```

Or create a combined update script:

```bash
#!/bin/bash
# update_all_metrics.sh

echo "Updating LTM metrics..."
python3 update_ltm_metrics.py

echo "Filling sub-categories..."
python3 fill_subcats.py

echo "Refreshing summary tables..."
python3 refresh_summaries.py

echo "All updates complete!"
```

