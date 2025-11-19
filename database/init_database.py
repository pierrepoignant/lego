#!/usr/bin/env python3
"""
Script to initialize MySQL database schema for LEGO project
This script only creates the database structure, it does not import data.
Use manage_data.py to import data.
"""

import sys
from db_utils import create_database, create_connection, create_tables

def main():
    print("=" * 60)
    print("LEGO Database Initialization")
    print("=" * 60)
    
    # Create database
    print("\n1. Creating database...")
    create_database()
    
    # Connect to database
    print("\n2. Connecting to database...")
    connection = create_connection()
    if not connection:
        sys.exit(1)
    
    print("✓ Connected to MySQL database")
    
    # Create tables
    print("\n3. Creating tables...")
    create_tables(connection)
    
    # Display summary
    print("\n4. Summary:")
    cursor = connection.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM brand")
    brand_count = cursor.fetchone()[0]
    print(f"  - Brands: {brand_count}")
    
    cursor.execute("SELECT COUNT(*) FROM asin")
    asin_count = cursor.fetchone()[0]
    print(f"  - ASINs: {asin_count}")
    
    cursor.execute("SELECT COUNT(*) FROM financials")
    financial_count = cursor.fetchone()[0]
    print(f"  - Financial records: {financial_count}")
    
    cursor.close()
    connection.close()
    
    print("\n" + "=" * 60)
    print("✓ Database initialization completed successfully!")
    print("=" * 60)
    print("\nNext steps:")
    print("  - To import data: python manage_data.py import-infinite")
    print("  - To import razor data: python manage_data.py import-razor")
    print("  - To flush financial data: python manage_data.py flush")

if __name__ == "__main__":
    main()


