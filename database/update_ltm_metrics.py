#!/usr/bin/env python3
"""
Update LTM (Last Twelve Months) Metrics in ASIN Table
======================================================
This script updates the ltm_revenues, ltm_cm3, ltm_brand_ebitda, and stock_value
fields in the asin table based on data from Nov 2024 - Oct 2025.

Run this script:
  - After importing new financial data
  - Monthly to keep LTM metrics current
  - When you notice missing LTM values in the UI

Usage:
    python3 update_ltm_metrics.py
    
    # Or with custom config:
    python3 update_ltm_metrics.py --config ../custom_config.ini
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

def execute_sql_file(cursor, sql_file_path):
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
        except pymysql.Error as e:
            print(f"ERROR executing statement {i}: {e}")
            return False
    
    return True

def update_ltm_metrics(config_path=None):
    """Main function to update LTM metrics"""
    print("=" * 70)
    print("LTM Metrics Update")
    print("=" * 70)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
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
    
    # Execute the update SQL
    sql_file = os.path.join(os.path.dirname(__file__), 'update_ltm_metrics.sql')
    
    print("Executing LTM metrics update SQL...")
    print("-" * 70)
    
    success = execute_sql_file(cursor, sql_file)
    
    if not success:
        print()
        print("✗ Failed to update LTM metrics")
        cursor.close()
        conn.close()
        sys.exit(1)
    
    # Commit changes
    conn.commit()
    cursor.close()
    conn.close()
    
    elapsed_time = time.time() - start_time
    
    print()
    print("-" * 70)
    print(f"✓ LTM metrics updated successfully!")
    print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Total time: {elapsed_time:.2f} seconds ({elapsed_time/60:.2f} minutes)")
    print()
    print("Next steps:")
    print("  - Refresh the ASIN pages to see updated LTM values")
    print("  - Set up a monthly cron job to keep LTM metrics current")
    print("=" * 70)

if __name__ == '__main__':
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description='Update LTM metrics in ASIN table')
    parser.add_argument('--config', help='Path to config.ini file', default=None)
    args = parser.parse_args()
    
    try:
        update_ltm_metrics(args.config)
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

