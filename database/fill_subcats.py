#!/usr/bin/env python3
"""
Fill Sub-Categories Script
For all brands with empty sub_category, find the top ASIN by revenues
and populate sub_category with concatenated Amazon categories
"""

import pymysql
import configparser
import json
import sys
from decimal import Decimal

def get_db_connection():
    """Get database connection from config"""
    config = configparser.ConfigParser()
    config.read('/Users/pierrepoignant/Coding/lego/config.ini')
    
    return pymysql.connect(
        host=config['database']['host'],
        port=int(config['database']['port']),
        user=config['database']['user'],
        password=config['database']['password'],
        database=config['database']['database'],
        cursorclass=pymysql.cursors.DictCursor
    )

def extract_categories_from_json(parse_json_str):
    """
    Extract category hierarchy from parse_json field
    Returns a concatenated string like "Category1 / Category2 / Category3"
    """
    if not parse_json_str:
        return None
    
    try:
        data = json.loads(parse_json_str) if isinstance(parse_json_str, str) else parse_json_str
        
        # Try to find category information in the JSON structure
        # The structure is: data.json[0].data.results[0].category_name
        if 'data' in data and 'json' in data['data']:
            json_data = data['data']['json']
            if json_data and len(json_data) > 0:
                results = json_data[0].get('data', {}).get('results', [])
                if results and len(results) > 0:
                    # Get the category_name
                    category_name = results[0].get('category_name')
                    if category_name:
                        return category_name
        
        return None
    except Exception as e:
        print(f"    ⚠️  Error parsing JSON: {str(e)}")
        return None

def get_brands_without_subcategory(conn):
    """Get all brands that have empty sub_category"""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, brand 
        FROM brand 
        WHERE sub_category IS NULL OR sub_category = ''
        ORDER BY brand
    """)
    brands = cursor.fetchall()
    cursor.close()
    return brands

def get_top_asins_for_brand(conn, brand_id, limit=20):
    """
    Get top ASINs for a brand by LTM revenues
    Returns up to 'limit' ASINs with their categories
    """
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            a.id,
            a.asin,
            a.amazon_category,
            a.parse_json,
            a.ltm_revenues
        FROM asin a
        WHERE a.brand_id = %s
            AND a.ltm_revenues > 0
        ORDER BY a.ltm_revenues DESC
        LIMIT %s
    """, [brand_id, limit])
    asins = cursor.fetchall()
    cursor.close()
    return asins

def update_brand_subcategory(conn, brand_id, sub_category):
    """Update the sub_category for a brand"""
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE brand 
        SET sub_category = %s
        WHERE id = %s
    """, [sub_category, brand_id])
    conn.commit()
    cursor.close()

def main():
    print("=" * 80)
    print("Fill Sub-Categories Script")
    print("=" * 80)
    print()
    
    try:
        # Connect to database
        conn = get_db_connection()
        print("✓ Connected to database")
        print()
        
        # Get brands without sub_category
        brands = get_brands_without_subcategory(conn)
        print(f"Found {len(brands)} brands without sub_category")
        print()
        
        updated_count = 0
        skipped_count = 0
        
        for brand in brands:
            brand_id = brand['id']
            brand_name = brand['brand']
            
            print(f"Processing: {brand_name} (ID: {brand_id})")
            
            # Get top 20 ASINs by revenue
            top_asins = get_top_asins_for_brand(conn, brand_id, limit=20)
            
            if not top_asins:
                print(f"  ⚠️  No ASINs with revenue data found")
                skipped_count += 1
                print()
                continue
            
            # Collect unique categories from top 20 ASINs
            categories = []
            for asin in top_asins:
                # First try amazon_category field
                if asin['amazon_category']:
                    if asin['amazon_category'] not in categories:
                        categories.append(asin['amazon_category'])
                
                # Also try to extract from parse_json (even if we have 3, keep looking for better ones)
                if asin['parse_json']:
                    json_category = extract_categories_from_json(asin['parse_json'])
                    if json_category and json_category not in categories:
                        categories.append(json_category)
                
                # Stop if we have 5 distinct categories (we'll pick top 3)
                if len(categories) >= 5:
                    break
            
            if not categories:
                print(f"  ⚠️  No category data found in top ASINs")
                skipped_count += 1
                print()
                continue
            
            # Create sub_category string (top 3 categories)
            sub_category = " / ".join(categories[:3])
            
            print(f"  📁 Analyzed top {len(top_asins)} ASINs (Top ASIN: {top_asins[0]['asin']}, Revenue: ${top_asins[0]['ltm_revenues']:,.2f})")
            print(f"  📋 Sub-category: {sub_category}")
            
            # Update brand
            update_brand_subcategory(conn, brand_id, sub_category)
            updated_count += 1
            print(f"  ✓ Updated!")
            print()
        
        conn.close()
        
        print("=" * 80)
        print(f"✅ Complete!")
        print(f"   Updated: {updated_count} brands")
        print(f"   Skipped: {skipped_count} brands (no data)")
        print("=" * 80)
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()

