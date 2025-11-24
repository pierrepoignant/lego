#!/usr/bin/env python3
"""
Script to create an initial admin user in the database.
Usage: python3 database/create_initial_admin.py [username] [password]
"""

import sys
import os
import pymysql
import configparser
from werkzeug.security import generate_password_hash

# Add parent directory to path to import db functions
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def get_config():
    """Read configuration from config.ini"""
    config = configparser.ConfigParser()
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config.ini')
    config.read(config_path)
    return config

def get_connection():
    """Create database connection"""
    config = get_config()
    
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

def create_admin_user(username, password, email=None):
    """Create an admin user"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Check if user already exists
        cursor.execute("SELECT id FROM users WHERE username = %s", [username])
        if cursor.fetchone():
            print(f"❌ User '{username}' already exists!")
            return False
        
        # Create user with explicit pbkdf2 method (compatible with all Python versions)
        password_hash = generate_password_hash(password, method='pbkdf2:sha256')
        cursor.execute("""
            INSERT INTO users (username, password_hash, email, is_admin, is_active)
            VALUES (%s, %s, %s, 1, 1)
        """, [username, password_hash, email])
        conn.commit()
        
        print(f"✅ Admin user '{username}' created successfully!")
        return True
    except Exception as e:
        print(f"❌ Error creating user: {str(e)}")
        return False
    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python3 create_initial_admin.py <username> <password> [email]")
        print("\nExample:")
        print("  python3 create_initial_admin.py admin mypassword admin@example.com")
        sys.exit(1)
    
    username = sys.argv[1]
    password = sys.argv[2]
    email = sys.argv[3] if len(sys.argv) > 3 else None
    
    if len(password) < 6:
        print("❌ Password must be at least 6 characters long")
        sys.exit(1)
    
    print(f"Creating admin user '{username}'...")
    success = create_admin_user(username, password, email)
    
    if success:
        print("\n✨ You can now log in with this user!")
    else:
        sys.exit(1)

