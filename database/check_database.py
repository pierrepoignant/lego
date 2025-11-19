#!/usr/bin/env python3
"""
Script to check the current state of the database
"""

import sys
import os
# Add parent directory to path to import db_utils
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db_utils import create_connection

def main():
    try:
        connection = create_connection()
        if not connection:
            print("Failed to connect to database")
            sys.exit(1)
        print("✓ Connected to MySQL database\n")
        
        cursor = connection.cursor()
        
        # Check tables
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()
        print(f"Tables in database: {[t[0] for t in tables]}\n")
        
        # Check counts
        for table in ['brand', 'asin', 'financials', 'category']:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                print(f"{table}: {count} records")
            except:
                print(f"{table}: table not found or error")
        
        # Sample some data
        print("\n--- Sample Brands ---")
        cursor.execute("SELECT * FROM brand LIMIT 5")
        for row in cursor.fetchall():
            print(row)
            
        print("\n--- Sample ASINs ---")
        cursor.execute("SELECT * FROM asin LIMIT 5")
        for row in cursor.fetchall():
            print(row)
        
        cursor.close()
        connection.close()
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()

