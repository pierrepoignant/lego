#!/usr/bin/env python3
"""
Refresh Summary Tables for Dashboard Performance
=================================================
This script refreshes the pre-aggregated summary tables used by the dashboard.

Run this script:
  - Initially after creating the summary tables
  - Daily via cron job (recommended: 2-3 AM)
  - After bulk imports of financial data
  - Manually when data seems stale

Usage:
    python3 refresh_summaries.py
    
    # Or with custom config:
    python3 refresh_summaries.py --config ../custom_config.ini
"""

import pymysql
import configparser
import sys
import os
import time
from datetime import datetime

def get_config(config_path=None):
    """Read configuration from config.ini"""
    config = configparser.ConfigParser()
    
    if config_path is None:
        # Look for config.ini in parent directory
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.ini')
    
    if not os.path.exists(config_path):
        print(f"ERROR: Config file not found at {config_path}")
        sys.exit(1)
    
    config.read(config_path)
    return config

def get_connection(config):
    """Create database connection"""
    # Read from config.ini first, fall back to environment variables
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

def execute_sql_file(cursor, conn, sql_file_path):
    """Execute a SQL file"""
    print(f"Reading SQL from: {sql_file_path}")
    
    if not os.path.exists(sql_file_path):
        print(f"ERROR: SQL file not found at {sql_file_path}")
        return False
    
    with open(sql_file_path, 'r') as f:
        sql_content = f.read()
    
    # Split into statements and execute
    statements = [s.strip() for s in sql_content.split(';') if s.strip()]
    
    for i, statement in enumerate(statements, 1):
        # Skip comments and empty statements
        if statement.startswith('--') or not statement:
            continue
        
        # Execute statement
        try:
            cursor.execute(statement)
            # If it's a SELECT, fetch and display results
            if statement.strip().upper().startswith('SELECT'):
                results = cursor.fetchall()
                for row in results:
                    print(f"  {row}")
            # Commit after INSERT, UPDATE, DELETE, TRUNCATE to make data visible
            elif any(statement.strip().upper().startswith(cmd) for cmd in ['INSERT', 'UPDATE', 'DELETE', 'TRUNCATE']):
                conn.commit()
        except pymysql.Error as e:
            print(f"ERROR executing statement {i}: {e}")
            return False
    
    return True

def refresh_summary_tables(config_path=None, refresh_asin=True, refresh_brand=True, refresh_category=True):
    """Main function to refresh summary tables"""
    print("=" * 70)
    print("Dashboard Summary Tables Refresh")
    print("=" * 70)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Show what will be refreshed
    tables_to_refresh = []
    if refresh_asin:
        tables_to_refresh.append("ASIN+Marketplace")
    if refresh_brand:
        tables_to_refresh.append("Brand")
    if refresh_category:
        tables_to_refresh.append("Category")
    
    print(f"Tables to refresh: {', '.join(tables_to_refresh)}")
    print()
    
    start_time = time.time()
    
    # Get configuration
    config = get_config(config_path)
    print(f"Database: {config.get('database', 'database', fallback='lego')}")
    print(f"Host: {config.get('database', 'host', fallback='127.0.0.1')}")
    print()
    
    # Connect to database
    try:
        conn = get_connection(config)
        cursor = conn.cursor()
        print("✓ Connected to database")
        print()
    except pymysql.Error as e:
        print(f"✗ Failed to connect to database: {e}")
        sys.exit(1)
    
    print("Executing refresh SQL...")
    print("-" * 70)
    
    try:
        # 1. ASIN+Marketplace table
        if refresh_asin:
            print("1/3: Refreshing ASIN+Marketplace monthly summary...")
            cursor.execute("TRUNCATE TABLE `financials_summary_monthly_asin_marketplace`")
            conn.commit()
            
            cursor.execute("""
                INSERT INTO `financials_summary_monthly_asin_marketplace` 
                    (asin_id, brand_id, category_id, marketplace, month, metric, value)
                SELECT 
                    f.asin_id,
                    a.brand_id,
                    b.category_id,
                    f.marketplace,
                    f.month,
                    f.metric,
                    SUM(f.value) as total_value
                FROM financials f
                INNER JOIN asin a ON f.asin_id = a.id
                INNER JOIN brand b ON a.brand_id = b.id
                WHERE (b.`group` IS NULL OR b.`group` != 'stock')
                GROUP BY 
                    f.asin_id,
                    a.brand_id,
                    b.category_id,
                    f.marketplace,
                    f.month,
                    f.metric
            """)
            conn.commit()
            print(f"   ✓ Inserted {cursor.rowcount:,} rows into asin+marketplace summary")
        else:
            print("1/3: Skipping ASIN+Marketplace table (already populated)")
        
        # 2. Brand table
        if refresh_brand:
            print("2/3: Refreshing Brand monthly summary...")
            cursor.execute("TRUNCATE TABLE `financials_summary_monthly_brand`")
            conn.commit()
            
            # By-marketplace aggregates
            cursor.execute("""
                INSERT INTO `financials_summary_monthly_brand` 
                    (brand_id, category_id, month, marketplace, metric, total_value, asin_count)
                SELECT 
                    brand_id,
                    category_id,
                    month,
                    marketplace,
                    metric,
                    SUM(value) as total_value,
                    COUNT(DISTINCT asin_id) as asin_count
                FROM financials_summary_monthly_asin_marketplace
                GROUP BY 
                    brand_id,
                    category_id,
                    month,
                    marketplace,
                    metric
            """)
            conn.commit()
            by_marketplace_count = cursor.rowcount
            print(f"   ✓ Inserted {by_marketplace_count:,} by-marketplace rows")
            
            # ALL marketplace aggregates
            cursor.execute("""
                INSERT INTO `financials_summary_monthly_brand` 
                    (brand_id, category_id, month, marketplace, metric, total_value, asin_count)
                SELECT 
                    brand_id,
                    category_id,
                    month,
                    'ALL' as marketplace,
                    metric,
                    SUM(value) as total_value,
                    COUNT(DISTINCT asin_id) as asin_count
                FROM financials_summary_monthly_asin_marketplace
                GROUP BY 
                    brand_id,
                    category_id,
                    month,
                    metric
            """)
            conn.commit()
            all_marketplace_count = cursor.rowcount
            print(f"   ✓ Inserted {all_marketplace_count:,} ALL-marketplace rows")
        else:
            print("2/3: Skipping Brand table")
        
        # 3. Category table
        if refresh_category:
            print("3/3: Refreshing Category monthly summary...")
            cursor.execute("TRUNCATE TABLE `financials_summary_monthly_category`")
            conn.commit()
            
            cursor.execute("""
                INSERT INTO `financials_summary_monthly_category` 
                    (category_id, month, metric, total_value, brand_count, asin_count)
                SELECT 
                    category_id,
                    month,
                    metric,
                    SUM(total_value) as total_value,
                    COUNT(DISTINCT brand_id) as brand_count,
                    SUM(asin_count) as asin_count
                FROM financials_summary_monthly_brand
                WHERE marketplace = 'ALL'
                  AND category_id IS NOT NULL
                GROUP BY 
                    category_id,
                    month,
                    metric
            """)
            conn.commit()
            print(f"   ✓ Inserted {cursor.rowcount:,} rows into category summary")
        else:
            print("3/3: Skipping Category table")
        
    except pymysql.Error as e:
        print()
        print(f"✗ Failed to refresh summary tables: {e}")
        cursor.close()
        conn.close()
        sys.exit(1)
    
    cursor.close()
    conn.close()
    
    elapsed_time = time.time() - start_time
    
    print()
    print("-" * 70)
    print(f"✓ Summary tables refreshed successfully!")
    print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Total time: {elapsed_time:.2f} seconds ({elapsed_time/60:.2f} minutes)")
    print()
    print("Next steps:")
    print("  - Test the dashboard to verify performance improvements")
    print("  - Set up a daily cron job to run this script automatically")
    print("=" * 70)

if __name__ == '__main__':
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(
        description='Refresh dashboard summary tables',
        epilog='''
Examples:
  # Refresh all tables (default):
  python3 refresh_summaries.py
  
  # Skip ASIN table, only refresh Brand and Category:
  python3 refresh_summaries.py --skip-asin
  
  # Only refresh specific tables:
  python3 refresh_summaries.py --only-brand
  python3 refresh_summaries.py --only-category
  python3 refresh_summaries.py --only-brand --only-category
        ''',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('--config', help='Path to config.ini file', default=None)
    parser.add_argument('--skip-asin', action='store_true', 
                       help='Skip refreshing ASIN+Marketplace table (useful if already populated)')
    parser.add_argument('--skip-brand', action='store_true',
                       help='Skip refreshing Brand table')
    parser.add_argument('--skip-category', action='store_true',
                       help='Skip refreshing Category table')
    parser.add_argument('--only-asin', action='store_true',
                       help='Only refresh ASIN+Marketplace table')
    parser.add_argument('--only-brand', action='store_true',
                       help='Only refresh Brand table')
    parser.add_argument('--only-category', action='store_true',
                       help='Only refresh Category table')
    args = parser.parse_args()
    
    # Determine which tables to refresh
    if args.only_asin or args.only_brand or args.only_category:
        # If any "only" flag is set, only refresh those
        refresh_asin = args.only_asin
        refresh_brand = args.only_brand
        refresh_category = args.only_category
    else:
        # Otherwise, refresh all except those explicitly skipped
        refresh_asin = not args.skip_asin
        refresh_brand = not args.skip_brand
        refresh_category = not args.skip_category
    
    try:
        refresh_summary_tables(args.config, refresh_asin, refresh_brand, refresh_category)
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

