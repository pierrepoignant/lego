#!/usr/bin/env python3
"""
Apply the top_asin migration to create top_asin_buckets and top_asins tables
"""

import pymysql
import configparser
import os
import sys

def get_config():
    """Read configuration from config.ini"""
    config = configparser.ConfigParser()
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.ini')
    config.read(config_path)
    return config

def get_connection():
    """Create database connection"""
    config = get_config()
    
    # Use production database config for migration
    host = os.getenv('DB_HOST', config.get('database', 'host', fallback='127.0.0.1'))
    port = int(os.getenv('DB_PORT', config.get('database', 'port', fallback='3306')))
    user = os.getenv('DB_USER', config.get('database', 'user', fallback='root'))
    password = os.getenv('DB_PASSWORD', config.get('database', 'password', fallback=''))
    database = os.getenv('DB_NAME', config.get('database', 'database', fallback='lego'))
    
    print(f"Connecting to: {host}:{port} as {user}")
    
    return pymysql.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        database=database,
        charset='utf8mb4'
    )

def apply_migration():
    """Apply the top_asin migration"""
    print("Connecting to database...")
    conn = get_connection()
    cursor = conn.cursor()
    
    # Read the SQL file
    sql_file = os.path.join(os.path.dirname(__file__), 'create_top_asin_tables.sql')
    
    print(f"Reading migration file: {sql_file}")
    with open(sql_file, 'r') as f:
        sql_script = f.read()
    
    # Split into individual statements and execute
    statements = [stmt.strip() for stmt in sql_script.split(';') if stmt.strip()]
    
    print(f"Executing {len(statements)} SQL statements...")
    for i, statement in enumerate(statements, 1):
        if statement:
            print(f"  [{i}/{len(statements)}] Executing statement...")
            cursor.execute(statement)
    
    conn.commit()
    cursor.close()
    conn.close()
    
    print("\n✅ Migration completed successfully!")
    print("\nCreated tables:")
    print("  - top_asin_buckets (id, name, description, color, created_at)")
    print("  - top_asins (id, asin_id, bucket_id, created_at)")

if __name__ == '__main__':
    try:
        apply_migration()
    except Exception as e:
        print(f"\n❌ Error applying migration: {str(e)}")
        sys.exit(1)

