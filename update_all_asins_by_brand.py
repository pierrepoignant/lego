#!/usr/bin/env python3
"""
Loop through all brands and update ASIN LTM metrics for each brand
"""

import pymysql
import os
import configparser
import subprocess
import sys

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

if __name__ == '__main__':
    print("=" * 80)
    print("Updating ASIN LTM Metrics for All Brands")
    print("=" * 80)
    print()
    
    conn = get_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    
    # Get all brands that have ASINs
    cursor.execute("""
        SELECT DISTINCT b.id, b.brand, COUNT(a.id) as asin_count
        FROM brand b
        INNER JOIN asin a ON a.brand_id = b.id
        WHERE (b.`group` IS NULL OR b.`group` != 'stock')
        GROUP BY b.id, b.brand
        ORDER BY b.id
    """)
    
    brands = cursor.fetchall()
    cursor.close()
    conn.close()
    
    if not brands:
        print("❌ No brands found with ASINs")
        sys.exit(1)
    
    print(f"Found {len(brands)} brands with ASINs\n")
    
    total_success = 0
    total_failed = 0
    
    for idx, brand in enumerate(brands, 1):
        brand_id = brand['id']
        brand_name = brand['brand']
        asin_count = brand['asin_count']
        
        print(f"\n[{idx}/{len(brands)}] Processing Brand: {brand_name} (ID: {brand_id}, {asin_count} ASINs)")
        print("-" * 80)
        
        # Run compute_ltm_metrics.py for this brand
        try:
            result = subprocess.run(
                ['python3', 'compute_ltm_metrics.py', '--asins-for-brand-id', str(brand_id)],
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout per brand
            )
            
            if result.returncode == 0:
                print(f"✅ Success for {brand_name}")
                total_success += 1
            else:
                print(f"❌ Failed for {brand_name}")
                print(f"Error: {result.stderr[:200]}")
                total_failed += 1
        except subprocess.TimeoutExpired:
            print(f"⏱️  Timeout for {brand_name} (took > 5 minutes)")
            total_failed += 1
        except Exception as e:
            print(f"❌ Error for {brand_name}: {str(e)}")
            total_failed += 1
    
    print("\n" + "=" * 80)
    print("All Brands Processed!")
    print("=" * 80)
    print(f"✅ Successful: {total_success} brands")
    print(f"❌ Failed: {total_failed} brands")
    print("=" * 80)

