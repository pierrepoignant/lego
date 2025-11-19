#!/usr/bin/env python3
"""
Compute LTM (Last Twelve Months) metrics for all ASINs and/or Brands
LTM = Nov 2024 - Oct 2025

This script calculates and updates:
1. ltm_revenues - Total Net revenue for Nov 2024 - Oct 2025
2. ltm_cm3 - Total CM3 for Nov 2024 - Oct 2025
3. ltm_brand_ebitda - (CM3 / Net revenue) * 100 for the LTM period
4. stock_value - Total inventory/stock value for the LTM period

Usage:
    python compute_ltm_metrics.py                    # Compute both ASINs and brands
    python compute_ltm_metrics.py --brands-only      # Compute only brands
    python compute_ltm_metrics.py --asins-only       # Compute only ASINs
    python compute_ltm_metrics.py --brand-id 3       # Compute specific brand only
    python compute_ltm_metrics.py --debug            # Show detailed debug info
"""

import pymysql
import os
import configparser
from datetime import datetime
import argparse

def get_config():
    """Read configuration from config.ini"""
    config = configparser.ConfigParser()
    config_path = os.path.join(os.path.dirname(__file__), 'config.ini')
    config.read(config_path)
    return config

def get_connection():
    """Create database connection"""
    config = get_config()
    
    host = os.getenv('DB_HOST', config.get('database', 'host', fallback='127.0.0.1'))
    port = int(os.getenv('DB_PORT', config.get('database', 'port', fallback='3306')))
    user = os.getenv('DB_USER', config.get('database', 'user', fallback='root'))
    password = os.getenv('DB_PASSWORD', config.get('database', 'password', fallback=''))
    database = os.getenv('DB_NAME', config.get('database', 'database', fallback='lego'))
    
    return pymysql.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        database=database,
        charset='utf8mb4'
    )

def compute_asin_ltm_metrics(conn, specific_brand_id=None):
    """Compute LTM metrics for all ASINs or ASINs of a specific brand"""
    import time
    start_time = time.time()
    
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    
    print("=" * 80)
    if specific_brand_id:
        print(f"Computing LTM Metrics for ASINs in Brand ID: {specific_brand_id}")
    else:
        print("Computing LTM Metrics for All ASINs")
    print("LTM Period: November 2024 - October 2025")
    print("=" * 80)
    print()
    
    # Get all ASINs or ASINs for specific brand
    if specific_brand_id:
        cursor.execute("""
            SELECT a.id, a.asin, b.brand 
            FROM asin a
            LEFT JOIN brand b ON a.brand_id = b.id
            WHERE a.brand_id = %s 
            ORDER BY a.id
        """, [specific_brand_id])
    else:
        cursor.execute("SELECT id, asin FROM asin ORDER BY id")
    asins = cursor.fetchall()
    
    if not asins:
        print(f"❌ No ASINs found for brand ID {specific_brand_id}")
        return 0, []
    
    print(f"Found {len(asins)} ASINs to process")
    print()
    
    updated_count = 0
    errors = []
    
    print(f"{'='*80}")
    print(f"Progress Tracking:")
    print(f"{'='*80}")
    
    for idx, asin_record in enumerate(asins, 1):
        asin_id = asin_record['id']
        asin_code = asin_record['asin']
        
        # Show progress for every ASIN
        if idx % 10 == 0:
            progress_pct = (idx / len(asins)) * 100
            print(f"[ASINs] {idx}/{len(asins)} ({progress_pct:.1f}%) - Latest: {asin_code}")
        
        try:
            # Query to get LTM financials from summary table (Nov 2024 - Oct 2025)
            # Sum across all marketplaces (ASIN table doesn't have 'ALL' marketplace)
            # Include both case variations for metric names
            query = """
                SELECT 
                    metric,
                    SUM(value) as total_value
                FROM financials_summary_monthly_asin_marketplace
                WHERE asin_id = %s
                AND (
                    (YEAR(month) = 2024 AND MONTH(month) >= 11) OR
                    (YEAR(month) = 2025 AND MONTH(month) <= 10)
                )
                AND (LOWER(metric) = 'net revenue' OR LOWER(metric) = 'cm3')
                GROUP BY metric
            """
            
            cursor.execute(query, [asin_id])
            results = cursor.fetchall()
            
            # Debug: Print query results for first 5 ASINs
            if idx <= 5:
                print(f"\n[DEBUG] ASIN {asin_code} (ID: {asin_id}) - Query returned {len(results)} rows:")
                for row in results:
                    print(f"  metric='{row['metric']}', total_value={row['total_value']}")
            
            # Extract metrics (case-insensitive comparison)
            ltm_revenues = 0
            ltm_cm3 = 0
            
            for row in results:
                metric_name = row['metric'].lower() if row['metric'] else ''
                if metric_name == 'net revenue':
                    ltm_revenues = float(row['total_value']) if row['total_value'] else 0
                elif metric_name == 'cm3':
                    ltm_cm3 = float(row['total_value']) if row['total_value'] else 0
            
            # Debug: Print computed values for first 5 ASINs
            if idx <= 5:
                ltm_brand_ebitda_preview = (ltm_cm3 / ltm_revenues * 100) if ltm_revenues > 0 else 0
                print(f"  Computed: Revenue=${ltm_revenues:,.2f}, CM3=${ltm_cm3:,.2f}, EBITDA={ltm_brand_ebitda_preview:.2f}%")
            
            # Get stock data from stock table
            stock_query = """
                SELECT SUM(value) as total_stock
                FROM stock
                WHERE asin_id = %s
                AND (
                    (YEAR(month) = 2024 AND MONTH(month) >= 11) OR
                    (YEAR(month) = 2025 AND MONTH(month) <= 10)
                )
            """
            cursor.execute(stock_query, [asin_id])
            stock_result = cursor.fetchone()
            ltm_stock = float(stock_result['total_stock']) if stock_result and stock_result['total_stock'] else 0
            
            # Calculate brand EBITDA %
            ltm_brand_ebitda = (ltm_cm3 / ltm_revenues * 100) if ltm_revenues > 0 else 0
            
            # Update ASIN record
            update_query = """
                UPDATE asin
                SET ltm_revenues = %s,
                    ltm_cm3 = %s,
                    ltm_brand_ebitda = %s,
                    stock_value = %s,
                    ltm_updated_at = NOW()
                WHERE id = %s
            """
            
            cursor.execute(update_query, [
                ltm_revenues,
                ltm_cm3,
                ltm_brand_ebitda,
                ltm_stock,
                asin_id
            ])
            
            updated_count += 1
        
        except Exception as e:
            error_msg = f"Error processing ASIN {asin_code} (ID: {asin_id}): {str(e)}"
            errors.append(error_msg)
            print(f"❌ {error_msg}")
    
    # Commit all changes
    conn.commit()
    
    print()
    print("=" * 80)
    print("Computation Complete!")
    print("=" * 80)
    print(f"✅ Successfully updated: {updated_count} ASINs")
    
    if errors:
        print(f"❌ Errors encountered: {len(errors)}")
        print()
        print("Error details:")
        for error in errors[:10]:  # Show first 10 errors
            print(f"  - {error}")
        if len(errors) > 10:
            print(f"  ... and {len(errors) - 10} more errors")
    
    print()
    print("Summary Statistics:")
    
    # Get some statistics
    cursor.execute("""
        SELECT 
            COUNT(*) as total_asins,
            SUM(ltm_revenues) as total_revenues,
            SUM(ltm_cm3) as total_cm3,
            AVG(ltm_brand_ebitda) as avg_ebitda,
            MAX(ltm_revenues) as max_revenue,
            MIN(ltm_revenues) as min_revenue
        FROM asin
        WHERE ltm_revenues > 0
    """)
    
    stats = cursor.fetchone()
    
    if stats and stats['total_asins']:
        print(f"  Total ASINs with revenue: {stats['total_asins']}")
        print(f"  Total LTM Revenue: ${stats['total_revenues']:,.2f}")
        print(f"  Total LTM CM3: ${stats['total_cm3']:,.2f}")
        print(f"  Average Brand EBITDA: {stats['avg_ebitda']:.2f}%")
        print(f"  Highest Revenue ASIN: ${stats['max_revenue']:,.2f}")
        print(f"  Lowest Revenue ASIN: ${stats['min_revenue']:,.2f}")
    
    cursor.close()
    
    elapsed_time = time.time() - start_time
    
    print()
    print(f"⏱️  ASIN computation completed in {elapsed_time:.2f} seconds ({elapsed_time/60:.2f} minutes)")
    return updated_count, errors

def compute_brand_ltm_metrics(conn, specific_brand_id=None, debug=False):
    """Compute LTM metrics for all Brands or a specific brand"""
    import time
    start_time = time.time()
    
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    
    print("=" * 80)
    if specific_brand_id:
        print(f"Computing LTM Metrics for Brand ID: {specific_brand_id}")
    else:
        print("Computing LTM Metrics for All Brands")
    print("LTM Period: November 2024 - October 2025")
    print("=" * 80)
    print()
    
    # Get all brands or specific brand
    if specific_brand_id:
        cursor.execute("SELECT id, brand FROM brand WHERE id = %s", [specific_brand_id])
    else:
        cursor.execute("SELECT id, brand FROM brand WHERE (`group` IS NULL OR `group` != 'stock') ORDER BY id")
    brands = cursor.fetchall()
    
    if not brands:
        print(f"❌ No brand found with ID {specific_brand_id}")
        return 0, []
    
    print(f"Found {len(brands)} brands to process")
    print()
    
    updated_count = 0
    errors = []
    
    print(f"{'='*80}")
    print(f"Progress Tracking:")
    print(f"{'='*80}")
    
    for idx, brand_record in enumerate(brands, 1):
        brand_id = brand_record['id']
        brand_name = brand_record['brand']
        
        # Show progress for every brand
        progress_pct = (idx / len(brands)) * 100
        print(f"[Brands] {idx}/{len(brands)} ({progress_pct:.1f}%) - Processing: {brand_name}")
        
        try:
            # Query to get LTM financials from brand summary table (Nov 2024 - Oct 2025)
            # Use the brand summary table which already aggregates all ASINs for the brand
            # Use case-insensitive metric matching
            query = """
                SELECT 
                    metric,
                    SUM(total_value) as total_value
                FROM financials_summary_monthly_brand
                WHERE brand_id = %s
                AND marketplace = 'ALL'
                AND (
                    (YEAR(month) = 2024 AND MONTH(month) >= 11) OR
                    (YEAR(month) = 2025 AND MONTH(month) <= 10)
                )
                AND (LOWER(metric) = 'net revenue' OR LOWER(metric) = 'cm3')
                GROUP BY metric
            """
            
            cursor.execute(query, [brand_id])
            results = cursor.fetchall()
            
            if debug:
                print(f"\n  [DEBUG] Brand: {brand_name} (ID: {brand_id})")
                print(f"  [DEBUG] Query returned {len(results)} metric rows")
                for row in results:
                    print(f"  [DEBUG]   - {row['metric']}: ${row['total_value']:,.2f}")
            
            # Extract metrics (case-insensitive comparison)
            ltm_revenues = 0
            ltm_cm3 = 0
            
            for row in results:
                metric_name = row['metric'].lower() if row['metric'] else ''
                if metric_name == 'net revenue':
                    ltm_revenues = float(row['total_value']) if row['total_value'] else 0
                elif metric_name == 'cm3':
                    ltm_cm3 = float(row['total_value']) if row['total_value'] else 0
            
            if debug and ltm_revenues == 0:
                print(f"  [DEBUG] ⚠️ WARNING: Brand {brand_name} has $0 LTM revenue!")
            
            # Get stock data from stock table for all ASINs in this brand
            # Join through asin table to ensure we get all stock for the brand's ASINs
            stock_query = """
                SELECT SUM(s.value) as total_stock
                FROM stock s
                INNER JOIN asin a ON s.asin_id = a.id
                WHERE a.brand_id = %s
                AND (
                    (YEAR(s.month) = 2024 AND MONTH(s.month) >= 11) OR
                    (YEAR(s.month) = 2025 AND MONTH(s.month) <= 10)
                )
            """
            cursor.execute(stock_query, [brand_id])
            stock_result = cursor.fetchone()
            ltm_stock = float(stock_result['total_stock']) if stock_result and stock_result['total_stock'] else 0
            
            # Calculate brand EBITDA %
            ltm_brand_ebitda = (ltm_cm3 / ltm_revenues * 100) if ltm_revenues > 0 else 0
            
            # Update brand record
            update_query = """
                UPDATE brand
                SET ltm_revenues = %s,
                    ltm_cm3 = %s,
                    ltm_brand_ebitda = %s,
                    stock_value = %s,
                    ltm_updated_at = NOW()
                WHERE id = %s
            """
            
            cursor.execute(update_query, [
                ltm_revenues,
                ltm_cm3,
                ltm_brand_ebitda,
                ltm_stock,
                brand_id
            ])
            
            if debug:
                print(f"  [DEBUG] ✅ Updated: Revenue=${ltm_revenues:,.2f}, CM3=${ltm_cm3:,.2f}, EBITDA={ltm_brand_ebitda:.2f}%, Stock=${ltm_stock:,.2f}\n")
            
            updated_count += 1
        
        except Exception as e:
            error_msg = f"Error processing brand {brand_name} (ID: {brand_id}): {str(e)}"
            errors.append(error_msg)
            print(f"❌ {error_msg}")
    
    # Commit all changes
    conn.commit()
    
    print()
    print("=" * 80)
    print("Brand Computation Complete!")
    print("=" * 80)
    print(f"✅ Successfully updated: {updated_count} brands")
    
    if errors:
        print(f"❌ Errors encountered: {len(errors)}")
        print()
        print("Error details:")
        for error in errors[:10]:  # Show first 10 errors
            print(f"  - {error}")
        if len(errors) > 10:
            print(f"  ... and {len(errors) - 10} more errors")
    
    print()
    print("Summary Statistics:")
    
    # Get some statistics
    cursor.execute("""
        SELECT 
            COUNT(*) as total_brands,
            SUM(ltm_revenues) as total_revenues,
            SUM(ltm_cm3) as total_cm3,
            AVG(ltm_brand_ebitda) as avg_ebitda,
            MAX(ltm_revenues) as max_revenue,
            MIN(ltm_revenues) as min_revenue
        FROM brand
        WHERE ltm_revenues > 0
    """)
    
    stats = cursor.fetchone()
    
    if stats and stats['total_brands']:
        print(f"  Total brands with revenue: {stats['total_brands']}")
        print(f"  Total LTM Revenue: ${stats['total_revenues']:,.2f}")
        print(f"  Total LTM CM3: ${stats['total_cm3']:,.2f}")
        print(f"  Average Brand EBITDA: {stats['avg_ebitda']:.2f}%")
        print(f"  Highest Revenue Brand: ${stats['max_revenue']:,.2f}")
        print(f"  Lowest Revenue Brand: ${stats['min_revenue']:,.2f}")
    
    cursor.close()
    
    elapsed_time = time.time() - start_time
    
    print()
    print(f"⏱️  Brand computation completed in {elapsed_time:.2f} seconds ({elapsed_time/60:.2f} minutes)")
    return updated_count, errors

def compute_ltm_metrics(brands_only=False, asins_only=False, specific_brand_id=None, asins_for_brand_id=None, debug=False):
    """Main function to compute LTM metrics for both ASINs and Brands"""
    import time
    total_start_time = time.time()
    
    conn = get_connection()
    
    asin_updated = 0
    asin_errors = []
    brand_updated = 0
    brand_errors = []
    
    # Compute ASIN metrics
    if asins_for_brand_id:
        # Compute ASINs for specific brand only
        asin_updated, asin_errors = compute_asin_ltm_metrics(conn, asins_for_brand_id)
    elif asins_only or (not brands_only and not specific_brand_id):
        # Compute all ASINs if:
        # - Explicitly requested with --asins-only
        # - OR computing both (not brands_only and not specific_brand_id)
        asin_updated, asin_errors = compute_asin_ltm_metrics(conn)
        
        if not asins_only:
            print("\n" + "="*80)
            print("Moving on to Brands...")
            print("="*80 + "\n")
    
    # Compute Brand metrics (unless asins_only or asins_for_brand_id)
    if not asins_only and not asins_for_brand_id:
        brand_updated, brand_errors = compute_brand_ltm_metrics(conn, specific_brand_id, debug)
    
    conn.close()
    
    total_elapsed = time.time() - total_start_time
    
    print("\n" + "=" * 80)
    print("✨ All Done! ✨")
    print("=" * 80)
    if asins_only or asins_for_brand_id or (not brands_only and not specific_brand_id):
        print(f"📊 ASINs updated: {asin_updated}")
    if not asins_only and not asins_for_brand_id:
        print(f"🏢 Brands updated: {brand_updated}")
    print(f"⏱️  Total time: {total_elapsed:.2f} seconds ({total_elapsed/60:.2f} minutes)")
    print("=" * 80)
    print()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Compute LTM metrics for ASINs and/or Brands',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python compute_ltm_metrics.py                         # Compute both ASINs and brands
  python compute_ltm_metrics.py --brands-only           # Compute only brands
  python compute_ltm_metrics.py --asins-only            # Compute only ASINs
  python compute_ltm_metrics.py --brand-id 3            # Compute specific brand only
  python compute_ltm_metrics.py --asins-for-brand-id 3  # Compute ASINs for brand 3 only
  python compute_ltm_metrics.py --brands-only --debug   # Debug mode for brands
        """
    )
    
    parser.add_argument('--brands-only', action='store_true',
                       help='Compute LTM metrics for brands only (skip ASINs)')
    parser.add_argument('--asins-only', action='store_true',
                       help='Compute LTM metrics for ASINs only (skip brands)')
    parser.add_argument('--brand-id', type=int, metavar='ID',
                       help='Compute LTM metrics for a specific brand ID only')
    parser.add_argument('--asins-for-brand-id', type=int, metavar='ID',
                       help='Compute LTM metrics for ASINs of a specific brand ID only')
    parser.add_argument('--debug', action='store_true',
                       help='Show detailed debug information for each brand')
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.brands_only and args.asins_only:
        print("❌ Error: Cannot use both --brands-only and --asins-only")
        exit(1)
    
    if args.brand_id and args.asins_only:
        print("❌ Error: Cannot use --brand-id with --asins-only")
        exit(1)
    
    if args.asins_for_brand_id and args.brands_only:
        print("❌ Error: Cannot use --asins-for-brand-id with --brands-only")
        exit(1)
    
    if args.asins_for_brand_id and args.brand_id:
        print("❌ Error: Cannot use both --asins-for-brand-id and --brand-id")
        exit(1)
    
    try:
        compute_ltm_metrics(
            brands_only=args.brands_only,
            asins_only=args.asins_only,
            specific_brand_id=args.brand_id,
            asins_for_brand_id=args.asins_for_brand_id,
            debug=args.debug
        )
    except Exception as e:
        print(f"Fatal error: {str(e)}")
        import traceback
        traceback.print_exc()
        exit(1)


