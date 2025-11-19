#!/usr/bin/env python3
"""
Shared database utilities for the LEGO project
"""

import pymysql
import sys
import os
import configparser

def get_config():
    """Read configuration from config.ini"""
    config = configparser.ConfigParser()
    config_path = os.path.join(os.path.dirname(__file__), 'config.ini')
    config.read(config_path)
    return config

def get_db_params():
    """Get database parameters from config.ini with environment variable fallbacks"""
    config = get_config()
    return {
        'host': os.getenv('DB_HOST', config.get('database', 'host', fallback='127.0.0.1')),
        'port': int(os.getenv('DB_PORT', config.get('database', 'port', fallback='3306'))),
        'user': os.getenv('DB_USER', config.get('database', 'user', fallback='root')),
        'password': os.getenv('DB_PASSWORD', config.get('database', 'password', fallback='')),
        'database': os.getenv('DB_NAME', config.get('database', 'database', fallback='lego'))
    }

def create_connection():
    """Create database connection"""
    try:
        params = get_db_params()
        connection = pymysql.connect(
            host=params['host'],
            port=params['port'],
            user=params['user'],
            password=params['password'],
            database=params['database'],
            charset='utf8mb4',
            cursorclass=pymysql.cursors.Cursor
        )
        return connection
    except Exception as e:
        print(f"Error connecting to MySQL: {e}")
        return None

def create_database():
    """Create the lego database if it doesn't exist"""
    try:
        params = get_db_params()
        connection = pymysql.connect(
            host=params['host'],
            port=params['port'],
            user=params['user'],
            password=params['password'],
            charset='utf8mb4'
        )
        cursor = connection.cursor()
        cursor.execute("CREATE DATABASE IF NOT EXISTS lego")
        print("✓ Database 'lego' created or already exists")
        cursor.close()
        connection.close()
    except Exception as e:
        print(f"Error creating database: {e}")
        sys.exit(1)

def create_tables(connection):
    """Create all required tables"""
    cursor = connection.cursor()
    
    # Create category table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS category (
            id INT AUTO_INCREMENT PRIMARY KEY,
            category VARCHAR(255) UNIQUE,
            level_1 VARCHAR(255),
            level_2 VARCHAR(255),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print("✓ Table 'category' created")
    
    # Create brand table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS brand (
            id INT AUTO_INCREMENT PRIMARY KEY,
            brand VARCHAR(255) UNIQUE NOT NULL,
            category_id INT,
            url VARCHAR(512),
            acquisition VARCHAR(255),
            `group` VARCHAR(50),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (category_id) REFERENCES category(id)
        )
    """)
    print("✓ Table 'brand' created")
    
    # Create asin table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS asin (
            id INT AUTO_INCREMENT PRIMARY KEY,
            asin VARCHAR(50) UNIQUE NOT NULL,
            product_id VARCHAR(100),
            brand_id INT,
            status VARCHAR(50),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (brand_id) REFERENCES brand(id)
        )
    """)
    print("✓ Table 'asin' created")
    
    # Create financials table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS financials (
            id INT AUTO_INCREMENT PRIMARY KEY,
            asin_id INT NOT NULL,
            marketplace VARCHAR(10),
            metric VARCHAR(100),
            month DATE,
            value DECIMAL(15, 2),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (asin_id) REFERENCES asin(id),
            INDEX idx_asin_metric_month (asin_id, metric, month)
        )
    """)
    print("✓ Table 'financials' created")
    
    connection.commit()
    cursor.close()

def get_or_create_brand(cursor, brand_name, group=None):
    """Get brand_id or create new brand with optional group"""
    cursor.execute("SELECT id FROM brand WHERE brand = %s", (brand_name,))
    result = cursor.fetchone()
    if result:
        # If brand exists and group is provided, update the group
        if group:
            cursor.execute("UPDATE brand SET `group` = %s WHERE id = %s", (group, result[0]))
        return result[0]
    else:
        if group:
            cursor.execute("INSERT INTO brand (brand, `group`) VALUES (%s, %s)", (brand_name, group))
        else:
            cursor.execute("INSERT INTO brand (brand) VALUES (%s)", (brand_name,))
        return cursor.lastrowid

def get_or_create_asin(cursor, asin_value, product_id, brand_id, status):
    """Get asin_id or create new asin. Updates brand_id and status if ASIN already exists."""
    cursor.execute("SELECT id, brand_id, status FROM asin WHERE asin = %s", (asin_value,))
    result = cursor.fetchone()
    if result:
        asin_id = result[0]
        # Update brand_id and status if they've changed (and new values are provided)
        if brand_id and status:
            cursor.execute(
                "UPDATE asin SET brand_id = %s, status = %s WHERE id = %s",
                (brand_id, status, asin_id)
            )
        return asin_id
    else:
        cursor.execute(
            "INSERT INTO asin (asin, product_id, brand_id, status) VALUES (%s, %s, %s, %s)",
            (asin_value, product_id, brand_id, status)
        )
        return cursor.lastrowid

def flush_financials(connection):
    """Delete all financial data from the database"""
    cursor = connection.cursor()
    cursor.execute("DELETE FROM financials")
    deleted = cursor.rowcount
    connection.commit()
    cursor.close()
    return deleted

