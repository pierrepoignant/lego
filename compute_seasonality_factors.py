#!/usr/bin/env python3
"""
Compute Seasonality Factors

This script computes seasonality factors for each seasonality in the database
using 2024 data from the financials table.

For each seasonality:
1. Get all ASINs that belong to that seasonality (excluding EOL items)
2. Sum the units for each month of 2024
3. Divide by total units for the year to get monthly percentages (sum = 1.0)
4. Store percentages in the seasonality table (unit_01 through unit_12)

Note: EOL (End of Life) items are excluded from the calculation to ensure
      seasonality factors reflect only active products.
"""

import pymysql
from decimal import Decimal
import sys
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

def compute_seasonality_factors():
    """Compute seasonality factors based on 2024 data"""
    print("Starting seasonality factor computation...")
    print("=" * 80)
    
    conn = get_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    
    try:
        # Get all seasonalities
        cursor.execute("SELECT id, name FROM seasonality ORDER BY name")
        seasonalities = cursor.fetchall()
        
        if not seasonalities:
            print("No seasonalities found in the database.")
            return
        
        print(f"Found {len(seasonalities)} seasonalities to process\n")
        
        for seasonality in seasonalities:
            seasonality_id = seasonality['id']
            seasonality_name = seasonality['name']
            
            print(f"Processing: {seasonality_name} (ID: {seasonality_id})")
            
            # Query to get monthly units for all ASINs with this seasonality in 2024
            # Using financials table joined with asin table
            # Excluding EOL (End of Life) items from the calculation
            query = """
                SELECT 
                    MONTH(f.month) as month_num,
                    SUM(f.value) as total_units
                FROM financials f
                INNER JOIN asin a ON f.asin_id = a.id
                WHERE a.seasonality = %s
                AND LOWER(f.metric) = 'net units'
                AND YEAR(f.month) = 2024
                AND (a.eol IS NULL OR a.eol = 0)
                GROUP BY MONTH(f.month)
                ORDER BY MONTH(f.month)
            """
            
            cursor.execute(query, [seasonality_name])
            monthly_data = cursor.fetchall()
            
            # Initialize monthly units array (12 months)
            monthly_units = [0.0] * 12
            
            # Fill in the monthly data
            for row in monthly_data:
                month_idx = row['month_num'] - 1  # Convert to 0-based index
                monthly_units[month_idx] = float(row['total_units']) if row['total_units'] else 0.0
            
            # Calculate total units for the year
            total_units = sum(monthly_units)
            
            if total_units == 0:
                print(f"  ⚠ No units found for {seasonality_name} in 2024, skipping...")
                continue
            
            # Calculate percentages (factors) for each month
            factors = [Decimal(str(units / total_units)) for units in monthly_units]
            
            # Verify that sum is approximately 1.0
            factor_sum = sum(factors)
            print(f"  Total units in 2024: {total_units:,.0f}")
            print(f"  Factor sum: {factor_sum:.4f}")
            
            # Display monthly breakdown
            months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
            print("  Monthly factors:")
            for i, (month, factor) in enumerate(zip(months, factors)):
                print(f"    {month}: {factor:.4f} ({monthly_units[i]:,.0f} units)")
            
            # Update the seasonality table
            update_query = """
                UPDATE seasonality
                SET 
                    unit_01 = %s, unit_02 = %s, unit_03 = %s, unit_04 = %s,
                    unit_05 = %s, unit_06 = %s, unit_07 = %s, unit_08 = %s,
                    unit_09 = %s, unit_10 = %s, unit_11 = %s, unit_12 = %s
                WHERE id = %s
            """
            
            cursor.execute(update_query, [
                factors[0], factors[1], factors[2], factors[3],
                factors[4], factors[5], factors[6], factors[7],
                factors[8], factors[9], factors[10], factors[11],
                seasonality_id
            ])
            
            print(f"  ✓ Updated seasonality factors for {seasonality_name}\n")
        
        # Commit all changes
        conn.commit()
        print("=" * 80)
        print("✓ Seasonality factor computation completed successfully!")
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        conn.rollback()
        sys.exit(1)
    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    compute_seasonality_factors()

