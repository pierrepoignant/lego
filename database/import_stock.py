#!/usr/bin/env python3
"""
Module to import stock data from CSV files into the database
CSV format: product_id;location;quantity;cogs;value;asin;brand
"""

import csv
import sys
import argparse
from datetime import datetime
from db_utils import create_connection, get_or_create_brand

def clean_decimal(value_str):
    """Clean decimal value string (handles commas as decimal separators)"""
    if not value_str or value_str.strip() in ['', '-', ' - ', '   ']:
        return None
    # Replace comma with period for decimal separator, remove spaces
    cleaned = value_str.replace(',', '.').replace(' ', '')
    try:
        return float(cleaned)
    except:
        return None

def get_asin_id_by_product(cursor, product_id):
    """Look up asin_id by product field in asin table"""
    cursor.execute("SELECT id FROM asin WHERE product = %s", (product_id,))
    result = cursor.fetchone()
    return result[0] if result else None

def get_asin_id_by_asin(cursor, asin_value):
    """Look up asin_id by asin field in asin table"""
    cursor.execute("SELECT id FROM asin WHERE asin = %s", (asin_value,))
    result = cursor.fetchone()
    return result[0] if result else None

def get_or_create_location(cursor, location_name):
    """Get location_id or create new location"""
    cursor.execute("SELECT id FROM location WHERE name = %s", (location_name,))
    result = cursor.fetchone()
    if result:
        return result[0]
    else:
        cursor.execute("INSERT INTO location (name) VALUES (%s)", (location_name,))
        return cursor.lastrowid

def import_stock_csv(connection, csv_file, month=None):
    """
    Load stock data from CSV file into database
    
    Args:
        connection: Database connection
        csv_file: Path to CSV file
        month: Month for stock data (YYYY-MM-DD format). If None, uses current month
    """
    cursor = connection.cursor()
    
    # Use current month if not provided
    if month is None:
        month = datetime.now().date().replace(day=1)
    else:
        try:
            month = datetime.strptime(month, '%Y-%m-%d').date()
        except ValueError:
            print(f"Error: Invalid month format. Use YYYY-MM-DD (e.g., 2024-01-01)")
            return 0, 0, 0
    
    print(f"Importing stock data for month: {month}")
    
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.reader(f, delimiter=';')
        
        # Read header
        header = next(reader)
        print(f"CSV columns: {header}")
        
        # Process data rows
        row_count = 0
        matched_product = 0
        matched_asin = 0
        no_match = 0
        skipped = 0
        
        for row in reader:
            if not row or len(row) < 7:
                continue
            
            product_id = row[0].strip()
            location = row[1].strip()
            quantity_str = row[2].strip()
            cogs_str = row[3].strip()
            value_str = row[4].strip()
            asin = row[5].strip()
            brand = row[6].strip()
            
            # Skip if essential fields are missing
            if not product_id or not location:
                skipped += 1
                continue
            
            # Parse numeric values
            quantity = int(quantity_str) if quantity_str else 0
            cogs = clean_decimal(cogs_str)
            value = clean_decimal(value_str)
            
            # Look up asin_id
            asin_id = None
            
            # Try to match by product_id first
            if product_id:
                asin_id = get_asin_id_by_product(cursor, product_id)
                if asin_id:
                    matched_product += 1
            
            # If no match, try to match by asin
            if asin_id is None and asin:
                asin_id = get_asin_id_by_asin(cursor, asin)
                if asin_id:
                    matched_asin += 1
            
            # If still no match, count it
            if asin_id is None:
                no_match += 1
                # We'll still insert the record with NULL asin_id as per requirements
            
            # Get or create brand
            brand_id = None
            if brand:
                brand_id = get_or_create_brand(cursor, brand, group='stock')
            
            # Get or create location
            location_id = get_or_create_location(cursor, location)
            
            # Insert or update stock record
            if asin_id is not None:
                # Check if record already exists for this asin_id, location_id, and month
                cursor.execute(
                    """SELECT id FROM stock 
                       WHERE asin_id = %s AND location_id = %s AND month = %s""",
                    (asin_id, location_id, month)
                )
                existing = cursor.fetchone()
                
                if existing:
                    # Update existing record
                    cursor.execute(
                        """UPDATE stock 
                           SET product = %s, brand_id = %s, quantity = %s, 
                               cogs = %s, value = %s
                           WHERE id = %s""",
                        (product_id, brand_id, quantity, cogs, value, existing[0])
                    )
                else:
                    # Insert new record
                    cursor.execute(
                        """INSERT INTO stock 
                           (asin_id, product, brand_id, location_id, month, 
                            quantity, cogs, value)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                        (asin_id, product_id, brand_id, location_id, month, 
                         quantity, cogs, value)
                    )
            else:
                # No asin_id found, insert with NULL asin_id
                # For NULL asin_id, check by product + location + month
                cursor.execute(
                    """SELECT id FROM stock 
                       WHERE product = %s AND location_id = %s AND month = %s 
                       AND asin_id IS NULL""",
                    (product_id, location_id, month)
                )
                existing = cursor.fetchone()
                
                if existing:
                    # Update existing record
                    cursor.execute(
                        """UPDATE stock 
                           SET brand_id = %s, quantity = %s, cogs = %s, value = %s
                           WHERE id = %s""",
                        (brand_id, quantity, cogs, value, existing[0])
                    )
                else:
                    # Insert new record with NULL asin_id
                    cursor.execute(
                        """INSERT INTO stock 
                           (asin_id, product, brand_id, location_id, month, 
                            quantity, cogs, value)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                        (None, product_id, brand_id, location_id, month, 
                         quantity, cogs, value)
                    )
                print(f"  Warning: No ASIN match for product_id={product_id}, asin={asin} - inserted with NULL asin_id")
            
            row_count += 1
            if row_count % 100 == 0:
                connection.commit()
                print(f"  Processed {row_count} rows...")
        
        connection.commit()
        print(f"\n✓ Import complete:")
        print(f"  - Total records processed: {row_count}")
        print(f"  - Matched by product_id: {matched_product}")
        print(f"  - Matched by ASIN: {matched_asin}")
        print(f"  - No match (inserted with NULL asin_id): {no_match}")
        print(f"  - Skipped (missing data): {skipped}")
    
    cursor.close()
    return row_count, matched_product, matched_asin

def main():
    """Main entry point for command line usage"""
    parser = argparse.ArgumentParser(
        description='Import stock data from CSV file into the database',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s stock_1.csv
  %(prog)s stock_1.csv --month 2024-01-01
  %(prog)s /path/to/stock_data.csv --month 2024-11-01
        """
    )
    parser.add_argument('csv_file', help='Path to the CSV file to import')
    parser.add_argument('--month', '-m', 
                       help='Month for stock data in YYYY-MM-DD format (default: current month)',
                       default=None)
    
    args = parser.parse_args()
    
    # Create database connection
    connection = create_connection()
    if not connection:
        print("Failed to connect to database")
        sys.exit(1)
    
    try:
        # Import the CSV file
        import_stock_csv(connection, args.csv_file, args.month)
    except FileNotFoundError:
        print(f"Error: File '{args.csv_file}' not found")
        sys.exit(1)
    except Exception as e:
        print(f"Error during import: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        connection.close()

if __name__ == '__main__':
    main()

