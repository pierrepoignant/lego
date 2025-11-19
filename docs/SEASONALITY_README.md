# Seasonality Factors Feature

## Overview

The seasonality feature allows you to compute and visualize seasonality patterns for different product categories based on historical 2024 unit sales data. This helps identify which months have higher or lower sales for each seasonality type.

## Components

### 1. Database Structure

The `seasonality` table stores monthly factors for each seasonality type:

```sql
CREATE TABLE seasonality (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(255) NOT NULL,
    unit_01 DECIMAL(4,2),  -- January factor
    unit_02 DECIMAL(4,2),  -- February factor
    ...
    unit_12 DECIMAL(4,2)   -- December factor
);
```

- Each `unit_XX` column represents the proportion of annual units sold in that month
- Values are stored as decimals (e.g., 0.08 = 8% of annual units)
- The sum of all 12 monthly factors should equal 1.00 (100%)

### 2. Computation Script

**File:** `compute_seasonality_factors.py`

This script calculates seasonality factors based on 2024 data:

```bash
./compute_seasonality_factors.py
```

**How it works:**
1. Retrieves all seasonalities from the database
2. For each seasonality:
   - Finds all ASINs with that seasonality (excluding EOL items)
   - Sums the 'Net units' metric for each month of 2024
   - Calculates the total units for the year
   - Computes monthly factors (month_units / total_units)
   - Updates the seasonality table with the factors

**Note:** EOL (End of Life) items are automatically excluded from the calculation to ensure seasonality factors reflect only active products.

**Output Example:**
```
Processing: Summer Products (ID: 1)
  Total units in 2024: 125,430
  Factor sum: 1.0000
  Monthly factors:
    Jan: 0.0521 (6,534 units)
    Feb: 0.0487 (6,108 units)
    Mar: 0.0623 (7,814 units)
    Apr: 0.0892 (11,188 units)
    May: 0.1245 (15,616 units)
    Jun: 0.1534 (19,241 units)
    Jul: 0.1689 (21,192 units)
    Aug: 0.1423 (17,849 units)
    Sep: 0.0934 (11,715 units)
    Oct: 0.0412 (5,167 units)
    Nov: 0.0134 (1,681 units)
    Dec: 0.0106 (1,329 units)
  ✓ Updated seasonality factors for Summer Products
```

**Requirements:**
- Database connection configured in `config.ini`
- Historical 2024 data in the `financials` table with 'Net units' metric
- ASINs linked to seasonalities via the `asin.seasonality` field

### 3. Web Interface

**Route:** `/seasonality`
**Access:** Brands > Seasonality (from navigation menu)

The web interface provides:

#### Seasonality List View
- Cards showing all seasonalities
- Each card displays:
  - Seasonality name
  - Number of ASINs
  - Total LTM revenue
- Click any card to view the seasonality chart

#### Seasonality Chart Modal
- **Bar Chart**: Visual representation of monthly factors
  - X-axis: Months (Jan-Dec)
  - Y-axis: Percentage of annual units
  - Shows distribution of units across the year
  
- **Data Table**: Detailed monthly breakdown
  - Factor (decimal): 0.0000-1.0000
  - Percentage: 0.00%-100.00%

**Technology:**
- Chart.js for interactive visualizations
- Responsive design that works on all devices
- Modal-based interface for better UX

## Usage Workflow

### Initial Setup

1. **Ensure seasonality data exists:**
   ```sql
   -- Check seasonalities
   SELECT * FROM seasonality;
   
   -- Verify ASINs have seasonality assigned
   SELECT COUNT(*), seasonality 
   FROM asin 
   WHERE seasonality IS NOT NULL 
   GROUP BY seasonality;
   ```

2. **Run the computation script:**
   ```bash
   cd /path/to/lego
   ./compute_seasonality_factors.py
   ```

3. **Access the web interface:**
   - Navigate to: http://your-domain/seasonality
   - Or click: Brands > Seasonality in the menu

### Updating Seasonality Factors

Run the computation script periodically (e.g., annually) to update factors based on the latest full year of data:

```bash
# Update for 2024 data (current implementation)
./compute_seasonality_factors.py

# For future years, modify the script's year filter
```

**Note:** The script currently uses 2024 data. To use a different year, modify line 67 in `compute_seasonality_factors.py`:
```python
AND YEAR(f.month) = 2024  # Change to desired year
```

## API Endpoints

### GET `/api/seasonality-data/<seasonality_id>`

Returns seasonality factor data for a specific seasonality.

**Response:**
```json
{
    "id": 1,
    "name": "Summer Products",
    "months": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
    "factors": [0.0521, 0.0487, 0.0623, 0.0892, 0.1245, 0.1534, 0.1689, 0.1423, 0.0934, 0.0412, 0.0134, 0.0106],
    "percentages": [5.21, 4.87, 6.23, 8.92, 12.45, 15.34, 16.89, 14.23, 9.34, 4.12, 1.34, 1.06]
}
```

## Files Created/Modified

### New Files
- `compute_seasonality_factors.py` - Computation script
- `templates/seasonality.html` - Web interface template
- `docs/SEASONALITY_README.md` - This documentation

### Modified Files
- `flask_app.py` - Added routes:
  - `/seasonality` - List view
  - `/api/seasonality-data/<seasonality_id>` - API endpoint
- `templates/base.html` - Added navigation link

## Troubleshooting

### No seasonalities showing up
- Check if seasonalities exist: `SELECT * FROM seasonality;`
- Verify ASINs have seasonality assigned: `SELECT COUNT(*) FROM asin WHERE seasonality IS NOT NULL;`

### Factors sum to 0 or incorrect values
- Ensure 2024 data exists in financials table
- Verify 'Net units' metric is present
- Check ASIN-seasonality relationships

### Chart not displaying
- Check browser console for JavaScript errors
- Verify API endpoint is accessible: `/api/seasonality-data/1`
- Ensure Chart.js CDN is loading correctly

## Future Enhancements

Potential improvements:
1. **Year Selection**: Allow users to compute factors for any year
2. **Comparison View**: Compare seasonality patterns across multiple years
3. **Forecasting**: Use factors to project future demand
4. **Seasonality Assignment**: Bulk assign seasonalities to ASINs
5. **Export**: Download seasonality data as CSV
6. **Multiple Marketplaces**: Compute separate factors per marketplace

## Data Validation

The script validates:
- ✓ Factor sum equals 1.00 (±0.0001 tolerance)
- ✓ All factors are between 0 and 1
- ✓ At least one month has data

Example validation output:
```
Processing: Winter Sports (ID: 3)
  Total units in 2024: 89,234
  Factor sum: 1.0001  ← Should be close to 1.0
```

If factor sum is significantly off (>1.01 or <0.99), investigate data integrity.

## Support

For issues or questions:
1. Check logs in the Flask application
2. Verify database connectivity
3. Review this documentation
4. Check the `compute_seasonality_factors.py` script output for errors

