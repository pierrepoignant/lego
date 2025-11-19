# ASIN Scraping Script

## Overview

The `scrape_asins.py` script automatically scrapes all ASINs that haven't been scraped yet, processing them in order of decreasing revenue (October 2025 Net Revenue).

## Usage

### Basic Usage

```bash
cd /Users/pierrepoignant/Coding/lego
source venv/bin/activate
python scrape_asins.py
```

### What It Does

1. **Queries the database** for all ASINs where `scraped_at IS NULL`
2. **Orders ASINs** by October 2025 revenue (descending)
3. **Scrapes each ASIN** using the Pangolin API
4. **Saves all data** to the database:
   - Title, price, rating, rating count
   - Images, sales volume, seller info
   - Amazon category, parent ASIN
   - Full JSON response
5. **Rate limits** requests (2 second delay between each scrape)

## Features

- ✅ **Revenue-based prioritization** - Scrapes highest revenue ASINs first
- ✅ **Progress tracking** - Shows current progress (e.g., [5/100])
- ✅ **Error handling** - Continues on failures, reports at the end
- ✅ **Rate limiting** - 2 second delay between requests to avoid API throttling
- ✅ **Detailed output** - Shows each ASIN being processed with status
- ✅ **Interruptible** - Can be stopped with Ctrl+C safely

## Output Example

```
================================================================================
ASIN Scraper - Scraping by Revenue Order
================================================================================
✓ API key loaded

Fetching unscraped ASINs...
✓ Found 150 unscraped ASINs

Starting scraping process...
--------------------------------------------------------------------------------

[1/150] ASIN: B07K1ZTTLT | Revenue: $12,450.50
  Calling Pangolin API... ✓
  ✓ Saved: Juvale Corrugated Plastic Board Yard Signs - 24 x...
  Waiting 2 seconds before next request...

[2/150] ASIN: B08XYZ1234 | Revenue: $10,200.00
  Calling Pangolin API... ✓
  ✓ Saved: Product Title Here...
  Waiting 2 seconds before next request...

...

================================================================================
SCRAPING COMPLETE
================================================================================
Total ASINs processed: 150
✓ Successful: 145
✗ Failed: 5
================================================================================
```

## Configuration

The script uses:
- **Database connection**: From environment variables or defaults
  - `DB_HOST` (default: 127.0.0.1)
  - `DB_PORT` (default: 3306)
  - `DB_USER` (default: root)
  - `DB_PASSWORD` (default: empty)
  - `DB_NAME` (default: lego)
- **API key**: From `config.ini` under `[pangolin]` section

## Rate Limiting

The script includes a **2-second delay** between API requests to:
- Avoid overwhelming the Pangolin API
- Stay within rate limits
- Be respectful to the service

You can modify this in the script by changing the `time.sleep(2)` value.

## Error Handling

If a scrape fails:
- The error is logged to the console
- The script continues with the next ASIN
- A summary shows success/failure counts at the end

## Stopping the Script

Press **Ctrl+C** to safely interrupt the scraping process. Already scraped ASINs will remain in the database.

## Tips

1. **Run during off-hours** - For large batches, run overnight
2. **Monitor progress** - The script shows real-time progress
3. **Check failures** - If many ASINs fail, check your API key and rate limits
4. **Re-run safely** - Running multiple times is safe - it only scrapes ASINs where `scraped_at IS NULL`

## Database Query

The script uses this query to find unscraped ASINs:

```sql
SELECT 
    a.id,
    a.asin,
    a.brand_id,
    COALESCE(SUM(CASE 
        WHEN f.metric = 'Net revenue' 
        AND DATE_FORMAT(f.month, '%Y-%m-%d') = '2025-10-01'
        THEN f.value 
        ELSE 0 
    END), 0) as oct_2025_revenue
FROM asin a
LEFT JOIN financials f ON a.id = f.asin_id
WHERE a.scraped_at IS NULL
GROUP BY a.id, a.asin, a.brand_id
ORDER BY oct_2025_revenue DESC, a.asin
```

## Troubleshooting

### "No module named 'requests'"
Make sure you're in the virtual environment:
```bash
source venv/bin/activate
```

### "Pangolin API key not found"
Check that `config.ini` exists and contains:
```ini
[pangolin]
api_key = YOUR_API_KEY_HERE
```

### "Can't connect to MySQL server"
Ensure MySQL is running and the connection settings are correct.

### Many API failures
- Check your Pangolin API key is valid
- Verify you have enough API credits
- Consider increasing the rate limit delay

