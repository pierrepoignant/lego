# Forecast System

## Overview

The forecast system projects sales metrics (units and revenues) for the next 12 months (November 2025 - October 2026) based on historical data and seasonality patterns.

## Components

### 1. Database Tables

Two tables store forecast data:

#### `forecast_asin` Table
Stores forecasted metrics at the ASIN level.

```sql
CREATE TABLE forecast_asin (
    id INT PRIMARY KEY AUTO_INCREMENT,
    asin_id INT NOT NULL,
    metric VARCHAR(50) NOT NULL,  -- 'Net units' or 'Net revenue'
    month DATE NOT NULL,
    value DECIMAL(15, 2) DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY (asin_id, metric, month)
);
```

#### `forecast_brand` Table
Stores aggregated forecasts at the brand level.

```sql
CREATE TABLE forecast_brand (
    id INT PRIMARY KEY AUTO_INCREMENT,
    brand_id INT NOT NULL,
    metric VARCHAR(50) NOT NULL,  -- 'Net units' or 'Net revenue'
    month DATE NOT NULL,
    value DECIMAL(15, 2) DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY (brand_id, metric, month)
);
```

### 2. Forecast Computation Script

**File:** `compute_forecast.py`

This script calculates forecasts using the following methodology:

#### For Each ASIN:

1. **EOL Products**: Set forecast to 0 for all months
   
2. **Active Products with Seasonality**:
   
   **Step 1: Calculate Base Period Sum**
   ```
   base_period_sum = seasonality.unit_08 + seasonality.unit_09 + seasonality.unit_10
   ```
   
   **Step 2: Calculate Total Next 12 Months Units**
   ```
   total_next_12_months = asin.l3m_units / base_period_sum
   ```
   
   *Note: Uses L3M (last 3 months) to capture most recent performance trend*
   
   **Step 3: Calculate Monthly Unit Forecasts**
   ```
   For each month (Nov 2025 - Oct 2026):
       forecasted_units[month] = seasonality.unit_XX * total_next_12_months
   ```
   
   **Step 4: Calculate ASP (Average Selling Price)**
   ```
   asp = asin.l3m_revenues / asin.l3m_units
   (fallback to ltm_revenues/ltm_units if l3m not available)
   ```
   
   **Step 5: Calculate Revenue Forecasts**
   ```
   For each month:
       forecasted_revenue[month] = forecasted_units[month] * asp
   ```

3. **Brand Aggregation**: Sum all ASIN forecasts by brand

#### Running the Script

```bash
# Create the forecast tables (first time only)
mysql -u [username] -p [database] < database/create_forecast_tables.sql

# Compute forecasts
python3 compute_forecast.py
```

The script will:
- Process all ASINs in the database
- Calculate unit and revenue forecasts for 12 months
- Store results in `forecast_asin` table
- Aggregate to brand level in `forecast_brand` table

### 3. Forecast Dashboard

Access the forecast dashboard at: **http://127.0.0.1:5003/forecast-dashboard**

Or navigate via menu: **Stats → 🔮 Dashboard Forecast**

#### Features:
- **Interactive Chart**: Visual representation of forecast data
- **Data Table**: Detailed monthly breakdown with totals
- **Filters**: 
  - Metric: Net Revenue or Net Units
  - Brand: Filter by specific brand or view all brands
- **Time Period**: November 2025 - October 2026 (12 months)

## Setup Instructions

### 1. Create Database Tables

```bash
mysql -u root -p lego < database/create_forecast_tables.sql
```

### 2. Ensure Prerequisites Are Met

Make sure these metrics are up to date:
- ASIN LTM metrics (ltm_revenues, ltm_units)
- ASIN L3M metrics (l3m_revenues, l3m_units)
- Seasonality factors in the `seasonality` table

Update if needed:
```bash
# Update LTM metrics
python3 compute_ltm_metrics.py

# Update seasonality factors
python3 compute_seasonality_factors.py
```

### 3. Compute Forecasts

```bash
python3 compute_forecast.py
```

This will populate both `forecast_asin` and `forecast_brand` tables.

### 4. View Dashboard

Navigate to: http://127.0.0.1:5003/forecast-dashboard

## Forecast Methodology Details

### Why Aug-Sep-Oct as Base Period?

The base period (Aug-Sep-Oct) represents the most recent complete 3-month period in the LTM window (Nov 2024 - Oct 2025). This period is used to:
1. Calculate the proportion of annual sales
2. Project forward using seasonality patterns

### Seasonality Factors

Seasonality factors are stored in the `seasonality` table:
- `unit_01` through `unit_12` represent the proportion of annual sales for each month
- Sum of all factors = 1.00 (100%)
- Based on 2024 historical data

Example:
```
If unit_08 = 0.08 (8%)
   unit_09 = 0.09 (9%)
   unit_10 = 0.10 (10%)
   
Then base_period_sum = 0.27 (27% of annual sales)
```

### ASP Calculation

The Average Selling Price (ASP) is calculated using the most recent available data:
1. **Primary**: L3M data (Aug-Sep-Oct 2025) for most current pricing
2. **Fallback**: LTM data if L3M is not available

## Maintenance

### Updating Forecasts

Re-run the forecast computation script monthly or when underlying data changes:

```bash
python3 compute_forecast.py
```

The script automatically:
- Clears old forecast data
- Recalculates based on latest metrics
- Updates both ASIN and brand level forecasts

### Monitoring

Check forecast data quality:

```sql
-- Check forecast totals by metric
SELECT 
    metric,
    SUM(value) as total_forecast
FROM forecast_brand
GROUP BY metric;

-- Check forecasts for a specific brand
SELECT 
    b.brand,
    fb.metric,
    DATE_FORMAT(fb.month, '%Y-%m') as month,
    fb.value
FROM forecast_brand fb
JOIN brand b ON fb.brand_id = b.id
WHERE b.id = [brand_id]
ORDER BY fb.metric, fb.month;
```

## API Endpoints

### Get Forecast Data

**Endpoint:** `/api/forecast-data`

**Parameters:**
- `metric` (required): "Net revenue" or "Net units"
- `brand_id` (optional): Filter by specific brand

**Example:**
```javascript
fetch('/api/forecast-data?metric=Net revenue&brand_id=123')
    .then(response => response.json())
    .then(data => {
        console.log(data.months);  // Array of month labels
        console.log(data.data);    // Array of forecast values
    });
```

## Troubleshooting

### No Forecast Data Showing

1. **Check if forecast tables exist:**
   ```sql
   SHOW TABLES LIKE 'forecast_%';
   ```

2. **Check if forecast data is populated:**
   ```sql
   SELECT COUNT(*) FROM forecast_asin;
   SELECT COUNT(*) FROM forecast_brand;
   ```

3. **Run the computation script:**
   ```bash
   python3 compute_forecast.py
   ```

### Forecast Values Are Zero

1. **Check if ASINs have seasonality assigned:**
   ```sql
   SELECT 
       COUNT(*) as total_asins,
       SUM(CASE WHEN seasonality IS NOT NULL THEN 1 ELSE 0 END) as with_seasonality
   FROM asin;
   ```

2. **Check if seasonality factors are computed:**
   ```sql
   SELECT * FROM seasonality LIMIT 5;
   ```

3. **Check if LTM metrics are populated:**
   ```sql
   SELECT 
       COUNT(*) as total_asins,
       SUM(CASE WHEN ltm_revenues > 0 THEN 1 ELSE 0 END) as with_ltm_revenue,
       SUM(CASE WHEN ltm_units > 0 THEN 1 ELSE 0 END) as with_ltm_units
   FROM asin;
   ```

## Integration with Existing System

The forecast system integrates seamlessly with:
- **LTM Metrics System**: Uses `ltm_revenues` and `ltm_units`
- **L3M Metrics**: Uses `l3m_revenues` and `l3m_units` for ASP
- **Seasonality System**: Uses seasonality factors for monthly distribution
- **Brand System**: Aggregates forecasts to brand level
- **Dashboard System**: Similar UI/UX to existing dashboard

## Future Enhancements

Potential improvements:
1. Add confidence intervals to forecasts
2. Include trend analysis (YoY growth adjustment)
3. Add scenario modeling (optimistic/pessimistic)
4. Export forecast data to CSV
5. Compare forecast vs actual (once actual data is available)
6. Add forecasting for other metrics (CM3, EBITDA)

