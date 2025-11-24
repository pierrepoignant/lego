#!/usr/bin/env python3
"""
Script to populate main_image for brand and top_asin_buckets tables.
For each brand/top_asin_bucket, finds the ASIN with the biggest ltm_revenue 
and main_image not null, then copies that ASIN's main_image.
"""

import pymysql
import os
import configparser

def get_config():
    """Read configuration from config.ini"""
    config = configparser.ConfigParser()
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config.ini')
    config.read(config_path)
    return config

def get_connection():
    """Create database connection using config.ini with environment variable fallbacks"""
    config = get_config()
    
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

def populate_brand_main_images():
    """Populate main_image for all brands"""
    conn = get_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    
    # Get all brands
    cursor.execute("SELECT id, brand FROM brand")
    brands = cursor.fetchall()
    
    updated_count = 0
    
    for brand in brands:
        brand_id = brand['id']
        
        # Find ASIN with biggest ltm_revenue and main_image not null for this brand
        query = """
            SELECT main_image
            FROM asin
            WHERE brand_id = %s
            AND main_image IS NOT NULL
            AND main_image != ''
            ORDER BY ltm_revenues DESC
            LIMIT 1
        """
        
        cursor.execute(query, [brand_id])
        result = cursor.fetchone()
        
        if result and result['main_image']:
            # Update brand with this main_image
            update_query = "UPDATE brand SET main_image = %s WHERE id = %s"
            cursor.execute(update_query, [result['main_image'], brand_id])
            updated_count += 1
            print(f"Updated brand {brand['brand']} (ID: {brand_id}) with image: {result['main_image'][:50]}...")
    
    conn.commit()
    cursor.close()
    conn.close()
    
    print(f"\n✅ Updated {updated_count} brands with main_image")
    return updated_count

def populate_top_asin_bucket_main_images():
    """Populate main_image for all top_asin_buckets"""
    conn = get_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    
    # Get all top_asin_buckets
    cursor.execute("SELECT id, name FROM top_asin_buckets")
    buckets = cursor.fetchall()
    
    updated_count = 0
    
    for bucket in buckets:
        bucket_id = bucket['id']
        
        # Find ASIN with biggest ltm_revenue and main_image not null in this bucket
        query = """
            SELECT a.main_image
            FROM asin a
            INNER JOIN top_asins ta ON a.id = ta.asin_id
            WHERE ta.bucket_id = %s
            AND a.main_image IS NOT NULL
            AND a.main_image != ''
            ORDER BY a.ltm_revenues DESC
            LIMIT 1
        """
        
        cursor.execute(query, [bucket_id])
        result = cursor.fetchone()
        
        if result and result['main_image']:
            # Update top_asin_bucket with this main_image
            update_query = "UPDATE top_asin_buckets SET main_image = %s WHERE id = %s"
            cursor.execute(update_query, [result['main_image'], bucket_id])
            updated_count += 1
            print(f"Updated top_asin_bucket {bucket['name']} (ID: {bucket_id}) with image: {result['main_image'][:50]}...")
    
    conn.commit()
    cursor.close()
    conn.close()
    
    print(f"\n✅ Updated {updated_count} top_asin_buckets with main_image")
    return updated_count

if __name__ == '__main__':
    print("🚀 Starting main_image population...")
    print("\n📦 Populating brand main_images...")
    brand_count = populate_brand_main_images()
    
    print("\n📦 Populating top_asin_buckets main_images...")
    bucket_count = populate_top_asin_bucket_main_images()
    
    print(f"\n✨ Done! Updated {brand_count} brands and {bucket_count} top_asin_buckets")

