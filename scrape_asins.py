#!/usr/bin/env python3
"""
Script to scrape ASINs that haven't been scraped yet, in order of revenue (descending)
"""

import pymysql
import requests
import configparser
import json
import re
import os
import time
import sys
import argparse

def get_db_connection():
    """Create database connection using config.ini"""
    config = configparser.ConfigParser()
    config_path = os.path.join(os.path.dirname(__file__), 'config.ini')
    config.read(config_path)
    
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

def get_pangolin_api_key():
    """Read Pangolin API key from config.ini"""
    config = configparser.ConfigParser()
    config_path = os.path.join(os.path.dirname(__file__), 'config.ini')
    config.read(config_path)
    return config.get('pangolin', 'api_key', fallback=None)

def get_unscraped_asins():
    """Get ASINs that haven't been scraped, ordered by LTM revenue (descending)"""
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    
    # Use ltm_revenues from the asin table (computed by compute_ltm_metrics.py)
    query = """
        SELECT 
            a.id,
            a.asin,
            a.brand_id,
            COALESCE(a.ltm_revenues, 0) as ltm_revenue
        FROM asin a
        WHERE a.scraped_at IS NULL
        ORDER BY a.ltm_revenues DESC, a.asin
    """
    
    cursor.execute(query)
    asins = cursor.fetchall()
    cursor.close()
    conn.close()
    return asins

def get_scraped_asins_missing_brand():
    """Get ASINs that have been scraped but brand_scrapped is null"""
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    
    query = """
        SELECT 
            a.id,
            a.asin,
            a.parse_json
        FROM asin a
        WHERE a.scraped_at IS NOT NULL 
        AND a.brand_scrapped IS NULL
        AND a.parse_json IS NOT NULL
        ORDER BY a.asin
    """
    
    cursor.execute(query)
    asins = cursor.fetchall()
    cursor.close()
    conn.close()
    return asins

def get_or_create_brand_scrapped(brand_name, brand_id=None):
    """
    Get or create a brand_scrapped entry for the given brand name.
    Returns the brand_scrapped.id
    """
    if not brand_name or brand_name.strip() == '':
        return None
    
    brand_name = brand_name.strip()
    
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    
    try:
        # Check if brand_scrapped already exists
        cursor.execute("SELECT id FROM brand_scrapped WHERE name = %s", [brand_name])
        existing = cursor.fetchone()
        
        if existing:
            brand_scrapped_id = existing['id']
        else:
            # Create new brand_scrapped entry
            cursor.execute("""
                INSERT INTO brand_scrapped (name, brand_id, created_at)
                VALUES (%s, %s, NOW())
            """, [brand_name, brand_id])
            brand_scrapped_id = cursor.lastrowid
            conn.commit()
            print(f"    → Created new brand_scrapped entry: {brand_name} (ID: {brand_scrapped_id})")
        
        cursor.close()
        conn.close()
        return brand_scrapped_id
        
    except Exception as e:
        print(f"  ✗ Error in get_or_create_brand_scrapped: {str(e)}")
        cursor.close()
        conn.close()
        return None

def complete_brand_from_json(asin_id, asin, parse_json_str):
    """Extract brand from parse_json and update brand_scrapped field"""
    try:
        # Parse the JSON
        data = json.loads(parse_json_str)
        
        # Navigate the nested structure to extract brand
        brand_name = None
        if data.get('code') == 0 and data.get('data'):
            json_array = data.get('data', {}).get('json', [])
            if json_array and len(json_array) > 0:
                results = json_array[0].get('data', {}).get('results', [])
                if results and len(results) > 0:
                    product_data = results[0]
                    brand_name = product_data.get('brand')
        
        if brand_name:
            # Get or create brand_scrapped entry
            brand_scrapped_id = get_or_create_brand_scrapped(brand_name)
            
            if brand_scrapped_id:
                # Update the database
                conn = get_db_connection()
                cursor = conn.cursor()
                
                update_query = """
                    UPDATE asin 
                    SET brand_scrapped = %s,
                        brand_scrapped_id = %s
                    WHERE id = %s
                """
                
                cursor.execute(update_query, [brand_name, brand_scrapped_id, asin_id])
                conn.commit()
                cursor.close()
                conn.close()
                
                return brand_name
            else:
                return None
        else:
            return None
            
    except Exception as e:
        print(f"  ✗ Error parsing JSON: {str(e)}")
        return None

def safe_truncate(value, max_length):
    """Safely truncate a string value to max_length"""
    if value is None:
        return None
    str_value = str(value)
    if len(str_value) > max_length:
        return str_value[:max_length]
    return str_value

def scrape_and_save_asin(asin, api_key):
    """Scrape ASIN data from Pangolin and save to database"""
    
    # Pangolin API endpoint
    pangolin_url = 'https://scrapeapi.pangolinfo.com/api/v1/scrape'
    
    # Construct the Amazon product URL
    amazon_url = f'https://www.amazon.com/dp/{asin}'
    
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    
    payload = {
        'url': amazon_url,
        'parserName': 'amzProductDetail',
        'format': 'json',
        'bizContext': {
            'zipcode': '10041'
        }
    }
    
    try:
        print(f"  Calling Pangolin API...", end='', flush=True)
        response = requests.post(pangolin_url, json=payload, headers=headers, timeout=90)
        response.raise_for_status()
        
        data = response.json()
        print(" ✓")
        
        # Extract relevant fields from the response
        product_data = {}
        parent_asin = None
        
        # Navigate the nested structure
        if data.get('code') == 0 and data.get('data'):
            json_array = data.get('data', {}).get('json', [])
            if json_array and len(json_array) > 0:
                results = json_array[0].get('data', {}).get('results', [])
                if results and len(results) > 0:
                    product_data = results[0]
                    parent_asin = safe_truncate(product_data.get('parentAsin'), 50)
        
        # Update the database with scraped data
        conn = get_db_connection()
        cursor = conn.cursor()
        
        update_query = """
            UPDATE asin 
            SET 
                title = %s,
                price = %s,
                rating = %s,
                rating_count = %s,
                main_image = %s,
                sales_volume = %s,
                seller = %s,
                shipper = %s,
                merchant_id = %s,
                color = %s,
                size = %s,
                has_buy_box = %s,
                delivery_date = %s,
                coupon = %s,
                parse_json = %s,
                parent_asin = %s,
                amazon_category = %s,
                brand_scrapped = %s,
                scraped_at = NOW()
            WHERE asin = %s
        """
        
        # Extract values from the actual Pangolin API response structure
        title = safe_truncate(product_data.get('title'), 1000)
        
        price_str = product_data.get('price')
        price = None
        if price_str:
            price_match = re.search(r'\$?([\d,]+\.?\d*)', str(price_str))
            if price_match:
                try:
                    price = float(price_match.group(1).replace(',', ''))
                except:
                    pass
        
        # Extract rating (star field contains the rating)
        rating_str = product_data.get('star')
        rating = None
        if rating_str:
            try:
                rating = float(rating_str)
            except:
                pass
        
        # Extract rating count from 'rating' field
        rating_count_str = product_data.get('rating')
        rating_count = None
        if rating_count_str:
            try:
                rating_count = int(re.sub(r'[^\d]', '', str(rating_count_str)))
            except:
                pass
        
        # Extract sales volume from 'sales' field like "400+ bought"
        sales_str = product_data.get('sales')
        sales_volume = None
        if sales_str:
            try:
                sales_match = re.search(r'(\d+)', str(sales_str))
                if sales_match:
                    sales_volume = int(sales_match.group(1))
            except:
                pass
        
        main_image = product_data.get('image')
        seller = safe_truncate(product_data.get('seller'), 255)
        shipper = safe_truncate(product_data.get('shipper'), 255)
        merchant_id = safe_truncate(product_data.get('merchant_id'), 255)
        color = safe_truncate(product_data.get('color'), 100)
        size = None
        has_buy_box = 1 if product_data.get('has_cart') else 0
        delivery_date = safe_truncate(product_data.get('delivery_time'), 255)
        
        coupon = safe_truncate(product_data.get('coupon'), 255)
        if coupon == 'null':
            coupon = None
        
        # Extract amazon category from category_name field
        amazon_category = safe_truncate(product_data.get('category_name'), 255)
        
        # Extract brand from brand field
        brand_scrapped = safe_truncate(product_data.get('brand'), 255)
        
        # Store the entire response as JSON
        parse_json = json.dumps(data)
        
        cursor.execute(update_query, [
            title, price, rating, rating_count, main_image, sales_volume,
            seller, shipper, merchant_id, color, size, has_buy_box,
            delivery_date, coupon, parse_json, parent_asin, amazon_category, brand_scrapped, asin
        ])
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print(f"  ✓ Saved: {title[:50]}..." if title else "  ✓ Saved (no title)")
        return True
        
    except requests.exceptions.RequestException as e:
        print(f" ✗ API Error: {str(e)}")
        return False
    except Exception as e:
        print(f" ✗ Database Error: {str(e)}")
        return False

def complete_brands():
    """Complete brand_scrapped from parse_json for already scraped ASINs"""
    print("=" * 80)
    print("ASIN Scraper - Complete Brands from Existing JSON")
    print("=" * 80)
    
    # Get ASINs that have been scraped but missing brand_scrapped
    print("\nFetching ASINs with missing brand_scrapped...")
    asins = get_scraped_asins_missing_brand()
    
    if not asins:
        print("✓ No ASINs need brand completion. All scraped ASINs have brand_scrapped!")
        return
    
    print(f"✓ Found {len(asins)} ASINs with missing brand_scrapped")
    print("\nStarting brand completion process...")
    print("-" * 80)
    
    success_count = 0
    fail_count = 0
    
    for idx, asin_data in enumerate(asins, 1):
        asin = asin_data['asin']
        asin_id = asin_data['id']
        parse_json = asin_data['parse_json']
        
        print(f"\n[{idx}/{len(asins)}] ASIN: {asin}")
        
        brand = complete_brand_from_json(asin_id, asin, parse_json)
        if brand:
            print(f"  ✓ Brand extracted: {brand}")
            success_count += 1
        else:
            print(f"  ✗ No brand found in JSON")
            fail_count += 1
    
    # Summary
    print("\n" + "=" * 80)
    print("BRAND COMPLETION COMPLETE")
    print("=" * 80)
    print(f"Total ASINs processed: {len(asins)}")
    print(f"✓ Successful: {success_count}")
    print(f"✗ Failed: {fail_count}")
    print("=" * 80)

def main():
    """Main function to scrape all unscraped ASINs"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Scrape ASINs from Amazon via Pangolin API')
    parser.add_argument('--complete-brands', action='store_true', 
                       help='Complete brand_scrapped from parse_json for already scraped ASINs')
    args = parser.parse_args()
    
    # If --complete-brands flag is set, run brand completion instead
    if args.complete_brands:
        complete_brands()
        return
    
    print("=" * 80)
    print("ASIN Scraper - Scraping by Revenue Order")
    print("=" * 80)
    
    # Get API key
    api_key = get_pangolin_api_key()
    if not api_key:
        print("❌ Error: Pangolin API key not found in config.ini")
        sys.exit(1)
    
    print(f"✓ API key loaded")
    
    # Get unscraped ASINs
    print("\nFetching unscraped ASINs...")
    asins = get_unscraped_asins()
    
    if not asins:
        print("✓ No ASINs to scrape. All ASINs have been scraped!")
        return
    
    print(f"✓ Found {len(asins)} unscraped ASINs")
    print("\nStarting scraping process...")
    print("-" * 80)
    
    success_count = 0
    fail_count = 0
    
    for idx, asin_data in enumerate(asins, 1):
        asin = asin_data['asin']
        revenue = asin_data['ltm_revenue']
        
        print(f"\n[{idx}/{len(asins)}] ASIN: {asin} | LTM Revenue: ${revenue:,.2f}")
        
        if scrape_and_save_asin(asin, api_key):
            success_count += 1
        else:
            fail_count += 1
        
        # Rate limiting: wait 2 seconds between requests to avoid overwhelming the API
        if idx < len(asins):
            print("  Waiting 2 seconds before next request...")
            time.sleep(2)
    
    # Summary
    print("\n" + "=" * 80)
    print("SCRAPING COMPLETE")
    print("=" * 80)
    print(f"Total ASINs processed: {len(asins)}")
    print(f"✓ Successful: {success_count}")
    print(f"✗ Failed: {fail_count}")
    print("=" * 80)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Scraping interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {str(e)}")
        sys.exit(1)

