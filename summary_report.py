#!/usr/bin/env python3
"""
Summary report of the LEGO database
"""

import pymysql

def main():
    try:
        connection = pymysql.connect(
            host='127.0.0.1',
            port=3306,
            user='root',
            password='',
            database='lego',
            charset='utf8mb4'
        )
        
        cursor = connection.cursor()
        
        print("=" * 70)
        print("LEGO DATABASE SUMMARY REPORT")
        print("=" * 70)
        
        # Overall counts
        print("\n📊 OVERALL STATISTICS:")
        cursor.execute("SELECT COUNT(*) FROM brand")
        print(f"  - Total Brands: {cursor.fetchone()[0]}")
        
        cursor.execute("SELECT COUNT(*) FROM asin")
        print(f"  - Total ASINs (Products): {cursor.fetchone()[0]}")
        
        cursor.execute("SELECT COUNT(*) FROM financials")
        print(f"  - Total Financial Records: {cursor.fetchone()[0]:,}")
        
        # ASIN status breakdown
        print("\n📦 ASIN STATUS BREAKDOWN:")
        cursor.execute("""
            SELECT status, COUNT(*) as count 
            FROM asin 
            GROUP BY status 
            ORDER BY count DESC
        """)
        for row in cursor.fetchall():
            print(f"  - {row[0]}: {row[1]}")
        
        # Top brands by product count
        print("\n🏢 TOP 10 BRANDS BY PRODUCT COUNT:")
        cursor.execute("""
            SELECT b.brand, COUNT(a.id) as product_count
            FROM brand b
            LEFT JOIN asin a ON b.id = a.brand_id
            GROUP BY b.id, b.brand
            ORDER BY product_count DESC
            LIMIT 10
        """)
        for i, row in enumerate(cursor.fetchall(), 1):
            print(f"  {i}. {row[0]}: {row[1]} products")
        
        # Marketplaces
        print("\n🌍 MARKETPLACES:")
        cursor.execute("""
            SELECT DISTINCT marketplace, COUNT(*) as records
            FROM financials
            GROUP BY marketplace
            ORDER BY records DESC
        """)
        for row in cursor.fetchall():
            print(f"  - {row[0]}: {row[1]:,} records")
        
        # Metrics available
        print("\n📈 FINANCIAL METRICS AVAILABLE:")
        cursor.execute("""
            SELECT DISTINCT metric
            FROM financials
            ORDER BY metric
        """)
        for row in cursor.fetchall():
            print(f"  - {row[0]}")
        
        # Date range
        print("\n📅 DATE RANGE:")
        cursor.execute("""
            SELECT MIN(month) as earliest, MAX(month) as latest
            FROM financials
        """)
        row = cursor.fetchone()
        print(f"  - From: {row[0]}")
        print(f"  - To: {row[1]}")
        
        # Sample financial data
        print("\n💰 SAMPLE FINANCIAL DATA (Latest Month):")
        cursor.execute("""
            SELECT a.product_id, b.brand, f.marketplace, f.metric, f.month, f.value
            FROM financials f
            JOIN asin a ON f.asin_id = a.id
            JOIN brand b ON a.brand_id = b.id
            WHERE f.month = (SELECT MAX(month) FROM financials)
            AND LOWER(f.metric) = 'net revenue'
            ORDER BY f.value DESC
            LIMIT 5
        """)
        print(f"  {'Product ID':<12} {'Brand':<20} {'MP':<4} {'Metric':<15} {'Month':<12} {'Value':>12}")
        print("  " + "-" * 85)
        for row in cursor.fetchall():
            print(f"  {row[0]:<12} {row[1]:<20} {row[2]:<4} {row[3]:<15} {str(row[4]):<12} ${row[5]:>11,.2f}")
        
        print("\n" + "=" * 70)
        print("✓ Database successfully created and loaded!")
        print("=" * 70)
        
        cursor.close()
        connection.close()
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

