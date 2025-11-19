#!/usr/bin/env python3
"""
Compute Forecast for ASINs and Brands

This script computes forecasts for the next 12 months (November 2025 - October 2026)
based on LTM revenues and seasonality factors.

Methodology:
1. For each ASIN:
   - If EOL (End of Life), set forecast to 0 for all months
   - Otherwise:
     a. Calculate total_next_12_months = ltm_revenue / (unit_08 + unit_09 + unit_10)
     b. For each month, calculate units = unit_XX * total_next_12_months
     c. Calculate ASP = l3m_revenues / l3m_units
     d. Calculate revenues = units * ASP
2. Aggregate ASIN forecasts to brand level
"""

import pymysql
from decimal import Decimal
import sys
from datetime import date
from db_utils import get_db_params

def get_connection():
    """Create database connection"""
    params = get_db_params()
    return pymysql.connect(
        host=params['host'],
        port=params['port'],
        user=params['user'],
        password=params['password'],
        database=params['database'],
        charset='utf8mb4'
    )

def compute_asin_forecasts(conn):
    """Compute forecasts for all ASINs"""
    print("Computing ASIN Forecasts...")
    print("=" * 80)
    
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    
    try:
        # Clear existing forecast data
        print("Clearing existing forecast data...")
        cursor.execute("DELETE FROM forecast_asin")
        conn.commit()
        print(f"✓ Cleared existing ASIN forecasts\n")
        
        # Get all ASINs with their metrics and seasonality
        query = """
            SELECT 
                a.id as asin_id,
                a.asin,
                a.brand_id,
                a.seasonality,
                a.eol,
                a.ltm_revenues,
                a.ltm_units,
                a.l3m_revenues,
                a.l3m_units,
                s.unit_01, s.unit_02, s.unit_03, s.unit_04, s.unit_05, s.unit_06,
                s.unit_07, s.unit_08, s.unit_09, s.unit_10, s.unit_11, s.unit_12
            FROM asin a
            LEFT JOIN seasonality s ON a.seasonality = s.name
            WHERE a.brand_id IS NOT NULL
            ORDER BY a.id
        """
        
        cursor.execute(query)
        asins = cursor.fetchall()
        
        print(f"Found {len(asins)} ASINs to process\n")
        
        # Months for forecast period (Nov 2025 - Oct 2026)
        forecast_months = [
            ('2025-11-01', 11),  # November 2025
            ('2025-12-01', 12),  # December 2025
            ('2026-01-01', 1),   # January 2026
            ('2026-02-01', 2),   # February 2026
            ('2026-03-01', 3),   # March 2026
            ('2026-04-01', 4),   # April 2026
            ('2026-05-01', 5),   # May 2026
            ('2026-06-01', 6),   # June 2026
            ('2026-07-01', 7),   # July 2026
            ('2026-08-01', 8),   # August 2026
            ('2026-09-01', 9),   # September 2026
            ('2026-10-01', 10),  # October 2026
        ]
        
        forecast_records = []
        asins_processed = 0
        asins_eol = 0
        asins_no_seasonality = 0
        asins_success = 0
        
        for asin in asins:
            asin_id = asin['asin_id']
            asin_code = asin['asin']
            is_eol = asin['eol'] == 1
            ltm_revenues = float(asin['ltm_revenues'] or 0)
            ltm_units = float(asin['ltm_units'] or 0)
            l3m_revenues = float(asin['l3m_revenues'] or 0)
            l3m_units = float(asin['l3m_units'] or 0)
            
            asins_processed += 1
            
            # Show progress
            if asins_processed % 1000 == 0:
                progress_pct = (asins_processed / len(asins)) * 100
                print(f"Progress: {asins_processed}/{len(asins)} ({progress_pct:.1f}%)")
            
            # Case 1: EOL products - forecast is 0
            if is_eol:
                asins_eol += 1
                for month_date, month_num in forecast_months:
                    forecast_records.append((asin_id, 'Net units', month_date, 0))
                    forecast_records.append((asin_id, 'Net revenue', month_date, 0))
                continue
            
            # Case 2: No seasonality assigned - skip
            if not asin['seasonality'] or not asin['unit_08']:
                asins_no_seasonality += 1
                for month_date, month_num in forecast_months:
                    forecast_records.append((asin_id, 'Net units', month_date, 0))
                    forecast_records.append((asin_id, 'Net revenue', month_date, 0))
                continue
            
            # Case 3: Active product with seasonality
            # Calculate base period sum (Aug + Sep + Oct 2024 from seasonality)
            base_period_sum = (
                float(asin['unit_08'] or 0) +
                float(asin['unit_09'] or 0) +
                float(asin['unit_10'] or 0)
            )
            
            if base_period_sum == 0:
                # Can't compute forecast without base period
                asins_no_seasonality += 1
                for month_date, month_num in forecast_months:
                    forecast_records.append((asin_id, 'Net units', month_date, 0))
                    forecast_records.append((asin_id, 'Net revenue', month_date, 0))
                continue
            
            # Calculate total forecasted units for next 12 months
            # Using l3m_units (Aug-Sep-Oct 2025) to capture most recent trend
            # Compare actual L3M performance to seasonality factors for those months
            total_next_12_months = l3m_units / base_period_sum
            
            # Calculate ASP (Average Selling Price)
            asp = 0
            if l3m_units > 0:
                asp = l3m_revenues / l3m_units
            elif ltm_units > 0:
                # Fallback to LTM if L3M not available
                asp = ltm_revenues / ltm_units
            
            # Generate forecasts for each month
            for month_date, month_num in forecast_months:
                # Get seasonality factor for this month
                unit_col = f'unit_{month_num:02d}'
                seasonality_factor = float(asin[unit_col] or 0)
                
                # Calculate forecasted units
                forecasted_units = seasonality_factor * total_next_12_months
                
                # Calculate forecasted revenue
                forecasted_revenue = forecasted_units * asp
                
                # Store forecasts
                forecast_records.append((asin_id, 'Net units', month_date, forecasted_units))
                forecast_records.append((asin_id, 'Net revenue', month_date, forecasted_revenue))
            
            asins_success += 1
        
        # Batch insert forecast records
        if forecast_records:
            print(f"\nInserting {len(forecast_records)} forecast records...")
            insert_query = """
                INSERT INTO forecast_asin (asin_id, metric, month, value)
                VALUES (%s, %s, %s, %s)
            """
            cursor.executemany(insert_query, forecast_records)
            conn.commit()
            print(f"✓ Inserted {len(forecast_records)} forecast records")
        
        print("\n" + "=" * 80)
        print("ASIN Forecast Summary:")
        print(f"  Total ASINs processed: {asins_processed}")
        print(f"  ASINs with forecasts: {asins_success}")
        print(f"  EOL ASINs (0 forecast): {asins_eol}")
        print(f"  ASINs without seasonality: {asins_no_seasonality}")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n✗ Error computing ASIN forecasts: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
        raise
    finally:
        cursor.close()

def compute_brand_forecasts(conn):
    """Aggregate ASIN forecasts to brand level"""
    print("\nComputing Brand Forecasts...")
    print("=" * 80)
    
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    
    try:
        # Clear existing brand forecast data
        print("Clearing existing brand forecast data...")
        cursor.execute("DELETE FROM forecast_brand")
        conn.commit()
        print(f"✓ Cleared existing brand forecasts\n")
        
        # Aggregate ASIN forecasts to brand level
        print("Aggregating ASIN forecasts to brands...")
        query = """
            INSERT INTO forecast_brand (brand_id, metric, month, value)
            SELECT 
                a.brand_id,
                fa.metric,
                fa.month,
                SUM(fa.value) as total_value
            FROM forecast_asin fa
            INNER JOIN asin a ON fa.asin_id = a.id
            WHERE a.brand_id IS NOT NULL
            GROUP BY a.brand_id, fa.metric, fa.month
        """
        
        cursor.execute(query)
        rows_inserted = cursor.rowcount
        conn.commit()
        
        print(f"✓ Created {rows_inserted} brand forecast records")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n✗ Error computing brand forecasts: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
        raise
    finally:
        cursor.close()

def main():
    """Main execution function"""
    print("\n" + "=" * 80)
    print("FORECAST COMPUTATION")
    print("Period: November 2025 - October 2026")
    print("=" * 80 + "\n")
    
    conn = get_connection()
    
    try:
        # Step 1: Compute ASIN forecasts
        compute_asin_forecasts(conn)
        
        # Step 2: Aggregate to brand forecasts
        compute_brand_forecasts(conn)
        
        print("\n" + "=" * 80)
        print("✓ FORECAST COMPUTATION COMPLETED SUCCESSFULLY!")
        print("=" * 80 + "\n")
        
    except Exception as e:
        print(f"\n✗ Fatal error: {e}")
        sys.exit(1)
    finally:
        conn.close()

if __name__ == '__main__':
    main()

