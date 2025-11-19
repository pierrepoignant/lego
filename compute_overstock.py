#!/usr/bin/env python3
"""
Compute Overstock Values for ASINs and Brands

This script computes overstock metrics based on current stock and forecasted demand:

For ASINs:
1. stock_overstock_unit = stock_units - (sum of ASIN unit forecast for next 6 months)
   - Next 6 months: Nov 2025, Dec 2025, Jan 2026, Feb 2026, Mar 2026, Apr 2026
2. stock_overstock_value = stock_overstock_unit * unit_COGS
   - unit_COGS = stock_value / stock_units (if negative or zero, COGS is 0)

For Brands:
1. Aggregates overstock values from all ASINs belonging to the brand
2. stock_overstock_unit = SUM(asin.stock_overstock_unit) for all brand ASINs
3. stock_overstock_value = SUM(asin.stock_overstock_value) for all brand ASINs

Usage:
    python compute_overstock.py                # Compute both ASINs and brands
    python compute_overstock.py --asins-only   # Compute only ASINs
    python compute_overstock.py --brands-only  # Compute only brands
"""

import pymysql
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

def compute_asin_overstock(conn):
    """Compute overstock values for all ASINs using efficient SQL"""
    print("Computing ASIN Overstock Values...")
    print("=" * 80)
    
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    
    try:
        # Step 1: Update overstock units and values in a single efficient query
        print("Calculating overstock values...")
        
        update_query = """
            UPDATE asin a
            LEFT JOIN (
                SELECT 
                    asin_id,
                    SUM(value) as forecast_6m_units
                FROM forecast_asin
                WHERE metric = 'Net units'
                AND month IN (
                    '2025-11-01', '2025-12-01', '2026-01-01', 
                    '2026-02-01', '2026-03-01', '2026-04-01'
                )
                GROUP BY asin_id
            ) f ON a.id = f.asin_id
            SET 
                a.stock_overstock_unit = GREATEST(
                    0,
                    a.stock_units - COALESCE(f.forecast_6m_units, 0)
                ),
                a.stock_overstock_value = CASE
                    WHEN a.stock_units > 0 AND a.stock_value > 0 
                         AND (a.stock_units - COALESCE(f.forecast_6m_units, 0)) > 0
                    THEN (a.stock_units - COALESCE(f.forecast_6m_units, 0)) * (a.stock_value / a.stock_units)
                    ELSE 0
                END
            WHERE a.brand_id IS NOT NULL
        """
        
        cursor.execute(update_query)
        rows_updated = cursor.rowcount
        conn.commit()
        
        print(f"✓ Updated {rows_updated} ASINs")
        
        # Get statistics
        stats_query = """
            SELECT 
                COUNT(*) as total_asins,
                SUM(CASE WHEN stock_units = 0 THEN 1 ELSE 0 END) as zero_stock,
                SUM(CASE WHEN stock_overstock_unit = 0 THEN 1 ELSE 0 END) as no_overstock,
                SUM(CASE WHEN stock_overstock_unit > 0 THEN 1 ELSE 0 END) as has_overstock,
                SUM(stock_overstock_value) as total_overstock_value
            FROM asin
            WHERE brand_id IS NOT NULL
        """
        
        cursor.execute(stats_query)
        stats = cursor.fetchone()
        
        print("\n" + "=" * 80)
        print("ASIN Overstock Summary:")
        print(f"  Total ASINs processed: {stats['total_asins']}")
        print(f"  ASINs with overstock: {stats['has_overstock']}")
        print(f"  ASINs with zero/no overstock: {stats['no_overstock']}")
        print(f"  ASINs with zero stock: {stats['zero_stock']}")
        print(f"  Total overstock value: ${stats['total_overstock_value']:,.2f}")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n✗ Error computing ASIN overstock: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
        raise
    finally:
        cursor.close()

def compute_brand_overstock(conn):
    """Compute overstock values for all brands by aggregating from ASINs"""
    print("\nComputing Brand Overstock Values (aggregating from ASINs)...")
    print("=" * 80)
    
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    
    try:
        # Step 1: Aggregate overstock from ASINs to Brands
        print("Aggregating overstock values from ASINs...")
        
        update_query = """
            UPDATE brand b
            LEFT JOIN (
                SELECT 
                    a.brand_id,
                    SUM(a.stock_overstock_unit) as total_overstock_units,
                    SUM(a.stock_overstock_value) as total_overstock_value
                FROM asin a
                WHERE a.brand_id IS NOT NULL
                GROUP BY a.brand_id
            ) agg ON b.id = agg.brand_id
            SET 
                b.stock_overstock_unit = COALESCE(agg.total_overstock_units, 0),
                b.stock_overstock_value = COALESCE(agg.total_overstock_value, 0)
        """
        
        cursor.execute(update_query)
        rows_updated = cursor.rowcount
        conn.commit()
        
        print(f"✓ Updated {rows_updated} brands")
        
        # Get statistics
        stats_query = """
            SELECT 
                COUNT(*) as total_brands,
                SUM(CASE WHEN stock_units = 0 THEN 1 ELSE 0 END) as zero_stock,
                SUM(CASE WHEN stock_overstock_unit = 0 THEN 1 ELSE 0 END) as no_overstock,
                SUM(CASE WHEN stock_overstock_unit > 0 THEN 1 ELSE 0 END) as has_overstock,
                SUM(stock_overstock_value) as total_overstock_value
            FROM brand
        """
        
        cursor.execute(stats_query)
        stats = cursor.fetchone()
        
        print("\n" + "=" * 80)
        print("Brand Overstock Summary:")
        print(f"  Total brands processed: {stats['total_brands']}")
        print(f"  Brands with overstock: {stats['has_overstock']}")
        print(f"  Brands with zero/no overstock: {stats['no_overstock']}")
        print(f"  Brands with zero stock: {stats['zero_stock']}")
        print(f"  Total overstock value: ${stats['total_overstock_value']:,.2f}")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n✗ Error computing brand overstock: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
        raise
    finally:
        cursor.close()

def main():
    """Main execution function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Compute overstock values for ASINs and brands')
    parser.add_argument('--asins-only', action='store_true', help='Compute only ASINs')
    parser.add_argument('--brands-only', action='store_true', help='Compute only brands')
    args = parser.parse_args()
    
    print("\n" + "=" * 80)
    print("OVERSTOCK COMPUTATION")
    print("Period: Next 6 months (Nov 2025 - Apr 2026)")
    print("=" * 80 + "\n")
    
    conn = get_connection()
    
    try:
        if args.brands_only:
            # Compute only brands
            compute_brand_overstock(conn)
        elif args.asins_only:
            # Compute only ASINs
            compute_asin_overstock(conn)
        else:
            # Compute both (default)
            compute_asin_overstock(conn)
            compute_brand_overstock(conn)
        
        print("\n" + "=" * 80)
        print("✓ OVERSTOCK COMPUTATION COMPLETED SUCCESSFULLY!")
        print("=" * 80 + "\n")
        
    except Exception as e:
        print(f"\n✗ Fatal error: {e}")
        sys.exit(1)
    finally:
        conn.close()

if __name__ == '__main__':
    main()
