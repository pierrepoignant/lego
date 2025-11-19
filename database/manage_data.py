#!/usr/bin/env python3
"""
Command-line script to manage data in the LEGO database

Usage:
    python manage_data.py flush                  # Flush all financial data
    python manage_data.py import-infinite        # Import infinite.csv
    python manage_data.py import-razor           # Import razor.csv
    python manage_data.py flush import-infinite  # Flush then import infinite.csv
    python manage_data.py flush import-razor     # Flush then import razor.csv
"""

import sys
from db_utils import create_connection, flush_financials
from import_infinite import import_infinite_csv
from import_razor import import_razor_csv

def show_usage():
    """Display usage information"""
    print("""
LEGO Data Management Tool

Usage:
    python manage_data.py COMMAND [COMMAND ...]

Commands:
    flush              Flush all financial data from the database
    import-infinite    Import data from infinite.csv
    import-razor       Import data from razor.csv

Examples:
    python manage_data.py flush
    python manage_data.py import-infinite
    python manage_data.py import-razor
    python manage_data.py flush import-infinite
    python manage_data.py flush import-razor

Notes:
    - You can chain multiple commands together
    - Make sure database is initialized first: python init_database.py
    - Flushing only removes financial data, not brands or ASINs
""")

def cmd_flush(connection):
    """Flush all financial data"""
    print("\n" + "=" * 60)
    print("FLUSHING FINANCIAL DATA")
    print("=" * 60)
    deleted = flush_financials(connection)
    print(f"✓ Deleted {deleted} financial records")
    print("=" * 60)

def cmd_import_infinite(connection):
    """Import data from infinite.csv"""
    print("\n" + "=" * 60)
    print("IMPORTING DATA FROM INFINITE.CSV")
    print("=" * 60)
    try:
        row_count, financial_count = import_infinite_csv(connection)
        print("=" * 60)
        print(f"✓ Import completed: {row_count} products, {financial_count} financial records")
        print("=" * 60)
    except FileNotFoundError:
        print("✗ Error: infinite.csv not found")
        sys.exit(1)
    except Exception as e:
        print(f"✗ Error importing data: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

def cmd_import_razor(connection):
    """Import data from razor.csv"""
    print("\n" + "=" * 60)
    print("IMPORTING DATA FROM RAZOR.CSV")
    print("=" * 60)
    try:
        row_count, financial_count = import_razor_csv(connection)
        print("=" * 60)
        print(f"✓ Import completed: {row_count} products, {financial_count} financial records")
        print("=" * 60)
    except FileNotFoundError:
        print("✗ Error: razor.csv not found")
        sys.exit(1)
    except Exception as e:
        print(f"✗ Error importing data: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

def main():
    if len(sys.argv) < 2:
        show_usage()
        sys.exit(1)
    
    commands = sys.argv[1:]
    
    # Validate commands
    valid_commands = ['flush', 'import-infinite', 'import-razor']
    for cmd in commands:
        if cmd not in valid_commands:
            print(f"✗ Error: Unknown command '{cmd}'")
            show_usage()
            sys.exit(1)
    
    # Connect to database
    print("Connecting to database...")
    connection = create_connection()
    if not connection:
        print("✗ Error: Could not connect to database")
        print("  Make sure MySQL is running and the database is initialized.")
        print("  Run: python init_database.py")
        sys.exit(1)
    print("✓ Connected to database")
    
    # Execute commands in order
    for cmd in commands:
        if cmd == 'flush':
            cmd_flush(connection)
        elif cmd == 'import-infinite':
            cmd_import_infinite(connection)
        elif cmd == 'import-razor':
            cmd_import_razor(connection)
    
    # Show final summary
    print("\n" + "=" * 60)
    print("FINAL DATABASE SUMMARY")
    print("=" * 60)
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
    print("=" * 60)
    print("✓ All operations completed successfully!")
    print("=" * 60)

if __name__ == "__main__":
    main()


