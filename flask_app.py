#!/usr/bin/env python3
"""
Flask app to edit LEGO database brand data
"""

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session, Response
from functools import wraps
import pymysql
import psycopg2
from psycopg2.extras import RealDictCursor
from decimal import Decimal
import os
import requests
import configparser
import csv
from io import StringIO
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from urllib.parse import unquote

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'your-secret-key-change-this-for-production')

def get_config():
    """Read configuration from config.ini"""
    config = configparser.ConfigParser()
    config_path = os.path.join(os.path.dirname(__file__), 'config.ini')
    config.read(config_path)
    return config

def get_auth_credentials():
    """Get authentication credentials from config.ini (legacy fallback)"""
    config = get_config()
    return {
        'username': config.get('auth', 'username', fallback='admin'),
        'password': config.get('auth', 'password', fallback='admin')
    }

def login_required(f):
    """Decorator to require login for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Decorator to require admin role for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login', next=request.url))
        if not session.get('is_admin'):
            flash('Admin access required', 'error')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

def verify_user(username, password):
    """Verify user credentials against database"""
    conn = get_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    
    try:
        cursor.execute("""
            SELECT id, username, password_hash, is_admin, is_active
            FROM users
            WHERE username = %s AND is_active = 1
        """, [username])
        user = cursor.fetchone()
        
        if user and check_password_hash(user['password_hash'], password):
            # Update last login
            cursor.execute("""
                UPDATE users SET last_login = NOW() WHERE id = %s
            """, [user['id']])
            conn.commit()
            return user
        return None
    finally:
        cursor.close()
        conn.close()

def create_user(username, password, email=None, is_admin=False):
    """Create a new user"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        password_hash = generate_password_hash(password, method='pbkdf2:sha256')
        cursor.execute("""
            INSERT INTO users (username, password_hash, email, is_admin)
            VALUES (%s, %s, %s, %s)
        """, [username, password_hash, email, is_admin])
        conn.commit()
        return cursor.lastrowid
    except pymysql.IntegrityError:
        return None
    finally:
        cursor.close()
        conn.close()

def get_pangolin_api_key():
    """Read Pangolin API key from config.ini"""
    config = get_config()
    return config.get('pangolin', 'api_key', fallback=None)

def get_postgres_connection():
    """Create PostgreSQL connection for search database"""
    config = get_config()
    
    # Read from config.ini [postgre] section
    host = os.getenv('POSTGRE_HOST', config.get('postgre', 'host', fallback='localhost'))
    port = int(os.getenv('POSTGRE_PORT', config.get('postgre', 'port', fallback='5432')))
    user = os.getenv('POSTGRE_USER', config.get('postgre', 'user', fallback='postgres'))
    password = os.getenv('POSTGRE_PASSWORD', config.get('postgre', 'password', fallback=''))
    database = os.getenv('POSTGRE_DATABASE', config.get('postgre', 'database', fallback='npd-search'))
    
    return psycopg2.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        database=database
    )

def get_connection():
    """Create database connection using config.ini with environment variable fallbacks"""
    config = get_config()
    
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

def get_categories():
    """Get list of all categories"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, category 
        FROM category 
        WHERE category IS NOT NULL 
        AND category != ''
        ORDER BY category
    """)
    categories = cursor.fetchall()
    cursor.close()
    conn.close()
    return categories

def get_brand_buckets():
    """Get list of all brand buckets"""
    conn = get_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    cursor.execute("""
        SELECT id, name, color, description
        FROM brand_buckets 
        ORDER BY name
    """)
    buckets = cursor.fetchall()
    cursor.close()
    conn.close()
    return buckets

def get_all_brands():
    """Get list of all brands ordered by LTM revenues (descending)"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, brand 
        FROM brand 
        WHERE (`group` IS NULL OR `group` != 'stock')
        ORDER BY 
            CASE WHEN ltm_revenues IS NULL THEN 1 ELSE 0 END,
            ltm_revenues DESC,
            brand
    """)
    brands = cursor.fetchall()
    cursor.close()
    conn.close()
    return brands

def get_all_marketplaces():
    """Get list of all marketplaces (OPTIMIZED - queries summary table or marketplace reference)"""
    conn = get_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    
    # Try to use marketplace reference table first (with nice country names)
    # Fall back to summary table if marketplace table doesn't exist
    try:
        cursor.execute("""
            SELECT m.code, m.country_name 
            FROM marketplace m
            INNER JOIN (
                SELECT DISTINCT marketplace 
                FROM financials_summary_monthly_brand 
                WHERE marketplace != 'ALL'
            ) s ON m.code = s.marketplace
            WHERE m.active = 1
            ORDER BY m.country_name
        """)
        marketplaces = cursor.fetchall()
        cursor.close()
        conn.close()
        return marketplaces
    except:
        # Fallback: just get codes from summary table
        cursor.execute("""
            SELECT DISTINCT marketplace 
            FROM financials_summary_monthly_brand 
            WHERE marketplace != 'ALL'
            ORDER BY marketplace
        """)
        marketplaces = [{'code': row['marketplace'], 'country_name': row['marketplace']} for row in cursor.fetchall()]
        cursor.close()
        conn.close()
        return marketplaces

def get_brands(category_id=None, brand_bucket_id=None, search_term=''):
    """Get list of brands ordered by LTM revenues (descending)"""
    conn = get_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    
    query = """
        SELECT 
            b.id,
            b.brand,
            b.url,
            b.main_image,
            c.category,
            b.category_id,
            b.position,
            b.sub_category,
            b.brand_bucket_id,
            bb.name as brand_bucket_name,
            bb.color as brand_bucket_color,
            b.ltm_revenues,
            b.ltm_cm3,
            b.ltm_brand_ebitda,
            b.ltm_units,
            b.stock_value,
            b.stock_units,
            b.stock_overstock_value,
            COUNT(a.id) as asin_count
        FROM brand b
        LEFT JOIN category c ON b.category_id = c.id
        LEFT JOIN brand_buckets bb ON b.brand_bucket_id = bb.id
        LEFT JOIN asin a ON a.brand_id = b.id
        WHERE (b.`group` IS NULL OR b.`group` != 'stock')
    """
    
    params = []
    
    # Handle special "null" value to filter for brands with no category
    if category_id == 'null':
        query += " AND b.category_id IS NULL"
    elif category_id:
        query += " AND b.category_id = %s"
        params.append(category_id)
    
    if brand_bucket_id:
        query += " AND b.brand_bucket_id = %s"
        params.append(brand_bucket_id)
    
    # Add search filter
    if search_term:
        query += " AND b.brand LIKE %s"
        params.append(f'%{search_term}%')
    
    query += """
        GROUP BY b.id, b.brand, b.url, b.main_image, c.category, b.category_id, b.position, 
                 b.sub_category, b.brand_bucket_id, bb.name, bb.color, 
                 b.ltm_revenues, b.ltm_cm3, b.ltm_brand_ebitda, b.ltm_units,
                 b.stock_value, b.stock_units, b.stock_overstock_value
        ORDER BY 
            CASE WHEN b.ltm_revenues IS NULL THEN 1 ELSE 0 END,
            b.ltm_revenues DESC,
            b.brand
    """
    
    cursor.execute(query, params)
    brands = cursor.fetchall()
    cursor.close()
    conn.close()
    return brands

def get_brand_by_id(brand_id):
    """Get a single brand by ID with all its fields"""
    conn = get_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    
    query = """
        SELECT 
            b.id,
            b.brand,
            b.url,
            b.category_id,
            c.category,
            b.`group`,
            b.sub_category,
            b.brand_bucket_id
        FROM brand b
        LEFT JOIN category c ON b.category_id = c.id
        WHERE b.id = %s
    """
    
    cursor.execute(query, [brand_id])
    brand = cursor.fetchone()
    cursor.close()
    conn.close()
    return brand

def update_brand(brand_id, brand_name, url, category_id, group, sub_category, brand_bucket_id=None):
    """Update a brand's information"""
    conn = get_connection()
    cursor = conn.cursor()
    
    query = """
        UPDATE brand 
        SET brand = %s, 
            url = %s, 
            category_id = %s,
            `group` = %s,
            sub_category = %s,
            brand_bucket_id = %s
        WHERE id = %s
    """
    
    # Handle empty values
    group_value = group if group and group.strip() else None
    category_value = category_id if category_id else None
    sub_category_value = sub_category if sub_category and sub_category.strip() else None
    brand_bucket_value = brand_bucket_id if brand_bucket_id else None
    
    cursor.execute(query, [brand_name, url, category_value, group_value, sub_category_value, brand_bucket_value, brand_id])
    conn.commit()
    cursor.close()
    conn.close()

def get_brand_asins(brand_id):
    """Get ASINs for a brand ordered by LTM revenues (descending)"""
    conn = get_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    
    query = """
        SELECT 
            id,
            asin,
            name,
            title,
            price,
            rating,
            rating_count,
            main_image,
            amazon_category,
            scraped_at,
            ltm_revenues,
            ltm_brand_ebitda,
            stock_value,
            ltm_updated_at
        FROM asin
        WHERE brand_id = %s
        ORDER BY ltm_revenues DESC, asin
    """
    
    cursor.execute(query, [brand_id])
    asins = cursor.fetchall()
    cursor.close()
    conn.close()
    return asins

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Try database authentication first
        user = verify_user(username, password)
        
        if user:
            session['logged_in'] = True
            session['username'] = user['username']
            session['user_id'] = user['id']
            session['is_admin'] = bool(user['is_admin'])
            flash('Successfully logged in!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('index'))
        
        # Fallback to config.ini for backward compatibility
        auth_creds = get_auth_credentials()
        if username == auth_creds['username'] and password == auth_creds['password']:
            session['logged_in'] = True
            session['username'] = username
            session['is_admin'] = True  # Legacy admin access
            flash('Successfully logged in!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('index'))
        
        flash('Invalid username or password', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    """Logout and clear session"""
    session.clear()
    flash('Successfully logged out', 'success')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    """Financial dashboard with Chart.js"""
    # Get filter options
    brands = get_all_brands()
    categories = get_categories()
    marketplaces = get_all_marketplaces()
    
    return render_template('dashboard.html', 
                         brands=brands,
                         categories=categories,
                         marketplaces=marketplaces)

@app.route('/profitability')
@login_required
def profitability():
    """Profitability analysis page"""
    # Get filter options
    brands = get_all_brands()
    categories = get_categories()
    
    return render_template('profitability.html', 
                         brands=brands,
                         categories=categories)

@app.route('/categories-dashboard')
@login_required
def categories_dashboard():
    """Categories dashboard page"""
    config = get_config()
    
    # Read EBITDA thresholds from config.ini
    ebitda_green = float(config.get('ebitda_thresholds', 'green', fallback='20'))
    ebitda_orange = float(config.get('ebitda_thresholds', 'orange', fallback='15'))
    
    return render_template('categories_dashboard.html',
                         ebitda_green=ebitda_green,
                         ebitda_orange=ebitda_orange)

@app.route('/top-asin-buckets-dashboard')
@login_required
def top_asin_buckets_dashboard():
    """Top ASIN Buckets dashboard page"""
    config = get_config()
    
    # Read EBITDA thresholds from config.ini
    ebitda_green = float(config.get('ebitda_thresholds', 'green', fallback='20'))
    ebitda_orange = float(config.get('ebitda_thresholds', 'orange', fallback='15'))
    
    return render_template('top_asin_buckets_dashboard.html',
                         ebitda_green=ebitda_green,
                         ebitda_orange=ebitda_orange)

@app.route('/forecast-dashboard')
@login_required
def forecast_dashboard():
    """Forecast dashboard page for Nov 2025 - Oct 2026"""
    # Get filter options
    brands = get_all_brands()
    categories = get_categories()
    
    return render_template('forecast_dashboard.html', brands=brands, categories=categories)

@app.route('/api/forecast-data')
@login_required
def get_forecast_data():
    """API endpoint to get forecast data (Nov 2025 - Oct 2026)"""
    metric = request.args.get('metric', 'Net revenue')
    brand_id = request.args.get('brand_id')
    category_id = request.args.get('category_id')
    
    conn = get_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    
    # Build query to get forecast data
    if brand_id:
        # Query specific brand forecast
        query = """
            SELECT 
                fb.month,
                MONTH(fb.month) as month_num,
                YEAR(fb.month) as year,
                fb.value
            FROM forecast_brand fb
            WHERE LOWER(fb.metric) = LOWER(%s)
            AND fb.brand_id = %s
            ORDER BY fb.month
        """
        cursor.execute(query, [metric, brand_id])
    elif category_id:
        # Aggregate brands by category
        query = """
            SELECT 
                fb.month,
                MONTH(fb.month) as month_num,
                YEAR(fb.month) as year,
                SUM(fb.value) as value
            FROM forecast_brand fb
            INNER JOIN brand b ON fb.brand_id = b.id
            WHERE LOWER(fb.metric) = LOWER(%s)
            AND b.category_id = %s
            GROUP BY fb.month, MONTH(fb.month), YEAR(fb.month)
            ORDER BY fb.month
        """
        cursor.execute(query, [metric, category_id])
    else:
        # Aggregate all brands
        query = """
            SELECT 
                fb.month,
                MONTH(fb.month) as month_num,
                YEAR(fb.month) as year,
                SUM(fb.value) as value
            FROM forecast_brand fb
            WHERE LOWER(fb.metric) = LOWER(%s)
            GROUP BY fb.month, MONTH(fb.month), YEAR(fb.month)
            ORDER BY fb.month
        """
        cursor.execute(query, [metric])
    
    results = cursor.fetchall()
    cursor.close()
    conn.close()
    
    # Process results
    months = []
    data = []
    
    month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    
    for row in results:
        month_num = row['month_num']
        year = row['year']
        value = float(row['value']) if row['value'] else 0
        
        # Format month label with year suffix
        year_suffix = str(year)[-2:]  # Get last 2 digits of year
        months.append(f"{month_names[month_num - 1]} '{year_suffix}")
        data.append(value)
    
    return jsonify({
        'metric': metric,
        'months': months,
        'data': data
    })

@app.route('/api/dashboard-data')
@login_required
def get_dashboard_data():
    """API endpoint to get dashboard data based on filters (OPTIMIZED with summary tables)"""
    metric = request.args.get('metric', 'Net revenue')
    brand_id = request.args.get('brand_id')
    category_id = request.args.get('category_id')
    marketplace = request.args.get('marketplace')
    
    conn = get_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    
    # Handle Brand EBITDA % metric (calculated from CM3 / Net revenue)
    if metric == 'Brand EBITDA %':
        # Query both Net revenue and CM3 to calculate EBITDA %
        query = """
            SELECT 
                s.metric,
                MONTH(s.month) as month_num,
                YEAR(s.month) as year,
                SUM(s.total_value) as total_value
            FROM financials_summary_monthly_brand s
            WHERE LOWER(s.metric) IN ('net revenue', 'cm3')
            AND YEAR(s.month) IN (2024, 2025)
        """
        
        params = []
        
        # Apply filters
        if brand_id:
            query += " AND s.brand_id = %s"
            params.append(brand_id)
        
        if category_id:
            query += " AND s.category_id = %s"
            params.append(category_id)
        
        if marketplace:
            query += " AND s.marketplace = %s"
            params.append(marketplace)
        else:
            # If no marketplace specified, use the 'ALL' aggregate
            query += " AND s.marketplace = 'ALL'"
        
        query += """
            GROUP BY s.metric, YEAR(s.month), MONTH(s.month)
            ORDER BY YEAR(s.month), MONTH(s.month)
        """
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        
        # Organize data by year, month, and metric
        revenue_2024 = [0] * 12
        revenue_2025 = [0] * 12
        cm3_2024 = [0] * 12
        cm3_2025 = [0] * 12
        
        for row in results:
            month_idx = row['month_num'] - 1
            metric_name = row['metric'].lower() if row['metric'] else ''
            value = float(row['total_value']) if row['total_value'] else 0
            
            if row['year'] == 2024:
                if metric_name == 'net revenue':
                    revenue_2024[month_idx] = value
                elif metric_name == 'cm3':
                    cm3_2024[month_idx] = value
            elif row['year'] == 2025:
                if metric_name == 'net revenue':
                    revenue_2025[month_idx] = value
                elif metric_name == 'cm3':
                    cm3_2025[month_idx] = value
        
        # Calculate EBITDA % = (CM3 / Revenue) * 100
        data_2024 = []
        data_2025 = []
        
        for i in range(12):
            # 2024 EBITDA %
            if revenue_2024[i] > 0:
                data_2024.append((cm3_2024[i] / revenue_2024[i]) * 100)
            else:
                data_2024.append(0)
            
            # 2025 EBITDA % (use None for future months)
            if i >= 10:  # Nov, Dec 2025 - future months
                data_2025.append(None)
            elif revenue_2025[i] > 0:
                data_2025.append((cm3_2025[i] / revenue_2025[i]) * 100)
            else:
                data_2025.append(0)
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'months': ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
            'data_2024': data_2024,
            'data_2025': data_2025,
            'metric': metric
        })
    
    # Handle regular metrics (Net revenue, CM3, Net units)
    else:
        # Use optimized summary table - much faster than joining 68M row financials table!
        # Query pre-aggregated data from financials_summary_monthly_brand
        # Use LOWER() for case-insensitive metric matching
        query = """
            SELECT 
                s.metric,
                MONTH(s.month) as month_num,
                YEAR(s.month) as year,
                SUM(s.total_value) as total_value
            FROM financials_summary_monthly_brand s
            WHERE LOWER(s.metric) = LOWER(%s)
            AND YEAR(s.month) IN (2024, 2025)
        """
        
        params = [metric]
        
        # Apply filters
        if brand_id:
            query += " AND s.brand_id = %s"
            params.append(brand_id)
        
        if category_id:
            query += " AND s.category_id = %s"
            params.append(category_id)
        
        if marketplace:
            query += " AND s.marketplace = %s"
            params.append(marketplace)
        else:
            # If no marketplace specified, use the 'ALL' aggregate
            query += " AND s.marketplace = 'ALL'"
        
        query += """
            GROUP BY s.metric, YEAR(s.month), MONTH(s.month)
            ORDER BY YEAR(s.month), MONTH(s.month)
        """
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        cursor.close()
        conn.close()
        
        # Organize data by year and month
        data_2024 = [0] * 12  # Initialize 12 months with 0
        data_2025 = [None] * 12  # Use None for 2025 to stop the line where data ends
        
        for row in results:
            month_idx = row['month_num'] - 1  # Convert to 0-based index
            if row['year'] == 2024:
                data_2024[month_idx] = float(row['total_value'])
            elif row['year'] == 2025:
                data_2025[month_idx] = float(row['total_value']) if row['total_value'] else 0
        
        return jsonify({
            'months': ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
            'data_2024': data_2024,
            'data_2025': data_2025,
            'metric': metric
        })

@app.route('/api/categories-dashboard-data')
@login_required
def get_categories_dashboard_data():
    """API endpoint to get all categories with their metrics (OPTIMIZED with summary tables)"""
    conn = get_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    
    # Use optimized summary table - queries category aggregates directly!
    query = """
        SELECT 
            c.id,
            c.category,
            -- Revenue 2024
            COALESCE(SUM(CASE 
                WHEN LOWER(s.metric) = 'net revenue'
                AND YEAR(s.month) = 2024 
                THEN s.total_value 
                ELSE 0 
            END), 0) as revenue_2024,
            -- Revenue LTM (Nov 2024 - Oct 2025)
            COALESCE(SUM(CASE 
                WHEN LOWER(s.metric) = 'net revenue'
                AND (
                    (YEAR(s.month) = 2024 AND MONTH(s.month) >= 11) OR
                    (YEAR(s.month) = 2025 AND MONTH(s.month) <= 10)
                )
                THEN s.total_value 
                ELSE 0 
            END), 0) as revenue_ltm,
            -- CM3 2024
            COALESCE(SUM(CASE 
                WHEN LOWER(s.metric) = 'cm3'
                AND YEAR(s.month) = 2024 
                THEN s.total_value 
                ELSE 0 
            END), 0) as cm3_2024,
            -- CM3 LTM (Nov 2024 - Oct 2025)
            COALESCE(SUM(CASE 
                WHEN LOWER(s.metric) = 'cm3'
                AND (
                    (YEAR(s.month) = 2024 AND MONTH(s.month) >= 11) OR
                    (YEAR(s.month) = 2025 AND MONTH(s.month) <= 10)
                )
                THEN s.total_value 
                ELSE 0 
            END), 0) as cm3_ltm
        FROM category c
        LEFT JOIN financials_summary_monthly_category s ON c.id = s.category_id
        GROUP BY c.id, c.category
        ORDER BY revenue_ltm DESC
    """
    
    cursor.execute(query)
    results = cursor.fetchall()
    
    # Get stock data for each category
    stock_query = """
        SELECT 
            b.category_id,
            SUM(st.value) as total_stock
        FROM stock st
        INNER JOIN asin a ON st.asin_id = a.id
        INNER JOIN brand b ON a.brand_id = b.id
        WHERE b.category_id IS NOT NULL
        AND (
            (YEAR(st.month) = 2024 AND MONTH(st.month) >= 11) OR
            (YEAR(st.month) = 2025 AND MONTH(st.month) <= 10)
        )
        GROUP BY b.category_id
    """
    
    cursor.execute(stock_query)
    stock_results = cursor.fetchall()
    
    # Create a dictionary for stock values by category_id
    stock_by_category = {row['category_id']: float(row['total_stock']) for row in stock_results}
    
    cursor.close()
    conn.close()
    
    # Process results
    categories_data = []
    for row in results:
        revenue_2024 = float(row['revenue_2024'])
        revenue_ltm = float(row['revenue_ltm'])
        cm3_2024 = float(row['cm3_2024'])
        cm3_ltm = float(row['cm3_ltm'])
        stock_ltm = stock_by_category.get(row['id'], 0)
        
        yoy_growth = ((revenue_ltm - revenue_2024) / revenue_2024 * 100) if revenue_2024 > 0 else 0
        ebitda_2024 = (cm3_2024 / revenue_2024 * 100) if revenue_2024 > 0 else 0
        ebitda_ltm = (cm3_ltm / revenue_ltm * 100) if revenue_ltm > 0 else 0
        
        categories_data.append({
            'id': row['id'],
            'category': row['category'],
            'revenue_2024': revenue_2024,
            'revenue_ltm': revenue_ltm,
            'yoy_growth': yoy_growth,
            'ebitda_2024': ebitda_2024,
            'ebitda_ltm': ebitda_ltm,
            'stock_ltm': stock_ltm
        })
    
    return jsonify({
        'categories': categories_data
    })

@app.route('/api/top-asin-buckets-dashboard-data')
@login_required
def get_top_asin_buckets_dashboard_data():
    """API endpoint to get dashboard data with Good Brands, Category Managed Brands, and Top ASIN Buckets"""
    bucket_type = request.args.get('bucket', None)
    conn = get_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    
    def get_brand_metrics_by_bucket(bucket_name):
        """Get metrics for brands in a specific brand bucket"""
        query = """
            SELECT 
                b.id,
                b.brand,
                -- Revenue 2024 (excluding EOL)
                COALESCE(SUM(CASE 
                    WHEN LOWER(s.metric) = 'net revenue'
                    AND YEAR(s.month) = 2024 
                    AND (a.eol IS NULL OR a.eol = 0)
                    THEN s.value 
                    ELSE 0 
                END), 0) as revenue_2024,
                -- Revenue LTM (Nov 2024 - Oct 2025, excluding EOL)
                COALESCE(SUM(CASE 
                    WHEN LOWER(s.metric) = 'net revenue'
                    AND (
                        (YEAR(s.month) = 2024 AND MONTH(s.month) >= 11) OR
                        (YEAR(s.month) = 2025 AND MONTH(s.month) <= 10)
                    )
                    AND (a.eol IS NULL OR a.eol = 0)
                    THEN s.value 
                    ELSE 0 
                END), 0) as revenue_ltm,
                -- CM3 2024
                COALESCE(SUM(CASE 
                    WHEN LOWER(s.metric) = 'cm3'
                    AND YEAR(s.month) = 2024 
                    THEN s.value 
                    ELSE 0 
                END), 0) as cm3_2024,
                -- CM3 LTM (Nov 2024 - Oct 2025)
                COALESCE(SUM(CASE 
                    WHEN LOWER(s.metric) = 'cm3'
                    AND (
                        (YEAR(s.month) = 2024 AND MONTH(s.month) >= 11) OR
                        (YEAR(s.month) = 2025 AND MONTH(s.month) <= 10)
                    )
                    THEN s.value 
                    ELSE 0 
                END), 0) as cm3_ltm
            FROM brand b
            INNER JOIN brand_buckets bb ON b.brand_bucket_id = bb.id
            LEFT JOIN asin a ON a.brand_id = b.id
            LEFT JOIN financials_summary_monthly_asin_marketplace s ON a.id = s.asin_id
            WHERE bb.name = %s
            AND (b.`group` IS NULL OR b.`group` != 'stock')
            GROUP BY b.id, b.brand
            ORDER BY revenue_ltm DESC
        """
        cursor.execute(query, [bucket_name])
        return cursor.fetchall()
    
    def get_forecast_for_brands(brand_ids):
        """Get forecast (next 12 months: Nov 2025 - Oct 2026) for a list of brand IDs"""
        if not brand_ids:
            return {}
        placeholders = ','.join(['%s'] * len(brand_ids))
        forecast_query = f"""
            SELECT 
                fb.brand_id,
                SUM(fb.value) as total_forecast
            FROM forecast_brand fb
            WHERE fb.brand_id IN ({placeholders})
            AND LOWER(fb.metric) = 'net revenue'
            AND fb.month >= '2025-11-01'
            AND fb.month <= '2026-10-31'
            GROUP BY fb.brand_id
        """
        cursor.execute(forecast_query, brand_ids)
        forecast_results = cursor.fetchall()
        return {row['brand_id']: float(row['total_forecast']) for row in forecast_results}
    
    def get_stock_for_brands(brand_ids):
        """Get stock LTM for a list of brand IDs"""
        if not brand_ids:
            return {}
        placeholders = ','.join(['%s'] * len(brand_ids))
        stock_query = f"""
            SELECT 
                a.brand_id,
                SUM(st.value) as total_stock
            FROM stock st
            INNER JOIN asin a ON st.asin_id = a.id
            WHERE a.brand_id IN ({placeholders})
            AND (
                (YEAR(st.month) = 2024 AND MONTH(st.month) >= 11) OR
                (YEAR(st.month) = 2025 AND MONTH(st.month) <= 10)
            )
            GROUP BY a.brand_id
        """
        cursor.execute(stock_query, brand_ids)
        stock_results = cursor.fetchall()
        return {row['brand_id']: float(row['total_stock']) for row in stock_results}
    
    # Get Good Brands data (only if requested or if no bucket specified)
    good_brands_data = []
    if bucket_type is None or bucket_type == 'good_brands':
        good_brands_results = get_brand_metrics_by_bucket('Good Brands')
        good_brand_ids = [row['id'] for row in good_brands_results]
        good_brands_stock = get_stock_for_brands(good_brand_ids)
        good_brands_forecast = get_forecast_for_brands(good_brand_ids)
        
        for row in good_brands_results:
            revenue_2024 = float(row['revenue_2024'])
            revenue_ltm = float(row['revenue_ltm'])
            cm3_2024 = float(row['cm3_2024'])
            cm3_ltm = float(row['cm3_ltm'])
            stock_ltm = good_brands_stock.get(row['id'], 0)
            forecast = good_brands_forecast.get(row['id'], 0)
            
            yoy_growth = ((revenue_ltm - revenue_2024) / revenue_2024 * 100) if revenue_2024 > 0 else 0
            ebitda_2024 = (cm3_2024 / revenue_2024 * 100) if revenue_2024 > 0 else 0
            ebitda_ltm = (cm3_ltm / revenue_ltm * 100) if revenue_ltm > 0 else 0
            
            good_brands_data.append({
                'id': row['id'],
                'name': row['brand'],
                'revenue_2024': revenue_2024,
                'revenue_ltm': revenue_ltm,
                'cm3_2024': cm3_2024,
                'cm3_ltm': cm3_ltm,
                'yoy_growth': yoy_growth,
                'ebitda_2024': ebitda_2024,
                'ebitda_ltm': ebitda_ltm,
                'stock_ltm': stock_ltm,
                'forecast': forecast
            })
    
    # Get Category Managed Brands data (only if requested or if no bucket specified)
    category_managed_data = []
    if bucket_type is None or bucket_type == 'category_managed_brands':
        category_managed_results = get_brand_metrics_by_bucket('Category Managed Brands')
        category_managed_ids = [row['id'] for row in category_managed_results]
        category_managed_stock = get_stock_for_brands(category_managed_ids)
        category_managed_forecast = get_forecast_for_brands(category_managed_ids)
        
        for row in category_managed_results:
            revenue_2024 = float(row['revenue_2024'])
            revenue_ltm = float(row['revenue_ltm'])
            cm3_2024 = float(row['cm3_2024'])
            cm3_ltm = float(row['cm3_ltm'])
            stock_ltm = category_managed_stock.get(row['id'], 0)
            forecast = category_managed_forecast.get(row['id'], 0)
            
            yoy_growth = ((revenue_ltm - revenue_2024) / revenue_2024 * 100) if revenue_2024 > 0 else 0
            ebitda_2024 = (cm3_2024 / revenue_2024 * 100) if revenue_2024 > 0 else 0
            ebitda_ltm = (cm3_ltm / revenue_ltm * 100) if revenue_ltm > 0 else 0
            
            category_managed_data.append({
                'id': row['id'],
                'name': row['brand'],
                'revenue_2024': revenue_2024,
                'revenue_ltm': revenue_ltm,
                'cm3_2024': cm3_2024,
                'cm3_ltm': cm3_ltm,
                'yoy_growth': yoy_growth,
                'ebitda_2024': ebitda_2024,
                'ebitda_ltm': ebitda_ltm,
                'stock_ltm': stock_ltm,
                'forecast': forecast
            })
    
    # Get Top ASIN Buckets data (existing logic)
    top_asin_buckets_data = []
    if bucket_type is None or bucket_type == 'top_asin_buckets':
        query = """
            SELECT 
                tab.id,
                tab.name as bucket_name,
                -- Revenue 2024 (excluding EOL)
                COALESCE(SUM(CASE 
                    WHEN LOWER(s.metric) = 'net revenue'
                    AND YEAR(s.month) = 2024 
                    AND (a.eol IS NULL OR a.eol = 0)
                    THEN s.value 
                    ELSE 0 
                END), 0) as revenue_2024,
                -- Revenue LTM (Nov 2024 - Oct 2025, excluding EOL)
                COALESCE(SUM(CASE 
                    WHEN LOWER(s.metric) = 'net revenue'
                    AND (
                        (YEAR(s.month) = 2024 AND MONTH(s.month) >= 11) OR
                        (YEAR(s.month) = 2025 AND MONTH(s.month) <= 10)
                    )
                    AND (a.eol IS NULL OR a.eol = 0)
                    THEN s.value 
                    ELSE 0 
                END), 0) as revenue_ltm,
                -- CM3 2024
                COALESCE(SUM(CASE 
                    WHEN LOWER(s.metric) = 'cm3'
                    AND YEAR(s.month) = 2024 
                    THEN s.value 
                    ELSE 0 
                END), 0) as cm3_2024,
                -- CM3 LTM (Nov 2024 - Oct 2025)
                COALESCE(SUM(CASE 
                    WHEN LOWER(s.metric) = 'cm3'
                    AND (
                        (YEAR(s.month) = 2024 AND MONTH(s.month) >= 11) OR
                        (YEAR(s.month) = 2025 AND MONTH(s.month) <= 10)
                    )
                    THEN s.value 
                    ELSE 0 
                END), 0) as cm3_ltm
            FROM top_asin_buckets tab
            LEFT JOIN top_asins ta ON tab.id = ta.bucket_id
            LEFT JOIN asin a ON ta.asin_id = a.id
            LEFT JOIN financials_summary_monthly_asin_marketplace s ON ta.asin_id = s.asin_id
            GROUP BY tab.id, tab.name
            ORDER BY revenue_ltm DESC
        """
        
        cursor.execute(query)
        results = cursor.fetchall()
        
        # Get stock data for each top ASIN bucket
        stock_query = """
            SELECT 
                ta.bucket_id,
                SUM(st.value) as total_stock
            FROM stock st
            INNER JOIN asin a ON st.asin_id = a.id
            INNER JOIN top_asins ta ON a.id = ta.asin_id
            WHERE (
                (YEAR(st.month) = 2024 AND MONTH(st.month) >= 11) OR
                (YEAR(st.month) = 2025 AND MONTH(st.month) <= 10)
            )
            GROUP BY ta.bucket_id
        """
        
        cursor.execute(stock_query)
        stock_results = cursor.fetchall()
        
        # Create a dictionary for stock values by bucket_id
        stock_by_bucket = {row['bucket_id']: float(row['total_stock']) for row in stock_results}
        
        # Get forecast for top ASIN buckets (sum of all ASINs in each bucket)
        bucket_ids = [row['id'] for row in results]
        bucket_forecasts = {}
        if bucket_ids:
            placeholders = ','.join(['%s'] * len(bucket_ids))
            forecast_query = f"""
                SELECT 
                    ta.bucket_id,
                    SUM(fa.value) as total_forecast
                FROM forecast_asin fa
                INNER JOIN top_asins ta ON fa.asin_id = ta.asin_id
                WHERE ta.bucket_id IN ({placeholders})
                AND LOWER(fa.metric) = 'net revenue'
                AND fa.month >= '2025-11-01'
                AND fa.month <= '2026-10-31'
                GROUP BY ta.bucket_id
            """
            cursor.execute(forecast_query, bucket_ids)
            forecast_results = cursor.fetchall()
            bucket_forecasts = {row['bucket_id']: float(row['total_forecast']) for row in forecast_results}
        
        for row in results:
            revenue_2024 = float(row['revenue_2024'])
            revenue_ltm = float(row['revenue_ltm'])
            cm3_2024 = float(row['cm3_2024'])
            cm3_ltm = float(row['cm3_ltm'])
            stock_ltm = stock_by_bucket.get(row['id'], 0)
            forecast = bucket_forecasts.get(row['id'], 0)
            
            yoy_growth = ((revenue_ltm - revenue_2024) / revenue_2024 * 100) if revenue_2024 > 0 else 0
            ebitda_2024 = (cm3_2024 / revenue_2024 * 100) if revenue_2024 > 0 else 0
            ebitda_ltm = (cm3_ltm / revenue_ltm * 100) if revenue_ltm > 0 else 0
            
            top_asin_buckets_data.append({
                'id': row['id'],
                'name': row['bucket_name'],
                'revenue_2024': revenue_2024,
                'revenue_ltm': revenue_ltm,
                'cm3_2024': cm3_2024,
                'cm3_ltm': cm3_ltm,
                'yoy_growth': yoy_growth,
                'ebitda_2024': ebitda_2024,
                'ebitda_ltm': ebitda_ltm,
                'stock_ltm': stock_ltm,
                'forecast': forecast
            })
    
    # Get Others data (ASINs not in Good Brands, Category Managed Brands, or Top ASIN Buckets), grouped by category
    others_data = []
    if bucket_type is None or bucket_type == 'others':
        # Pre-fetch excluded IDs
        cursor.execute("""
            SELECT id FROM brand_buckets 
            WHERE name IN ('Good Brands', 'Category Managed Brands')
        """)
        excluded_bucket_ids = [row['id'] for row in cursor.fetchall()]
        
        # Get brands that are NOT in excluded buckets
        if excluded_bucket_ids:
            bucket_placeholders = ','.join(['%s'] * len(excluded_bucket_ids))
            bucket_filter = f"AND (b.brand_bucket_id IS NULL OR b.brand_bucket_id NOT IN ({bucket_placeholders}))"
            bucket_params = excluded_bucket_ids
        else:
            bucket_filter = "AND b.brand_bucket_id IS NULL"
            bucket_params = []
        
        # Step 1: Get total revenue by category for eligible brands (excluding Good Brands and Category Managed Brands)
        # Use brand summary table for speed
        others_query = f"""
            SELECT 
                s.category_id,
                c.category,
                -- Revenue 2024 (excluding EOL - filtered at brand level via summary table)
                COALESCE(SUM(CASE 
                    WHEN LOWER(s.metric) = 'net revenue'
                    AND YEAR(s.month) = 2024 
                    THEN s.total_value 
                    ELSE 0 
                END), 0) as revenue_2024,
                -- Revenue LTM (Nov 2024 - Oct 2025)
                COALESCE(SUM(CASE 
                    WHEN LOWER(s.metric) = 'net revenue'
                    AND (
                        (YEAR(s.month) = 2024 AND MONTH(s.month) >= 11) OR
                        (YEAR(s.month) = 2025 AND MONTH(s.month) <= 10)
                    )
                    THEN s.total_value 
                    ELSE 0 
                END), 0) as revenue_ltm,
                -- CM3 2024
                COALESCE(SUM(CASE 
                    WHEN LOWER(s.metric) = 'cm3'
                    AND YEAR(s.month) = 2024 
                    THEN s.total_value 
                    ELSE 0 
                END), 0) as cm3_2024,
                -- CM3 LTM (Nov 2024 - Oct 2025)
                COALESCE(SUM(CASE 
                    WHEN LOWER(s.metric) = 'cm3'
                    AND (
                        (YEAR(s.month) = 2024 AND MONTH(s.month) >= 11) OR
                        (YEAR(s.month) = 2025 AND MONTH(s.month) <= 10)
                    )
                    THEN s.total_value 
                    ELSE 0 
                END), 0) as cm3_ltm
            FROM financials_summary_monthly_brand s
            INNER JOIN category c ON s.category_id = c.id
            INNER JOIN brand b ON s.brand_id = b.id
            WHERE (b.`group` IS NULL OR b.`group` != 'stock')
            {bucket_filter}
            AND s.marketplace = 'ALL'
            AND s.category_id IS NOT NULL
            GROUP BY s.category_id, c.category
            ORDER BY revenue_ltm DESC
        """
        cursor.execute(others_query, bucket_params)
        category_totals = {row['category_id']: row for row in cursor.fetchall()}
        
        # Step 2: Get revenue from top_asin_buckets ASINs by category (to subtract)
        top_asin_query = """
            SELECT 
                b.category_id,
                -- Revenue 2024 (excluding EOL)
                COALESCE(SUM(CASE 
                    WHEN LOWER(s.metric) = 'net revenue'
                    AND YEAR(s.month) = 2024 
                    AND (a.eol IS NULL OR a.eol = 0)
                    THEN s.value 
                    ELSE 0 
                END), 0) as revenue_2024,
                -- Revenue LTM (Nov 2024 - Oct 2025, excluding EOL)
                COALESCE(SUM(CASE 
                    WHEN LOWER(s.metric) = 'net revenue'
                    AND (
                        (YEAR(s.month) = 2024 AND MONTH(s.month) >= 11) OR
                        (YEAR(s.month) = 2025 AND MONTH(s.month) <= 10)
                    )
                    AND (a.eol IS NULL OR a.eol = 0)
                    THEN s.value 
                    ELSE 0 
                END), 0) as revenue_ltm,
                -- CM3 2024
                COALESCE(SUM(CASE 
                    WHEN LOWER(s.metric) = 'cm3'
                    AND YEAR(s.month) = 2024 
                    THEN s.value 
                    ELSE 0 
                END), 0) as cm3_2024,
                -- CM3 LTM (Nov 2024 - Oct 2025)
                COALESCE(SUM(CASE 
                    WHEN LOWER(s.metric) = 'cm3'
                    AND (
                        (YEAR(s.month) = 2024 AND MONTH(s.month) >= 11) OR
                        (YEAR(s.month) = 2025 AND MONTH(s.month) <= 10)
                    )
                    THEN s.value 
                    ELSE 0 
                END), 0) as cm3_ltm
            FROM top_asins ta
            INNER JOIN asin a ON ta.asin_id = a.id
            INNER JOIN brand b ON a.brand_id = b.id
            LEFT JOIN financials_summary_monthly_asin_marketplace s ON a.id = s.asin_id
            WHERE b.category_id IS NOT NULL
            GROUP BY b.category_id
        """
        cursor.execute(top_asin_query)
        top_asin_by_category = {row['category_id']: row for row in cursor.fetchall()}
        
        # Step 3: Subtract top_asin_buckets revenue from category totals
        for category_id, category_total in category_totals.items():
            top_asin_data = top_asin_by_category.get(category_id, {})
            
            revenue_2024 = float(category_total['revenue_2024']) - float(top_asin_data.get('revenue_2024', 0))
            revenue_ltm = float(category_total['revenue_ltm']) - float(top_asin_data.get('revenue_ltm', 0))
            cm3_2024 = float(category_total['cm3_2024']) - float(top_asin_data.get('cm3_2024', 0))
            cm3_ltm = float(category_total['cm3_ltm']) - float(top_asin_data.get('cm3_ltm', 0))
            
            # Only include categories with positive LTM revenue after subtraction
            if revenue_ltm > 0:
                yoy_growth = ((revenue_ltm - revenue_2024) / revenue_2024 * 100) if revenue_2024 > 0 else 0
                ebitda_2024 = (cm3_2024 / revenue_2024 * 100) if revenue_2024 > 0 else 0
                ebitda_ltm = (cm3_ltm / revenue_ltm * 100) if revenue_ltm > 0 else 0
                
                others_data.append({
                    'id': category_id,
                    'name': category_total['category'],
                    'revenue_2024': revenue_2024,
                    'revenue_ltm': revenue_ltm,
                    'cm3_2024': cm3_2024,
                    'cm3_ltm': cm3_ltm,
                    'yoy_growth': yoy_growth,
                    'ebitda_2024': ebitda_2024,
                    'ebitda_ltm': ebitda_ltm,
                    'forecast': 0  # Will calculate below
                })
        
        # Step 4: Get forecast for others by category (total forecast minus top_asin_buckets forecast)
        category_ids = [row['id'] for row in others_data]
        category_forecasts = {}
        if category_ids:
            # Get total forecast by category for eligible brands
            category_placeholders = ','.join(['%s'] * len(category_ids))
            if excluded_bucket_ids:
                bucket_forecast_placeholders = ','.join(['%s'] * len(excluded_bucket_ids))
                total_forecast_query = f"""
                    SELECT 
                        b.category_id,
                        SUM(fa.value) as total_forecast
                    FROM forecast_asin fa
                    INNER JOIN asin a ON fa.asin_id = a.id
                    INNER JOIN brand b ON a.brand_id = b.id
                    WHERE b.category_id IN ({category_placeholders})
                    AND (b.brand_bucket_id IS NULL OR b.brand_bucket_id NOT IN ({bucket_forecast_placeholders}))
                    AND (a.eol IS NULL OR a.eol = 0)
                    AND LOWER(fa.metric) = 'net revenue'
                    AND fa.month >= '2025-11-01'
                    AND fa.month <= '2026-10-31'
                    GROUP BY b.category_id
                """
                cursor.execute(total_forecast_query, category_ids + excluded_bucket_ids)
            else:
                total_forecast_query = f"""
                    SELECT 
                        b.category_id,
                        SUM(fa.value) as total_forecast
                    FROM forecast_asin fa
                    INNER JOIN asin a ON fa.asin_id = a.id
                    INNER JOIN brand b ON a.brand_id = b.id
                    WHERE b.category_id IN ({category_placeholders})
                    AND b.brand_bucket_id IS NULL
                    AND (a.eol IS NULL OR a.eol = 0)
                    AND LOWER(fa.metric) = 'net revenue'
                    AND fa.month >= '2025-11-01'
                    AND fa.month <= '2026-10-31'
                    GROUP BY b.category_id
                """
                cursor.execute(total_forecast_query, category_ids)
            
            total_forecasts = {row['category_id']: float(row['total_forecast']) for row in cursor.fetchall()}
            
            # Get top_asin_buckets forecast by category
            top_asin_forecast_query = f"""
                SELECT 
                    b.category_id,
                    SUM(fa.value) as total_forecast
                FROM forecast_asin fa
                INNER JOIN asin a ON fa.asin_id = a.id
                INNER JOIN top_asins ta ON a.id = ta.asin_id
                INNER JOIN brand b ON a.brand_id = b.id
                WHERE b.category_id IN ({category_placeholders})
                AND (a.eol IS NULL OR a.eol = 0)
                AND LOWER(fa.metric) = 'net revenue'
                AND fa.month >= '2025-11-01'
                AND fa.month <= '2026-10-31'
                GROUP BY b.category_id
            """
            cursor.execute(top_asin_forecast_query, category_ids)
            top_asin_forecasts = {row['category_id']: float(row['total_forecast']) for row in cursor.fetchall()}
            
            # Subtract top_asin_buckets forecast from total
            for category_id in category_ids:
                total_forecast = total_forecasts.get(category_id, 0)
                top_asin_forecast = top_asin_forecasts.get(category_id, 0)
                category_forecasts[category_id] = total_forecast - top_asin_forecast
            
            # Update forecast in others_data
            for item in others_data:
                item['forecast'] = category_forecasts.get(item['id'], 0)
            
            # Sort by revenue_ltm descending
            others_data.sort(key=lambda x: x['revenue_ltm'], reverse=True)
    
    # Close cursor and connection after all queries
    cursor.close()
    conn.close()
    
    return jsonify({
        'good_brands': good_brands_data,
        'category_managed_brands': category_managed_data,
        'top_asin_buckets': top_asin_buckets_data,
        'others': others_data
    })

@app.route('/api/profitability-data')
@login_required
def get_profitability_data():
    """API endpoint to get profitability data for brand or category (OPTIMIZED with summary tables)"""
    brand_id = request.args.get('brand_id')
    category_id = request.args.get('category_id')
    
    conn = get_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    
    # Use optimized summary table - queries pre-aggregated data!
    query = """
        SELECT 
            s.metric,
            s.month,
            MONTH(s.month) as month_num,
            YEAR(s.month) as year,
            SUM(s.total_value) as total_value
        FROM financials_summary_monthly_brand s
        WHERE (LOWER(s.metric) = 'net revenue' OR LOWER(s.metric) = 'cm3')
        AND YEAR(s.month) IN (2024, 2025)
        AND s.marketplace = 'ALL'
    """
    
    params = []
    
    if brand_id:
        query += " AND s.brand_id = %s"
        params.append(brand_id)
    elif category_id:
        query += " AND s.category_id = %s"
        params.append(category_id)
    
    query += """
        GROUP BY s.metric, s.month
        ORDER BY s.month
    """
    
    cursor.execute(query, params)
    results = cursor.fetchall()
    cursor.close()
    conn.close()
    
    # Organize data by month
    monthly_data = []
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    
    for month_idx in range(12):
        month_name = months[month_idx]
        month_num = month_idx + 1
        
        # Get 2024 data
        revenue_2024 = 0
        cm3_2024 = 0
        for row in results:
            if row['year'] == 2024 and row['month_num'] == month_num:
                metric_lower = row['metric'].lower() if row['metric'] else ''
                if metric_lower == 'net revenue':
                    revenue_2024 = float(row['total_value'])
                elif metric_lower == 'cm3':
                    cm3_2024 = float(row['total_value'])
        
        # Get 2025 data
        revenue_2025 = 0
        cm3_2025 = 0
        for row in results:
            if row['year'] == 2025 and row['month_num'] == month_num:
                metric_lower = row['metric'].lower() if row['metric'] else ''
                if metric_lower == 'net revenue':
                    revenue_2025 = float(row['total_value'])
                elif metric_lower == 'cm3':
                    cm3_2025 = float(row['total_value'])
        
        # Calculate metrics
        yoy_growth = ((revenue_2025 - revenue_2024) / revenue_2024 * 100) if revenue_2024 > 0 else 0
        ebitda_2024 = (cm3_2024 / revenue_2024 * 100) if revenue_2024 > 0 else 0
        ebitda_2025 = (cm3_2025 / revenue_2025 * 100) if revenue_2025 > 0 else 0
        
        monthly_data.append({
            'month': month_name,
            'revenue_2024': revenue_2024,
            'revenue_2025': revenue_2025,
            'yoy_growth': yoy_growth,
            'ebitda_2024': ebitda_2024,
            'ebitda_2025': ebitda_2025
        })
    
    return jsonify({
        'data': monthly_data
    })

@app.route('/')
@login_required
def index():
    """Main page showing list of brands"""
    category_id_param = request.args.get('category_id')
    brand_bucket_id = request.args.get('brand_bucket_id', type=int)
    search_term = request.args.get('search', '')
    
    # Handle special "null" value for no category filter
    if category_id_param == 'null':
        category_id = 'null'
    elif category_id_param:
        category_id = int(category_id_param)
    else:
        category_id = None
    
    brands = get_brands(category_id, brand_bucket_id, search_term)
    categories = get_categories()
    brand_buckets = get_brand_buckets()
    
    # Calculate summary statistics for filtered results
    total_ltm_revenue = sum(brand['ltm_revenues'] or 0 for brand in brands)
    total_ltm_cm3 = sum(brand['ltm_cm3'] or 0 for brand in brands)
    total_ltm_units = sum(brand['ltm_units'] or 0 for brand in brands)
    total_ltm_stock = sum(brand['stock_value'] or 0 for brand in brands)
    total_stock_units = sum(brand['stock_units'] or 0 for brand in brands)
    total_overstock = sum(brand['stock_overstock_value'] or 0 for brand in brands)
    avg_ltm_ebitda = (total_ltm_cm3 / total_ltm_revenue * 100) if total_ltm_revenue > 0 else 0
    
    # Get total brand count (unfiltered)
    total_brands = get_brands(None, None, '')
    total_count = len(total_brands)
    
    return render_template('index.html', 
                         brands=brands, 
                         categories=categories,
                         brand_buckets=brand_buckets,
                         selected_category=category_id_param,
                         selected_brand_bucket=brand_bucket_id,
                         search_term=search_term,
                         total_brand_count=total_count,
                         filtered_brand_count=len(brands),
                         total_ltm_revenue=total_ltm_revenue,
                         total_ltm_cm3=total_ltm_cm3,
                         total_ltm_units=total_ltm_units,
                         total_ltm_stock=total_ltm_stock,
                         total_stock_units=total_stock_units,
                         total_overstock=total_overstock,
                         avg_ltm_ebitda=avg_ltm_ebitda)

@app.route('/edit/<int:brand_id>', methods=['GET', 'POST'])
@login_required
def edit_brand(brand_id):
    """Edit a brand"""
    if request.method == 'POST':
        brand_name = request.form.get('brand')
        url = request.form.get('url')
        category_id = request.form.get('category_id')
        group = request.form.get('group')
        sub_category = request.form.get('sub_category')
        brand_bucket_id = request.form.get('brand_bucket_id')
        
        try:
            update_brand(brand_id, brand_name, url, category_id, group, sub_category, brand_bucket_id)
            flash('Brand updated successfully!', 'success')
            return redirect(url_for('index'))
        except Exception as e:
            flash(f'Error updating brand: {str(e)}', 'error')
    
    brand = get_brand_by_id(brand_id)
    if not brand:
        flash('Brand not found', 'error')
        return redirect(url_for('index'))
    
    categories = get_categories()
    brand_buckets = get_brand_buckets()
    return render_template('edit_brand.html', brand=brand, categories=categories, brand_buckets=brand_buckets)

@app.route('/brand-buckets')
@login_required
def brand_buckets_list():
    """List all brand buckets"""
    buckets = get_brand_buckets()
    
    # Count brands in each bucket
    conn = get_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    cursor.execute("""
        SELECT brand_bucket_id, COUNT(*) as count
        FROM brand
        WHERE brand_bucket_id IS NOT NULL
        GROUP BY brand_bucket_id
    """)
    bucket_counts = {row['brand_bucket_id']: row['count'] for row in cursor.fetchall()}
    cursor.close()
    conn.close()
    
    # Add counts to buckets
    for bucket in buckets:
        bucket['brand_count'] = bucket_counts.get(bucket['id'], 0)
    
    return render_template('brand_buckets.html', buckets=buckets)

@app.route('/brand-buckets/add', methods=['GET', 'POST'])
@login_required
def add_brand_bucket():
    """Add a new brand bucket"""
    if request.method == 'POST':
        name = request.form.get('name')
        color = request.form.get('color', '#667eea')
        description = request.form.get('description', '')
        
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO brand_buckets (name, color, description)
                VALUES (%s, %s, %s)
            """, [name, color, description])
            conn.commit()
            cursor.close()
            conn.close()
            flash('Brand bucket created successfully!', 'success')
            return redirect(url_for('brand_buckets_list'))
        except Exception as e:
            flash(f'Error creating brand bucket: {str(e)}', 'error')
    
    return render_template('edit_brand_bucket.html', bucket=None)

@app.route('/brand-buckets/edit/<int:bucket_id>', methods=['GET', 'POST'])
@login_required
def edit_brand_bucket(bucket_id):
    """Edit a brand bucket"""
    if request.method == 'POST':
        name = request.form.get('name')
        color = request.form.get('color', '#667eea')
        description = request.form.get('description', '')
        
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE brand_buckets 
                SET name = %s, color = %s, description = %s
                WHERE id = %s
            """, [name, color, description, bucket_id])
            conn.commit()
            cursor.close()
            conn.close()
            flash('Brand bucket updated successfully!', 'success')
            return redirect(url_for('brand_buckets_list'))
        except Exception as e:
            flash(f'Error updating brand bucket: {str(e)}', 'error')
    
    # Get bucket details
    conn = get_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    cursor.execute("SELECT * FROM brand_buckets WHERE id = %s", [bucket_id])
    bucket = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if not bucket:
        flash('Brand bucket not found', 'error')
        return redirect(url_for('brand_buckets_list'))
    
    return render_template('edit_brand_bucket.html', bucket=bucket)

@app.route('/brand-buckets/delete/<int:bucket_id>', methods=['POST'])
@login_required
def delete_brand_bucket(bucket_id):
    """Delete a brand bucket"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM brand_buckets WHERE id = %s", [bucket_id])
        conn.commit()
        cursor.close()
        conn.close()
        flash('Brand bucket deleted successfully!', 'success')
    except Exception as e:
        flash(f'Error deleting brand bucket: {str(e)}', 'error')
    
    return redirect(url_for('brand_buckets_list'))

@app.route('/top-asins')
@login_required
def top_asins():
    """Display top ASINs across all brands with filtering and pagination"""
    # Get query parameters
    brand_id = request.args.get('brand_id', type=int)
    bucket_id = request.args.get('bucket_id', type=int)
    brand_bucket_id = request.args.get('brand_bucket_id', type=int)
    search_term = request.args.get('search', '')
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 50, type=int)
    hide_eol = request.args.get('hide_eol', type=int, default=0)
    
    # Calculate offset
    offset = (page - 1) * page_size
    
    conn = get_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    
    # Get filter type for bucket combinations
    bucket_filter = request.args.get('bucket_filter', 'all')
    
    # Build query - now includes bucket information AND brand bucket information
    query = """
        SELECT 
            a.id,
            a.asin,
            a.name,
            a.title,
            a.price,
            a.rating,
            a.rating_count,
            a.main_image,
            a.amazon_category,
            a.ltm_revenues,
            a.ltm_cm3,
            a.ltm_brand_ebitda,
            a.ltm_units,
            a.stock_value,
            a.stock_units,
            a.stock_overstock_value,
            a.scraped_at,
            b.brand,
            b.id as brand_id,
            b.url as brand_url,
            bb.name as brand_bucket_name,
            bb.color as brand_bucket_color,
            GROUP_CONCAT(DISTINCT tab.name ORDER BY tab.name SEPARATOR ', ') as bucket_names,
            GROUP_CONCAT(DISTINCT tab.color ORDER BY tab.name SEPARATOR ',') as bucket_colors
        FROM asin a
        LEFT JOIN brand b ON a.brand_id = b.id
        LEFT JOIN brand_buckets bb ON b.brand_bucket_id = bb.id
        LEFT JOIN top_asins ta ON a.id = ta.asin_id
        LEFT JOIN top_asin_buckets tab ON ta.bucket_id = tab.id
        WHERE (b.`group` IS NULL OR b.`group` != 'stock')
    """
    
    params = []
    
    # Add brand filter
    if brand_id:
        query += " AND a.brand_id = %s"
        params.append(brand_id)
    
    # Add bucket filter
    if bucket_id:
        query += " AND ta.bucket_id = %s"
        params.append(bucket_id)
    
    # Add brand bucket filter
    if brand_bucket_id:
        query += " AND b.brand_bucket_id = %s"
        params.append(brand_bucket_id)
    
    # Add search filter
    if search_term:
        query += " AND (a.title LIKE %s OR a.name LIKE %s OR a.asin LIKE %s)"
        search_pattern = f"%{search_term}%"
        params.extend([search_pattern, search_pattern, search_pattern])
    
    # Add EOL filter
    if hide_eol:
        query += " AND (a.eol IS NULL OR a.eol = 0)"
    
    # Add bucket combination filter
    query += " GROUP BY a.id"
    
    if bucket_filter == 'has_asin_bucket':
        query += " HAVING COUNT(DISTINCT ta.bucket_id) > 0"
    elif bucket_filter == 'has_brand_bucket':
        query += " HAVING MAX(CASE WHEN bb.id IS NOT NULL THEN 1 ELSE 0 END) = 1"
    elif bucket_filter == 'has_both':
        query += " HAVING COUNT(DISTINCT ta.bucket_id) > 0 AND MAX(CASE WHEN bb.id IS NOT NULL THEN 1 ELSE 0 END) = 1"
    elif bucket_filter == 'no_asin_bucket':
        query += " HAVING COUNT(DISTINCT ta.bucket_id) = 0"
    elif bucket_filter == 'no_brand_bucket':
        query += " HAVING MAX(CASE WHEN bb.id IS NOT NULL THEN 1 ELSE 0 END) = 0"
    elif bucket_filter == 'both_none':
        query += " HAVING COUNT(DISTINCT ta.bucket_id) = 0 AND MAX(CASE WHEN bb.id IS NOT NULL THEN 1 ELSE 0 END) = 0"
    
    query += """
        ORDER BY a.ltm_revenues DESC
        LIMIT %s OFFSET %s
    """
    
    params.extend([page_size, offset])
    
    cursor.execute(query, params)
    asins = cursor.fetchall()
    
    # Get total count for pagination
    count_query = """
        SELECT COUNT(*) as total
        FROM (
            SELECT DISTINCT a.id
            FROM asin a
            LEFT JOIN brand b ON a.brand_id = b.id
            LEFT JOIN brand_buckets bb ON b.brand_bucket_id = bb.id
            LEFT JOIN top_asins ta ON a.id = ta.asin_id
            WHERE (b.`group` IS NULL OR b.`group` != 'stock')
    """
    
    count_params = []
    if brand_id:
        count_query += " AND a.brand_id = %s"
        count_params.append(brand_id)
    
    if bucket_id:
        count_query += " AND ta.bucket_id = %s"
        count_params.append(bucket_id)
    
    if brand_bucket_id:
        count_query += " AND b.brand_bucket_id = %s"
        count_params.append(brand_bucket_id)
    
    if search_term:
        count_query += " AND (a.title LIKE %s OR a.name LIKE %s OR a.asin LIKE %s)"
        search_pattern = f"%{search_term}%"
        count_params.extend([search_pattern, search_pattern, search_pattern])
    
    if hide_eol:
        count_query += " AND (a.eol IS NULL OR a.eol = 0)"
    
    count_query += " GROUP BY a.id"
    
    if bucket_filter == 'has_asin_bucket':
        count_query += " HAVING COUNT(DISTINCT ta.bucket_id) > 0"
    elif bucket_filter == 'has_brand_bucket':
        count_query += " HAVING MAX(CASE WHEN bb.id IS NOT NULL THEN 1 ELSE 0 END) = 1"
    elif bucket_filter == 'has_both':
        count_query += " HAVING COUNT(DISTINCT ta.bucket_id) > 0 AND MAX(CASE WHEN bb.id IS NOT NULL THEN 1 ELSE 0 END) = 1"
    elif bucket_filter == 'no_asin_bucket':
        count_query += " HAVING COUNT(DISTINCT ta.bucket_id) = 0"
    elif bucket_filter == 'no_brand_bucket':
        count_query += " HAVING MAX(CASE WHEN bb.id IS NOT NULL THEN 1 ELSE 0 END) = 0"
    elif bucket_filter == 'both_none':
        count_query += " HAVING COUNT(DISTINCT ta.bucket_id) = 0 AND MAX(CASE WHEN bb.id IS NOT NULL THEN 1 ELSE 0 END) = 0"
    
    count_query += ") as filtered_asins"
    
    cursor.execute(count_query, count_params)
    total_count = cursor.fetchone()['total']
    
    # Get total LTM revenues for filtered results - using same subquery approach
    revenue_query = """
        SELECT SUM(ltm_revenues) as total_revenue
        FROM (
            SELECT DISTINCT a.id, a.ltm_revenues
            FROM asin a
            LEFT JOIN brand b ON a.brand_id = b.id
            LEFT JOIN brand_buckets bb ON b.brand_bucket_id = bb.id
            LEFT JOIN top_asins ta ON a.id = ta.asin_id
            WHERE (b.`group` IS NULL OR b.`group` != 'stock')
    """
    
    revenue_params = []
    if brand_id:
        revenue_query += " AND a.brand_id = %s"
        revenue_params.append(brand_id)
    
    if bucket_id:
        revenue_query += " AND ta.bucket_id = %s"
        revenue_params.append(bucket_id)
    
    if brand_bucket_id:
        revenue_query += " AND b.brand_bucket_id = %s"
        revenue_params.append(brand_bucket_id)
    
    if search_term:
        revenue_query += " AND (a.title LIKE %s OR a.name LIKE %s OR a.asin LIKE %s)"
        search_pattern = f"%{search_term}%"
        revenue_params.extend([search_pattern, search_pattern, search_pattern])
    
    if hide_eol:
        revenue_query += " AND (a.eol IS NULL OR a.eol = 0)"
    
    revenue_query += " GROUP BY a.id"
    
    if bucket_filter == 'has_asin_bucket':
        revenue_query += " HAVING COUNT(DISTINCT ta.bucket_id) > 0"
    elif bucket_filter == 'has_brand_bucket':
        revenue_query += " HAVING MAX(CASE WHEN bb.id IS NOT NULL THEN 1 ELSE 0 END) = 1"
    elif bucket_filter == 'has_both':
        revenue_query += " HAVING COUNT(DISTINCT ta.bucket_id) > 0 AND MAX(CASE WHEN bb.id IS NOT NULL THEN 1 ELSE 0 END) = 1"
    elif bucket_filter == 'no_asin_bucket':
        revenue_query += " HAVING COUNT(DISTINCT ta.bucket_id) = 0"
    elif bucket_filter == 'no_brand_bucket':
        revenue_query += " HAVING MAX(CASE WHEN bb.id IS NOT NULL THEN 1 ELSE 0 END) = 0"
    elif bucket_filter == 'both_none':
        revenue_query += " HAVING COUNT(DISTINCT ta.bucket_id) = 0 AND MAX(CASE WHEN bb.id IS NOT NULL THEN 1 ELSE 0 END) = 0"
    
    revenue_query += ") as filtered_asins"
    
    cursor.execute(revenue_query, revenue_params)
    total_revenue = cursor.fetchone()['total_revenue'] or 0
    
    # Get total LTM stock value for filtered results
    stock_query = """
        SELECT SUM(stock_value) as total_stock
        FROM (
            SELECT DISTINCT a.id, a.stock_value
            FROM asin a
            LEFT JOIN brand b ON a.brand_id = b.id
            LEFT JOIN brand_buckets bb ON b.brand_bucket_id = bb.id
            LEFT JOIN top_asins ta ON a.id = ta.asin_id
            WHERE (b.`group` IS NULL OR b.`group` != 'stock')
    """
    
    stock_params = []
    if brand_id:
        stock_query += " AND a.brand_id = %s"
        stock_params.append(brand_id)
    
    if bucket_id:
        stock_query += " AND ta.bucket_id = %s"
        stock_params.append(bucket_id)
    
    if brand_bucket_id:
        stock_query += " AND b.brand_bucket_id = %s"
        stock_params.append(brand_bucket_id)
    
    if search_term:
        stock_query += " AND (a.title LIKE %s OR a.name LIKE %s OR a.asin LIKE %s)"
        search_pattern = f"%{search_term}%"
        stock_params.extend([search_pattern, search_pattern, search_pattern])
    
    if hide_eol:
        stock_query += " AND (a.eol IS NULL OR a.eol = 0)"
    
    stock_query += " GROUP BY a.id"
    
    if bucket_filter == 'has_asin_bucket':
        stock_query += " HAVING COUNT(DISTINCT ta.bucket_id) > 0"
    elif bucket_filter == 'has_brand_bucket':
        stock_query += " HAVING MAX(CASE WHEN bb.id IS NOT NULL THEN 1 ELSE 0 END) = 1"
    elif bucket_filter == 'has_both':
        stock_query += " HAVING COUNT(DISTINCT ta.bucket_id) > 0 AND MAX(CASE WHEN bb.id IS NOT NULL THEN 1 ELSE 0 END) = 1"
    elif bucket_filter == 'no_asin_bucket':
        stock_query += " HAVING COUNT(DISTINCT ta.bucket_id) = 0"
    elif bucket_filter == 'no_brand_bucket':
        stock_query += " HAVING MAX(CASE WHEN bb.id IS NOT NULL THEN 1 ELSE 0 END) = 0"
    elif bucket_filter == 'both_none':
        stock_query += " HAVING COUNT(DISTINCT ta.bucket_id) = 0 AND MAX(CASE WHEN bb.id IS NOT NULL THEN 1 ELSE 0 END) = 0"
    
    stock_query += ") as filtered_asins"
    
    cursor.execute(stock_query, stock_params)
    total_stock = cursor.fetchone()['total_stock'] or 0
    
    # Get total LTM overstock value for filtered results
    overstock_query = """
        SELECT SUM(stock_overstock_value) as total_overstock
        FROM (
            SELECT DISTINCT a.id, a.stock_overstock_value
            FROM asin a
            LEFT JOIN brand b ON a.brand_id = b.id
            LEFT JOIN brand_buckets bb ON b.brand_bucket_id = bb.id
            LEFT JOIN top_asins ta ON a.id = ta.asin_id
            WHERE (b.`group` IS NULL OR b.`group` != 'stock')
    """
    
    overstock_params = []
    if brand_id:
        overstock_query += " AND a.brand_id = %s"
        overstock_params.append(brand_id)
    
    if bucket_id:
        overstock_query += " AND ta.bucket_id = %s"
        overstock_params.append(bucket_id)
    
    if brand_bucket_id:
        overstock_query += " AND b.brand_bucket_id = %s"
        overstock_params.append(brand_bucket_id)
    
    if search_term:
        overstock_query += " AND (a.title LIKE %s OR a.name LIKE %s OR a.asin LIKE %s)"
        search_pattern = f"%{search_term}%"
        overstock_params.extend([search_pattern, search_pattern, search_pattern])
    
    if hide_eol:
        overstock_query += " AND (a.eol IS NULL OR a.eol = 0)"
    
    overstock_query += " GROUP BY a.id"
    
    if bucket_filter == 'has_asin_bucket':
        overstock_query += " HAVING COUNT(DISTINCT ta.bucket_id) > 0"
    elif bucket_filter == 'has_brand_bucket':
        overstock_query += " HAVING MAX(CASE WHEN bb.id IS NOT NULL THEN 1 ELSE 0 END) = 1"
    elif bucket_filter == 'has_both':
        overstock_query += " HAVING COUNT(DISTINCT ta.bucket_id) > 0 AND MAX(CASE WHEN bb.id IS NOT NULL THEN 1 ELSE 0 END) = 1"
    elif bucket_filter == 'no_asin_bucket':
        overstock_query += " HAVING COUNT(DISTINCT ta.bucket_id) = 0"
    elif bucket_filter == 'no_brand_bucket':
        overstock_query += " HAVING MAX(CASE WHEN bb.id IS NOT NULL THEN 1 ELSE 0 END) = 0"
    elif bucket_filter == 'both_none':
        overstock_query += " HAVING COUNT(DISTINCT ta.bucket_id) = 0 AND MAX(CASE WHEN bb.id IS NOT NULL THEN 1 ELSE 0 END) = 0"
    
    overstock_query += ") as filtered_asins"
    
    cursor.execute(overstock_query, overstock_params)
    total_overstock = cursor.fetchone()['total_overstock'] or 0
    
    # Get total LTM CM3 for filtered results
    cm3_query = """
        SELECT SUM(ltm_cm3) as total_cm3
        FROM (
            SELECT DISTINCT a.id, a.ltm_cm3
            FROM asin a
            LEFT JOIN brand b ON a.brand_id = b.id
            LEFT JOIN brand_buckets bb ON b.brand_bucket_id = bb.id
            LEFT JOIN top_asins ta ON a.id = ta.asin_id
            WHERE (b.`group` IS NULL OR b.`group` != 'stock')
    """
    
    cm3_params = []
    if brand_id:
        cm3_query += " AND a.brand_id = %s"
        cm3_params.append(brand_id)
    
    if bucket_id:
        cm3_query += " AND ta.bucket_id = %s"
        cm3_params.append(bucket_id)
    
    if brand_bucket_id:
        cm3_query += " AND b.brand_bucket_id = %s"
        cm3_params.append(brand_bucket_id)
    
    if search_term:
        cm3_query += " AND (a.title LIKE %s OR a.name LIKE %s OR a.asin LIKE %s)"
        search_pattern = f"%{search_term}%"
        cm3_params.extend([search_pattern, search_pattern, search_pattern])
    
    if hide_eol:
        cm3_query += " AND (a.eol IS NULL OR a.eol = 0)"
    
    cm3_query += " GROUP BY a.id"
    
    if bucket_filter == 'has_asin_bucket':
        cm3_query += " HAVING COUNT(DISTINCT ta.bucket_id) > 0"
    elif bucket_filter == 'has_brand_bucket':
        cm3_query += " HAVING MAX(CASE WHEN bb.id IS NOT NULL THEN 1 ELSE 0 END) = 1"
    elif bucket_filter == 'has_both':
        cm3_query += " HAVING COUNT(DISTINCT ta.bucket_id) > 0 AND MAX(CASE WHEN bb.id IS NOT NULL THEN 1 ELSE 0 END) = 1"
    elif bucket_filter == 'no_asin_bucket':
        cm3_query += " HAVING COUNT(DISTINCT ta.bucket_id) = 0"
    elif bucket_filter == 'no_brand_bucket':
        cm3_query += " HAVING MAX(CASE WHEN bb.id IS NOT NULL THEN 1 ELSE 0 END) = 0"
    elif bucket_filter == 'both_none':
        cm3_query += " HAVING COUNT(DISTINCT ta.bucket_id) = 0 AND MAX(CASE WHEN bb.id IS NOT NULL THEN 1 ELSE 0 END) = 0"
    
    cm3_query += ") as filtered_asins"
    
    cursor.execute(cm3_query, cm3_params)
    total_cm3 = cursor.fetchone()['total_cm3'] or 0
    
    # Get total LTM units for filtered results
    units_query = """
        SELECT SUM(ltm_units) as total_units
        FROM (
            SELECT DISTINCT a.id, a.ltm_units
            FROM asin a
            LEFT JOIN brand b ON a.brand_id = b.id
            LEFT JOIN brand_buckets bb ON b.brand_bucket_id = bb.id
            LEFT JOIN top_asins ta ON a.id = ta.asin_id
            WHERE (b.`group` IS NULL OR b.`group` != 'stock')
    """
    
    units_params = []
    if brand_id:
        units_query += " AND a.brand_id = %s"
        units_params.append(brand_id)
    
    if bucket_id:
        units_query += " AND ta.bucket_id = %s"
        units_params.append(bucket_id)
    
    if brand_bucket_id:
        units_query += " AND b.brand_bucket_id = %s"
        units_params.append(brand_bucket_id)
    
    if search_term:
        units_query += " AND (a.title LIKE %s OR a.name LIKE %s OR a.asin LIKE %s)"
        search_pattern = f"%{search_term}%"
        units_params.extend([search_pattern, search_pattern, search_pattern])
    
    if hide_eol:
        units_query += " AND (a.eol IS NULL OR a.eol = 0)"
    
    units_query += " GROUP BY a.id"
    
    if bucket_filter == 'has_asin_bucket':
        units_query += " HAVING COUNT(DISTINCT ta.bucket_id) > 0"
    elif bucket_filter == 'has_brand_bucket':
        units_query += " HAVING MAX(CASE WHEN bb.id IS NOT NULL THEN 1 ELSE 0 END) = 1"
    elif bucket_filter == 'has_both':
        units_query += " HAVING COUNT(DISTINCT ta.bucket_id) > 0 AND MAX(CASE WHEN bb.id IS NOT NULL THEN 1 ELSE 0 END) = 1"
    elif bucket_filter == 'no_asin_bucket':
        units_query += " HAVING COUNT(DISTINCT ta.bucket_id) = 0"
    elif bucket_filter == 'no_brand_bucket':
        units_query += " HAVING MAX(CASE WHEN bb.id IS NOT NULL THEN 1 ELSE 0 END) = 0"
    elif bucket_filter == 'both_none':
        units_query += " HAVING COUNT(DISTINCT ta.bucket_id) = 0 AND MAX(CASE WHEN bb.id IS NOT NULL THEN 1 ELSE 0 END) = 0"
    
    units_query += ") as filtered_asins"
    
    cursor.execute(units_query, units_params)
    total_units = cursor.fetchone()['total_units'] or 0
    
    # Get total stock units for filtered results
    stock_units_query = """
        SELECT SUM(stock_units) as total_stock_units
        FROM (
            SELECT DISTINCT a.id, a.stock_units
            FROM asin a
            LEFT JOIN brand b ON a.brand_id = b.id
            LEFT JOIN brand_buckets bb ON b.brand_bucket_id = bb.id
            LEFT JOIN top_asins ta ON a.id = ta.asin_id
            WHERE (b.`group` IS NULL OR b.`group` != 'stock')
    """
    
    stock_units_params = []
    if brand_id:
        stock_units_query += " AND a.brand_id = %s"
        stock_units_params.append(brand_id)
    
    if bucket_id:
        stock_units_query += " AND ta.bucket_id = %s"
        stock_units_params.append(bucket_id)
    
    if brand_bucket_id:
        stock_units_query += " AND b.brand_bucket_id = %s"
        stock_units_params.append(brand_bucket_id)
    
    if search_term:
        stock_units_query += " AND (a.title LIKE %s OR a.name LIKE %s OR a.asin LIKE %s)"
        search_pattern = f"%{search_term}%"
        stock_units_params.extend([search_pattern, search_pattern, search_pattern])
    
    if hide_eol:
        stock_units_query += " AND (a.eol IS NULL OR a.eol = 0)"
    
    stock_units_query += " GROUP BY a.id"
    
    if bucket_filter == 'has_asin_bucket':
        stock_units_query += " HAVING COUNT(DISTINCT ta.bucket_id) > 0"
    elif bucket_filter == 'has_brand_bucket':
        stock_units_query += " HAVING MAX(CASE WHEN bb.id IS NOT NULL THEN 1 ELSE 0 END) = 1"
    elif bucket_filter == 'has_both':
        stock_units_query += " HAVING COUNT(DISTINCT ta.bucket_id) > 0 AND MAX(CASE WHEN bb.id IS NOT NULL THEN 1 ELSE 0 END) = 1"
    elif bucket_filter == 'no_asin_bucket':
        stock_units_query += " HAVING COUNT(DISTINCT ta.bucket_id) = 0"
    elif bucket_filter == 'no_brand_bucket':
        stock_units_query += " HAVING MAX(CASE WHEN bb.id IS NOT NULL THEN 1 ELSE 0 END) = 0"
    elif bucket_filter == 'both_none':
        stock_units_query += " HAVING COUNT(DISTINCT ta.bucket_id) = 0 AND MAX(CASE WHEN bb.id IS NOT NULL THEN 1 ELSE 0 END) = 0"
    
    stock_units_query += ") as filtered_asins"
    
    cursor.execute(stock_units_query, stock_units_params)
    total_stock_units = cursor.fetchone()['total_stock_units'] or 0
    
    # Calculate average EBITDA %
    avg_ebitda = (total_cm3 / total_revenue * 100) if total_revenue > 0 else 0
    
    # Get all brands for filter dropdown
    cursor.execute("""
        SELECT id, brand 
        FROM brand 
        WHERE (`group` IS NULL OR `group` != 'stock')
        ORDER BY brand ASC
    """)
    brands = cursor.fetchall()
    
    # Get all top ASIN buckets
    cursor.execute("""
        SELECT id, name, color, description
        FROM top_asin_buckets
        ORDER BY name
    """)
    top_asin_buckets = cursor.fetchall()
    
    # Get all brand buckets
    cursor.execute("""
        SELECT id, name, color
        FROM brand_buckets
        ORDER BY name
    """)
    brand_buckets = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    # Calculate total pages
    total_pages = (total_count + page_size - 1) // page_size
    
    return render_template('top_asins.html', 
                         asins=asins,
                         brands=brands,
                         top_asin_buckets=top_asin_buckets,
                         brand_buckets=brand_buckets,
                         total_count=total_count,
                         total_revenue=total_revenue,
                         total_cm3=total_cm3,
                         total_units=total_units,
                         total_stock=total_stock,
                         total_stock_units=total_stock_units,
                         total_overstock=total_overstock,
                         avg_ebitda=avg_ebitda,
                         page=page,
                         page_size=page_size,
                         total_pages=total_pages,
                         brand_id=brand_id,
                         bucket_id=bucket_id,
                         brand_bucket_id=brand_bucket_id,
                         search_term=search_term,
                         bucket_filter=bucket_filter,
                         hide_eol=hide_eol)

@app.route('/top-asin-buckets')
@login_required
def top_asin_buckets_list():
    """Display all top ASIN buckets with statistics"""
    conn = get_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    
    # Get all buckets with their statistics
    query = """
        SELECT 
            tab.id,
            tab.name,
            tab.description,
            tab.color,
            tab.created_at,
            COUNT(DISTINCT ta.asin_id) as asin_count,
            COALESCE(SUM(a.ltm_revenues), 0) as total_ltm_revenues,
            (
                SELECT a2.main_image
                FROM top_asins ta2
                INNER JOIN asin a2 ON ta2.asin_id = a2.id
                WHERE ta2.bucket_id = tab.id
                ORDER BY a2.ltm_revenues DESC
                LIMIT 1
            ) as top_asin_image,
            (
                SELECT a2.asin
                FROM top_asins ta2
                INNER JOIN asin a2 ON ta2.asin_id = a2.id
                WHERE ta2.bucket_id = tab.id
                ORDER BY a2.ltm_revenues DESC
                LIMIT 1
            ) as top_asin_code
        FROM top_asin_buckets tab
        LEFT JOIN top_asins ta ON tab.id = ta.bucket_id
        LEFT JOIN asin a ON ta.asin_id = a.id
        GROUP BY tab.id, tab.name, tab.description, tab.color, tab.created_at
        ORDER BY total_ltm_revenues DESC, tab.name
    """
    
    cursor.execute(query)
    buckets = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('top_asin_buckets_list.html', buckets=buckets)

@app.route('/brand/<int:brand_id>/asins')
@login_required
def brand_asins(brand_id):
    """Show ASINs for a brand"""
    brand = get_brand_by_id(brand_id)
    if not brand:
        flash('Brand not found', 'error')
        return redirect(url_for('index'))
    
    asins = get_brand_asins(brand_id)
    return render_template('brand_asins.html', brand=brand, asins=asins)

@app.route('/asin/<asin_code>')
@login_required
def view_asin(asin_code):
    """View detailed ASIN information with scraped data"""
    conn = get_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    
    query = """
        SELECT 
            a.*,
            b.brand,
            b.url as brand_url,
            c.category
        FROM asin a
        LEFT JOIN brand b ON a.brand_id = b.id
        LEFT JOIN category c ON b.category_id = c.id
        WHERE a.asin = %s
    """
    
    cursor.execute(query, [asin_code])
    asin = cursor.fetchone()
    
    if not asin:
        cursor.close()
        conn.close()
        flash('ASIN not found', 'error')
        return redirect(url_for('index'))
    
    # Get buckets this ASIN is allocated to
    cursor.execute("""
        SELECT tab.id, tab.name, tab.color, tab.description
        FROM top_asin_buckets tab
        INNER JOIN top_asins ta ON tab.id = ta.bucket_id
        WHERE ta.asin_id = %s
        ORDER BY tab.name
    """, [asin['id']])
    asin_buckets = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    # Parse the JSON data if available
    import json
    scraped_data = None
    if asin.get('parse_json'):
        try:
            scraped_data = json.loads(asin['parse_json'])
        except:
            pass
    
    return render_template('view_asin.html', asin=asin, scraped_data=scraped_data, asin_buckets=asin_buckets)

@app.route('/api/asin-revenue-data/<asin_code>')
@login_required
def get_asin_revenue_data(asin_code):
    """API endpoint to get revenue data for a specific ASIN"""
    conn = get_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    
    # Get ASIN ID first
    cursor.execute("SELECT id FROM asin WHERE asin = %s", [asin_code])
    asin_result = cursor.fetchone()
    
    if not asin_result:
        cursor.close()
        conn.close()
        return jsonify({'error': 'ASIN not found'}), 404
    
    asin_id = asin_result['id']
    
    # Get revenue data by month for 2024 and 2025
    query = """
        SELECT 
            MONTH(f.month) as month_num,
            YEAR(f.month) as year,
            SUM(f.value) as total_value
        FROM financials f
        WHERE f.asin_id = %s
        AND LOWER(f.metric) = 'net revenue'
        AND YEAR(f.month) IN (2024, 2025)
        GROUP BY YEAR(f.month), MONTH(f.month)
        ORDER BY YEAR(f.month), MONTH(f.month)
    """
    
    cursor.execute(query, [asin_id])
    results = cursor.fetchall()
    cursor.close()
    conn.close()
    
    # Organize data by year and month
    data_2024 = [0] * 12
    data_2025 = [None] * 12
    
    for row in results:
        month_idx = row['month_num'] - 1
        if row['year'] == 2024:
            data_2024[month_idx] = float(row['total_value'])
        elif row['year'] == 2025:
            data_2025[month_idx] = float(row['total_value']) if row['total_value'] else 0
    
    return jsonify({
        'months': ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
        'data_2024': data_2024,
        'data_2025': data_2025,
        'asin': asin_code
    })

@app.route('/api/top-asin-buckets/create', methods=['POST'])
@login_required
def create_top_asin_bucket():
    """API endpoint to create a new top ASIN bucket"""
    try:
        data = request.get_json()
        name = data.get('name')
        description = data.get('description', '')
        color = data.get('color', '#667eea')
        
        if not name:
            return jsonify({'success': False, 'error': 'Bucket name is required'}), 400
        
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO top_asin_buckets (name, description, color)
            VALUES (%s, %s, %s)
        """, [name, description, color])
        bucket_id = cursor.lastrowid
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'bucket_id': bucket_id,
            'name': name,
            'message': 'Bucket created successfully'
        })
    except pymysql.IntegrityError:
        return jsonify({'success': False, 'error': 'A bucket with this name already exists'}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/top-asins/allocate', methods=['POST'])
@login_required
def allocate_asins_to_bucket():
    """API endpoint to allocate ASINs to a top ASIN bucket"""
    try:
        data = request.get_json()
        asin_ids = data.get('asin_ids', [])
        bucket_id = data.get('bucket_id')
        
        if not asin_ids or not bucket_id:
            return jsonify({'success': False, 'error': 'ASIN IDs and bucket ID are required'}), 400
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Insert or ignore duplicates
        success_count = 0
        for asin_id in asin_ids:
            try:
                cursor.execute("""
                    INSERT INTO top_asins (asin_id, bucket_id)
                    VALUES (%s, %s)
                """, [asin_id, bucket_id])
                success_count += 1
            except pymysql.IntegrityError:
                # ASIN already in this bucket, skip
                pass
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'allocated_count': success_count,
            'message': f'Successfully allocated {success_count} ASIN(s) to bucket'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/top-asins/remove', methods=['POST'])
@login_required
def remove_asin_from_bucket():
    """API endpoint to remove an ASIN from a top ASIN bucket"""
    try:
        data = request.get_json()
        asin_id = data.get('asin_id')
        bucket_id = data.get('bucket_id')
        
        if not asin_id or not bucket_id:
            return jsonify({'success': False, 'error': 'ASIN ID and bucket ID are required'}), 400
        
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            DELETE FROM top_asins
            WHERE asin_id = %s AND bucket_id = %s
        """, [asin_id, bucket_id])
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'ASIN removed from bucket successfully'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/test-scrape/<asin>')
@login_required
def test_scrape_asin(asin):
    """Test API endpoint to scrape ASIN data from Pangolin and return JSON"""
    api_key = get_pangolin_api_key()
    
    if not api_key:
        return jsonify({
            'success': False,
            'error': 'Pangolin API key not found in config.ini'
        }), 500
    
    # Pangolin API endpoint for Amazon product detail scraping
    # Based on API docs: https://docs.pangolinfo.com/en-api-reference/amazonApi/submit
    pangolin_url = 'https://scrapeapi.pangolinfo.com/api/v1/scrape'
    
    # Construct the Amazon product URL
    amazon_url = f'https://www.amazon.com/dp/{asin}'
    
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    
    payload = {
        'url': amazon_url,
        'parserName': 'amzProductDetail',
        'format': 'json',
        'bizContext': {
            'zipcode': '10041'
        }
    }
    
    try:
        response = requests.post(pangolin_url, json=payload, headers=headers, timeout=90)
        response.raise_for_status()
        
        data = response.json()
        return jsonify({
            'success': True,
            'asin': asin,
            'data': data
        })
        
    except requests.exceptions.RequestException as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'asin': asin
        }), 500

@app.route('/api/scrape-and-save/<asin>')
@login_required
def scrape_and_save_asin(asin):
    """Scrape ASIN data from Pangolin and save to database"""
    api_key = get_pangolin_api_key()
    
    if not api_key:
        return jsonify({
            'success': False,
            'error': 'Pangolin API key not found in config.ini'
        }), 500
    
    # Pangolin API endpoint for Amazon product detail scraping
    # Based on API docs: https://docs.pangolinfo.com/en-api-reference/amazonApi/submit
    pangolin_url = 'https://scrapeapi.pangolinfo.com/api/v1/scrape'
    
    # Construct the Amazon product URL
    amazon_url = f'https://www.amazon.com/dp/{asin}'
    
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    
    payload = {
        'url': amazon_url,
        'parserName': 'amzProductDetail',
        'format': 'json',
        'bizContext': {
            'zipcode': '10041'
        }
    }
    
    try:
        response = requests.post(pangolin_url, json=payload, headers=headers, timeout=90)
        response.raise_for_status()
        
        data = response.json()
        
        # Extract relevant fields from the response
        # Response structure: data.data.json[0].data.results[0] contains product data
        import json as json_lib
        
        product_data = {}
        parent_asin = None
        
        # Navigate the nested structure
        if data.get('code') == 0 and data.get('data'):
            json_array = data.get('data', {}).get('json', [])
            if json_array and len(json_array) > 0:
                results = json_array[0].get('data', {}).get('results', [])
                if results and len(results) > 0:
                    product_data = results[0]
                    parent_asin = product_data.get('parentAsin')
        
        # Update the database with scraped data
        conn = get_connection()
        cursor = conn.cursor()
        
        update_query = """
            UPDATE asin 
            SET 
                title = %s,
                price = %s,
                rating = %s,
                rating_count = %s,
                main_image = %s,
                sales_volume = %s,
                seller = %s,
                shipper = %s,
                merchant_id = %s,
                color = %s,
                size = %s,
                has_buy_box = %s,
                delivery_date = %s,
                coupon = %s,
                parse_json = %s,
                parent_asin = %s,
                amazon_category = %s,
                scraped_at = NOW()
            WHERE asin = %s
        """
        
        # Extract values from the actual Pangolin API response structure
        title = product_data.get('title')
        price_str = product_data.get('price')
        price = None
        if price_str:
            # Try to extract numeric value from price string like "$47.68 with 19 percent savings"
            import re
            price_match = re.search(r'\$?([\d,]+\.?\d*)', str(price_str))
            if price_match:
                try:
                    price = float(price_match.group(1).replace(',', ''))
                except:
                    pass
        
        # Extract rating (star field contains the rating)
        rating_str = product_data.get('star')
        rating = None
        if rating_str:
            try:
                rating = float(rating_str)
            except:
                pass
        
        # Extract rating count from 'rating' field
        rating_count_str = product_data.get('rating')
        rating_count = None
        if rating_count_str:
            try:
                # Remove non-numeric characters except digits
                rating_count = int(re.sub(r'[^\d]', '', str(rating_count_str)))
            except:
                pass
        
        # Extract sales volume from 'sales' field like "400+ bought"
        sales_str = product_data.get('sales')
        sales_volume = None
        if sales_str:
            try:
                sales_match = re.search(r'(\d+)', str(sales_str))
                if sales_match:
                    sales_volume = int(sales_match.group(1))
            except:
                pass
        
        main_image = product_data.get('image')
        seller = product_data.get('seller')
        shipper = product_data.get('shipper')
        merchant_id = product_data.get('merchant_id')
        color = product_data.get('color')
        size = None  # Not in the response
        has_buy_box = 1 if product_data.get('has_cart') else 0
        delivery_date = product_data.get('delivery_time')
        coupon = product_data.get('coupon')
        if coupon == 'null':
            coupon = None
        
        # Extract amazon category from category_name field
        amazon_category = product_data.get('category_name')
        
        # Store the entire response as JSON
        parse_json = json_lib.dumps(data)
        
        cursor.execute(update_query, [
            title, price, rating, rating_count, main_image, sales_volume,
            seller, shipper, merchant_id, color, size, has_buy_box,
            delivery_date, coupon, parse_json, parent_asin, amazon_category, asin
        ])
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'asin': asin,
            'message': 'Data scraped and saved successfully',
            'data': data
        })
        
    except requests.exceptions.RequestException as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'asin': asin
        }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Database error: {str(e)}',
            'asin': asin
        }), 500

@app.route('/brand-scrapped')
@login_required
def brand_scrapped_list():
    """List all brand_scrapped entries with their mapping status"""
    search_query = request.args.get('search', '')
    mapping_filter = request.args.get('mapping', 'all')  # all, mapped, unmapped
    
    conn = get_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    
    query = """
        SELECT 
            bs.id,
            bs.name,
            bs.brand_id,
            bs.created_at,
            b.brand as official_brand_name,
            COUNT(DISTINCT a.id) as asin_count
        FROM brand_scrapped bs
        LEFT JOIN brand b ON bs.brand_id = b.id
        LEFT JOIN asin a ON a.brand_scrapped = bs.name
        WHERE 1=1
    """
    
    params = []
    
    # Apply search filter
    if search_query:
        query += " AND bs.name LIKE %s"
        params.append(f'%{search_query}%')
    
    # Apply mapping filter
    if mapping_filter == 'mapped':
        query += " AND bs.brand_id IS NOT NULL"
    elif mapping_filter == 'unmapped':
        query += " AND bs.brand_id IS NULL"
    
    query += " GROUP BY bs.id, bs.name, bs.brand_id, bs.created_at, b.brand ORDER BY bs.name"
    
    cursor.execute(query, params)
    brand_scrapped = cursor.fetchall()
    
    # Get all brands for the dropdown
    cursor.execute("""
        SELECT id, brand 
        FROM brand 
        ORDER BY brand
    """)
    all_brands = cursor.fetchall()
    
    # Get statistics
    cursor.execute("""
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN brand_id IS NOT NULL THEN 1 ELSE 0 END) as mapped,
            SUM(CASE WHEN brand_id IS NULL THEN 1 ELSE 0 END) as unmapped
        FROM brand_scrapped
    """)
    stats = cursor.fetchone()
    
    cursor.close()
    conn.close()
    
    return render_template('brand_scrapped.html', 
                         brand_scrapped=brand_scrapped,
                         all_brands=all_brands,
                         stats=stats,
                         search_query=search_query,
                         mapping_filter=mapping_filter)

@app.route('/brand-scrapped/update/<int:scrapped_id>', methods=['POST'])
@login_required
def update_brand_scrapped(scrapped_id):
    """Update the brand_id for a brand_scrapped entry"""
    brand_id = request.form.get('brand_id')
    
    # Convert empty string to None
    if brand_id == '' or brand_id == 'null':
        brand_id = None
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE brand_scrapped 
            SET brand_id = %s
            WHERE id = %s
        """, [brand_id, scrapped_id])
        
        conn.commit()
        cursor.close()
        conn.close()
        
        flash('Brand mapping updated successfully!', 'success')
    except Exception as e:
        flash(f'Error updating brand mapping: {str(e)}', 'error')
    
    return redirect(url_for('brand_scrapped_list'))

@app.route('/brand-scrapped/create-brand/<int:scrapped_id>', methods=['POST'])
@login_required
def create_brand_from_scrapped(scrapped_id):
    """Create a new brand from a brand_scrapped entry"""
    try:
        # Get the brand name from the form (allows user to edit it)
        brand_name = request.form.get('new_brand_name', '').strip()
        
        if not brand_name:
            flash('Brand name is required', 'error')
            return redirect(url_for('brand_scrapped_list'))
        
        conn = get_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        
        # Verify the scrapped brand exists
        cursor.execute("SELECT name FROM brand_scrapped WHERE id = %s", [scrapped_id])
        scrapped = cursor.fetchone()
        
        if not scrapped:
            flash('Scrapped brand not found', 'error')
            return redirect(url_for('brand_scrapped_list'))
        
        # Check if brand already exists
        cursor.execute("SELECT id FROM brand WHERE brand = %s", [brand_name])
        existing = cursor.fetchone()
        
        if existing:
            # Brand already exists, just link it
            cursor.execute("""
                UPDATE brand_scrapped 
                SET brand_id = %s
                WHERE id = %s
            """, [existing['id'], scrapped_id])
            conn.commit()
            flash(f'Brand "{brand_name}" already exists. Linked to existing brand.', 'info')
        else:
            # Create new brand
            cursor.execute("""
                INSERT INTO brand (brand, created_at)
                VALUES (%s, NOW())
            """, [brand_name])
            
            new_brand_id = cursor.lastrowid
            
            # Link the brand_scrapped to the new brand
            cursor.execute("""
                UPDATE brand_scrapped 
                SET brand_id = %s
                WHERE id = %s
            """, [new_brand_id, scrapped_id])
            
            conn.commit()
            flash(f'New brand "{brand_name}" created and linked successfully!', 'success')
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        flash(f'Error creating brand: {str(e)}', 'error')
    
    return redirect(url_for('brand_scrapped_list'))

@app.route('/export/brands-csv')
@login_required
def export_brands_csv():
    """Export filtered brands data to CSV"""
    category_id_param = request.args.get('category_id')
    brand_bucket_id = request.args.get('brand_bucket_id', type=int)
    search_term = request.args.get('search', '')
    
    # Handle special "null" value for no category filter
    if category_id_param == 'null':
        category_id = 'null'
    elif category_id_param:
        category_id = int(category_id_param)
    else:
        category_id = None
    
    brands = get_brands(category_id, brand_bucket_id, search_term)
    
    # Create CSV in memory
    output = StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow([
        'Brand',
        'Category',
        'Sub Category',
        'Brand Bucket',
        'LTM Revenue',
        'LTM CM3',
        'LTM EBITDA %',
        'LTM Stock Value',
        'ASIN Count',
        'Store URL'
    ])
    
    # Write data rows
    for brand in brands:
        writer.writerow([
            brand['brand'],
            brand['category'] or '',
            brand['sub_category'] or '',
            brand['brand_bucket_name'] or '',
            f"{brand['ltm_revenues']:.2f}" if brand['ltm_revenues'] else '0',
            f"{brand['ltm_cm3']:.2f}" if brand['ltm_cm3'] else '0',
            f"{brand['ltm_brand_ebitda']:.2f}" if brand['ltm_brand_ebitda'] else '0',
            f"{brand['stock_value']:.2f}" if brand['stock_value'] else '0',
            brand['asin_count'],
            brand['url'] or ''
        ])
    
    # Prepare response
    output.seek(0)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'brands_export_{timestamp}.csv'
    
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename={filename}'}
    )

@app.route('/seasonality')
@login_required
def seasonality_list():
    """List all seasonalities with their factors"""
    conn = get_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    
    query = """
        SELECT 
            s.id,
            s.name,
            s.unit_01, s.unit_02, s.unit_03, s.unit_04, s.unit_05, s.unit_06,
            s.unit_07, s.unit_08, s.unit_09, s.unit_10, s.unit_11, s.unit_12,
            COUNT(DISTINCT a.id) as asin_count,
            COALESCE(SUM(a.ltm_revenues), 0) as total_ltm_revenue
        FROM seasonality s
        LEFT JOIN asin a ON s.name = a.seasonality AND (a.eol IS NULL OR a.eol = 0)
        GROUP BY s.id, s.name, 
                 s.unit_01, s.unit_02, s.unit_03, s.unit_04, s.unit_05, s.unit_06,
                 s.unit_07, s.unit_08, s.unit_09, s.unit_10, s.unit_11, s.unit_12
        ORDER BY total_ltm_revenue DESC, s.name
    """
    
    cursor.execute(query)
    seasonalities = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return render_template('seasonality.html', seasonalities=seasonalities)

@app.route('/api/seasonality-data/<int:seasonality_id>')
@login_required
def get_seasonality_data(seasonality_id):
    """API endpoint to get seasonality factor data for a specific seasonality"""
    conn = get_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    
    query = """
        SELECT 
            id,
            name,
            unit_01, unit_02, unit_03, unit_04, unit_05, unit_06,
            unit_07, unit_08, unit_09, unit_10, unit_11, unit_12
        FROM seasonality
        WHERE id = %s
    """
    
    cursor.execute(query, [seasonality_id])
    seasonality = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if not seasonality:
        return jsonify({'error': 'Seasonality not found'}), 404
    
    # Extract monthly factors
    factors = [
        float(seasonality['unit_01']) if seasonality['unit_01'] else 0,
        float(seasonality['unit_02']) if seasonality['unit_02'] else 0,
        float(seasonality['unit_03']) if seasonality['unit_03'] else 0,
        float(seasonality['unit_04']) if seasonality['unit_04'] else 0,
        float(seasonality['unit_05']) if seasonality['unit_05'] else 0,
        float(seasonality['unit_06']) if seasonality['unit_06'] else 0,
        float(seasonality['unit_07']) if seasonality['unit_07'] else 0,
        float(seasonality['unit_08']) if seasonality['unit_08'] else 0,
        float(seasonality['unit_09']) if seasonality['unit_09'] else 0,
        float(seasonality['unit_10']) if seasonality['unit_10'] else 0,
        float(seasonality['unit_11']) if seasonality['unit_11'] else 0,
        float(seasonality['unit_12']) if seasonality['unit_12'] else 0,
    ]
    
    # Convert to percentages (multiply by 100)
    percentages = [f * 100 for f in factors]
    
    return jsonify({
        'id': seasonality['id'],
        'name': seasonality['name'],
        'months': ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
        'factors': factors,
        'percentages': percentages
    })

@app.route('/comments')
@login_required
def comments_list():
    """List all comments with filtering by entity type"""
    entity_type = request.args.get('entity_type', 'all')
    
    conn = get_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    
    query = """
        SELECT 
            c.id,
            c.entity_type,
            c.entity_id,
            c.text,
            c.author,
            c.created_at,
            CASE 
                WHEN c.entity_type = 'brand' THEN b.brand
                WHEN c.entity_type = 'asin' THEN a.asin
                WHEN c.entity_type = 'brand_bucket' THEN bb.name
                WHEN c.entity_type = 'top_asin_buckets' THEN tab.name
                ELSE NULL
            END as entity_name,
            CASE 
                WHEN c.entity_type = 'brand' THEN b.main_image
                WHEN c.entity_type = 'asin' THEN a.main_image
                WHEN c.entity_type = 'brand_bucket' THEN NULL
                WHEN c.entity_type = 'top_asin_buckets' THEN tab.main_image
                ELSE NULL
            END as entity_main_image,
            CASE 
                WHEN c.entity_type = 'asin' THEN a.asin
                ELSE NULL
            END as asin_code
        FROM comments c
        LEFT JOIN brand b ON c.entity_type = 'brand' AND c.entity_id = b.id
        LEFT JOIN asin a ON c.entity_type = 'asin' AND c.entity_id = a.id
        LEFT JOIN brand_buckets bb ON c.entity_type = 'brand_bucket' AND c.entity_id = bb.id
        LEFT JOIN top_asin_buckets tab ON c.entity_type = 'top_asin_buckets' AND c.entity_id = tab.id
        WHERE 1=1
    """
    
    params = []
    if entity_type != 'all':
        query += " AND c.entity_type = %s"
        params.append(entity_type)
    
    query += " ORDER BY c.created_at DESC"
    
    cursor.execute(query, params)
    comments = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return render_template('comments_list.html', comments=comments, selected_entity_type=entity_type)

@app.route('/api/comments', methods=['GET'])
@login_required
def get_comments():
    """API endpoint to get comments for a specific entity"""
    entity_type = request.args.get('entity_type')
    entity_id = request.args.get('entity_id', type=int)
    count_only = request.args.get('count_only', 'false').lower() == 'true'
    
    if not entity_type or not entity_id:
        return jsonify({'error': 'entity_type and entity_id are required'}), 400
    
    conn = get_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    
    if count_only:
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM comments
            WHERE entity_type = %s AND entity_id = %s
        """, [entity_type, entity_id])
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        return jsonify({'count': result['count'] if result else 0})
    
    cursor.execute("""
        SELECT id, text, author, created_at
        FROM comments
        WHERE entity_type = %s AND entity_id = %s
        ORDER BY created_at DESC
    """, [entity_type, entity_id])
    
    comments = cursor.fetchall()
    cursor.close()
    conn.close()
    
    # Convert datetime to string for JSON serialization
    for comment in comments:
        if comment['created_at']:
            comment['created_at'] = comment['created_at'].strftime('%Y-%m-%d %H:%M:%S')
    
    return jsonify({'comments': comments})

@app.route('/api/comments', methods=['POST'])
@login_required
def create_comment():
    """API endpoint to create a new comment"""
    data = request.get_json()
    entity_type = data.get('entity_type')
    entity_id = data.get('entity_id')
    text = data.get('text', '').strip()
    
    if not entity_type or not entity_id:
        return jsonify({'success': False, 'error': 'entity_type and entity_id are required'}), 400
    
    try:
        entity_id = int(entity_id)
    except (ValueError, TypeError):
        return jsonify({'success': False, 'error': 'entity_id must be a valid integer'}), 400
    
    if not text:
        return jsonify({'success': False, 'error': 'Comment text is required'}), 400
    
    author = session.get('username', 'Unknown')
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO comments (entity_type, entity_id, text, author)
            VALUES (%s, %s, %s, %s)
        """, [entity_type, entity_id, text, author])
        comment_id = cursor.lastrowid
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'comment_id': comment_id,
            'message': 'Comment added successfully'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/comments/<int:comment_id>', methods=['PUT', 'PATCH'])
@login_required
def update_comment(comment_id):
    """API endpoint to update a comment"""
    data = request.get_json()
    text = data.get('text', '').strip()
    
    if not text:
        return jsonify({'success': False, 'error': 'Comment text is required'}), 400
    
    author = session.get('username', 'Unknown')
    
    try:
        conn = get_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        
        # Check if comment exists and user is the author
        cursor.execute("""
            SELECT author FROM comments WHERE id = %s
        """, [comment_id])
        comment = cursor.fetchone()
        
        if not comment:
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'error': 'Comment not found'}), 404
        
        if comment['author'] != author:
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'error': 'You can only edit your own comments'}), 403
        
        # Update the comment
        cursor.execute("""
            UPDATE comments 
            SET text = %s
            WHERE id = %s
        """, [text, comment_id])
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Comment updated successfully'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/comments/<int:comment_id>', methods=['DELETE'])
@login_required
def delete_comment(comment_id):
    """API endpoint to delete a comment"""
    author = session.get('username', 'Unknown')
    
    try:
        conn = get_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        
        # Check if comment exists and user is the author
        cursor.execute("""
            SELECT author FROM comments WHERE id = %s
        """, [comment_id])
        comment = cursor.fetchone()
        
        if not comment:
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'error': 'Comment not found'}), 404
        
        if comment['author'] != author:
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'error': 'You can only delete your own comments'}), 403
        
        cursor.execute("DELETE FROM comments WHERE id = %s", [comment_id])
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Comment deleted successfully'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/export/dashboard-csv')
@login_required
def export_dashboard_csv():
    """Export dashboard data to CSV (Net Revenue, CM3, and Net Units)"""
    brand_id = request.args.get('brand_id')
    category_id = request.args.get('category_id')
    marketplace = request.args.get('marketplace')
    
    conn = get_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    
    # Query Net revenue, CM3, and Net units for 2024 and 2025
    query = """
        SELECT 
            s.metric,
            MONTH(s.month) as month_num,
            YEAR(s.month) as year,
            SUM(s.total_value) as total_value
        FROM financials_summary_monthly_brand s
        WHERE LOWER(s.metric) IN ('net revenue', 'cm3', 'net units')
        AND YEAR(s.month) IN (2024, 2025)
    """
    
    params = []
    
    # Apply filters
    if brand_id:
        query += " AND s.brand_id = %s"
        params.append(brand_id)
    
    if category_id:
        query += " AND s.category_id = %s"
        params.append(category_id)
    
    if marketplace:
        query += " AND s.marketplace = %s"
        params.append(marketplace)
    else:
        query += " AND s.marketplace = 'ALL'"
    
    query += """
        GROUP BY s.metric, YEAR(s.month), MONTH(s.month)
        ORDER BY YEAR(s.month), MONTH(s.month)
    """
    
    cursor.execute(query, params)
    results = cursor.fetchall()
    cursor.close()
    conn.close()
    
    # Organize data by month and metric
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    revenue_2024 = [0] * 12
    revenue_2025 = [0] * 12
    cm3_2024 = [0] * 12
    cm3_2025 = [0] * 12
    units_2024 = [0] * 12
    units_2025 = [0] * 12
    
    for row in results:
        month_idx = row['month_num'] - 1
        metric_name = row['metric'].lower() if row['metric'] else ''
        value = float(row['total_value']) if row['total_value'] else 0
        
        if row['year'] == 2024:
            if metric_name == 'net revenue':
                revenue_2024[month_idx] = value
            elif metric_name == 'cm3':
                cm3_2024[month_idx] = value
            elif metric_name == 'net units':
                units_2024[month_idx] = value
        elif row['year'] == 2025:
            if metric_name == 'net revenue':
                revenue_2025[month_idx] = value
            elif metric_name == 'cm3':
                cm3_2025[month_idx] = value
            elif metric_name == 'net units':
                units_2025[month_idx] = value
    
    # Create CSV in memory
    output = StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow(['Metric', 'Year'] + months)
    
    # Write data rows
    writer.writerow(['Net Revenue', '2024'] + [f"{val:.2f}" for val in revenue_2024])
    writer.writerow(['Net Revenue', '2025'] + [f"{val:.2f}" for val in revenue_2025])
    writer.writerow(['CM3', '2024'] + [f"{val:.2f}" for val in cm3_2024])
    writer.writerow(['CM3', '2025'] + [f"{val:.2f}" for val in cm3_2025])
    writer.writerow(['Net Units', '2024'] + [f"{val:.0f}" for val in units_2024])
    writer.writerow(['Net Units', '2025'] + [f"{val:.0f}" for val in units_2025])
    
    # Calculate EBITDA %
    ebitda_2024 = [(cm3_2024[i] / revenue_2024[i] * 100) if revenue_2024[i] > 0 else 0 for i in range(12)]
    ebitda_2025 = [(cm3_2025[i] / revenue_2025[i] * 100) if revenue_2025[i] > 0 else 0 for i in range(12)]
    
    writer.writerow(['EBITDA %', '2024'] + [f"{val:.2f}" for val in ebitda_2024])
    writer.writerow(['EBITDA %', '2025'] + [f"{val:.2f}" for val in ebitda_2025])
    
    # Prepare response
    output.seek(0)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'dashboard_export_{timestamp}.csv'
    
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename={filename}'}
    )

@app.route('/users')
@login_required
@admin_required
def users_list():
    """List all users"""
    conn = get_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    
    cursor.execute("""
        SELECT id, username, email, is_admin, is_active, created_at, last_login
        FROM users
        ORDER BY created_at DESC
    """)
    users = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return render_template('users_list.html', users=users)

@app.route('/users/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_user():
    """Add a new user"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        email = request.form.get('email', '').strip() or None
        is_admin = request.form.get('is_admin') == '1'
        
        if not username or not password:
            flash('Username and password are required', 'error')
            return render_template('edit_user.html', user=None)
        
        if len(password) < 6:
            flash('Password must be at least 6 characters long', 'error')
            return render_template('edit_user.html', user=None)
        
        user_id = create_user(username, password, email, is_admin)
        
        if user_id:
            flash(f'User "{username}" created successfully!', 'success')
            return redirect(url_for('users_list'))
        else:
            flash(f'Username "{username}" already exists', 'error')
    
    return render_template('edit_user.html', user=None)

@app.route('/users/edit/<int:user_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(user_id):
    """Edit a user"""
    conn = get_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        email = request.form.get('email', '').strip() or None
        is_admin = request.form.get('is_admin') == '1'
        is_active = request.form.get('is_active') == '1'
        
        if not username:
            flash('Username is required', 'error')
            cursor.execute("SELECT * FROM users WHERE id = %s", [user_id])
            user = cursor.fetchone()
            cursor.close()
            conn.close()
            return render_template('edit_user.html', user=user)
        
        # Update user
        if password:
            if len(password) < 6:
                flash('Password must be at least 6 characters long', 'error')
                cursor.execute("SELECT * FROM users WHERE id = %s", [user_id])
                user = cursor.fetchone()
                cursor.close()
                conn.close()
                return render_template('edit_user.html', user=user)
            
            password_hash = generate_password_hash(password, method='pbkdf2:sha256')
            cursor.execute("""
                UPDATE users 
                SET username = %s, password_hash = %s, email = %s, is_admin = %s, is_active = %s
                WHERE id = %s
            """, [username, password_hash, email, is_admin, is_active, user_id])
        else:
            cursor.execute("""
                UPDATE users 
                SET username = %s, email = %s, is_admin = %s, is_active = %s
                WHERE id = %s
            """, [username, email, is_admin, is_active, user_id])
        
        conn.commit()
        cursor.close()
        conn.close()
        
        flash('User updated successfully!', 'success')
        return redirect(url_for('users_list'))
    
    # GET request - show edit form
    cursor.execute("SELECT * FROM users WHERE id = %s", [user_id])
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if not user:
        flash('User not found', 'error')
        return redirect(url_for('users_list'))
    
    return render_template('edit_user.html', user=user)

@app.route('/users/delete/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    """Delete a user"""
    # Prevent deleting yourself
    if user_id == session.get('user_id'):
        flash('You cannot delete your own account', 'error')
        return redirect(url_for('users_list'))
    
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("DELETE FROM users WHERE id = %s", [user_id])
        conn.commit()
        flash('User deleted successfully!', 'success')
    except Exception as e:
        flash(f'Error deleting user: {str(e)}', 'error')
    finally:
        cursor.close()
        conn.close()
    
    return redirect(url_for('users_list'))

# ==================== Search Routes ====================

def get_latest_date():
    """Get the latest reporting_date from the search database"""
    conn = get_postgres_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT MAX(reporting_date) as latest_date FROM amz_search_data WHERE reporting_date IS NOT NULL AND reporting_date != ''")
        result = cur.fetchone()
        return result[0] if result and result[0] else None
    finally:
        cur.close()
        conn.close()

@app.route('/search')
@login_required
def search():
    """Main search page for Amazon search data"""
    return render_template('search.html')

@app.route('/search/browse')
@login_required
def search_browse():
    """Browse all search terms from latest month"""
    page = int(request.args.get('page', 1))
    per_page = 100
    offset = (page - 1) * per_page
    
    # Get latest date
    latest_date = get_latest_date()
    if not latest_date:
        flash('No data found in database', 'error')
        return render_template('search.html')
    
    conn = get_postgres_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        # Get total count
        cur.execute("""
            SELECT COUNT(*) as total
            FROM amz_search_data
            WHERE reporting_date = %s
        """, (latest_date,))
        total = cur.fetchone()['total']
        total_pages = (total + per_page - 1) // per_page
        
        # Get paginated results ordered by search frequency rank (ascending)
        cur.execute("""
            SELECT search_frequency_rank, search_term,
                   top_clicked_brand_1, top_clicked_brands_2, top_clicked_brands_3,
                   top_clicked_product_1_asin, top_clicked_product_2_asin, top_clicked_product_3_asin
            FROM amz_search_data
            WHERE reporting_date = %s
            ORDER BY search_frequency_rank ASC
            LIMIT %s OFFSET %s
        """, (latest_date, per_page, offset))
        
        results = cur.fetchall()
        
        return render_template('search_results.html',
                             results=results,
                             query='',
                             search_type='browse_all',
                             page=page,
                             total_pages=total_pages,
                             total=total,
                             latest_date=latest_date)
    finally:
        cur.close()
        conn.close()

@app.route('/search/query', methods=['GET', 'POST'])
@login_required
def search_query():
    """Handle search requests"""
    if request.method == 'POST':
        search_type = request.form.get('search_type', 'search_term')
        query = request.form.get('query', '').strip()
        page = int(request.form.get('page', 1))
    else:
        search_type = request.args.get('search_type', 'search_term')
        query = request.args.get('query', '').strip()
        page = int(request.args.get('page', 1))
    
    if not query:
        flash('Please enter a search query', 'error')
        return render_template('search.html')
    
    # Get latest date
    latest_date = get_latest_date()
    if not latest_date:
        flash('No data found in database', 'error')
        return render_template('search.html')
    
    per_page = 100
    offset = (page - 1) * per_page
    
    conn = get_postgres_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        # Build query based on search type
        if search_type == 'search_term':
            # LIKE search for search term
            base_query = """
                SELECT search_frequency_rank, search_term, 
                       top_clicked_brand_1, top_clicked_brands_2, top_clicked_brands_3,
                       top_clicked_product_1_asin, top_clicked_product_2_asin, top_clicked_product_3_asin
                FROM amz_search_data
                WHERE reporting_date = %s 
                AND search_term ILIKE %s
                ORDER BY search_frequency_rank ASC
            """
            search_param = f'%{query}%'
        elif search_type == 'brand':
            # Exact match on any of the 3 brand columns
            base_query = """
                SELECT search_frequency_rank, search_term,
                       top_clicked_brand_1, top_clicked_brands_2, top_clicked_brands_3,
                       top_clicked_product_1_asin, top_clicked_product_2_asin, top_clicked_product_3_asin
                FROM amz_search_data
                WHERE reporting_date = %s
                AND (top_clicked_brand_1 = %s OR top_clicked_brands_2 = %s OR top_clicked_brands_3 = %s)
                ORDER BY search_frequency_rank ASC
            """
            search_param = query
        elif search_type == 'asin':
            # Exact match on any of the 3 ASIN columns
            base_query = """
                SELECT search_frequency_rank, search_term,
                       top_clicked_brand_1, top_clicked_brands_2, top_clicked_brands_3,
                       top_clicked_product_1_asin, top_clicked_product_2_asin, top_clicked_product_3_asin
                FROM amz_search_data
                WHERE reporting_date = %s
                AND (top_clicked_product_1_asin = %s OR top_clicked_product_2_asin = %s OR top_clicked_product_3_asin = %s)
                ORDER BY search_frequency_rank ASC
            """
            search_param = query
        else:
            flash('Invalid search type', 'error')
            return render_template('search.html')
        
        # Get total count
        if search_type == 'search_term':
            count_query = """
                SELECT COUNT(*) as total
                FROM amz_search_data
                WHERE reporting_date = %s AND search_term ILIKE %s
            """
            cur.execute(count_query, (latest_date, search_param))
        elif search_type == 'brand':
            count_query = """
                SELECT COUNT(*) as total
                FROM amz_search_data
                WHERE reporting_date = %s
                AND (top_clicked_brand_1 = %s OR top_clicked_brands_2 = %s OR top_clicked_brands_3 = %s)
            """
            cur.execute(count_query, (latest_date, query, query, query))
        else:  # asin
            count_query = """
                SELECT COUNT(*) as total
                FROM amz_search_data
                WHERE reporting_date = %s
                AND (top_clicked_product_1_asin = %s OR top_clicked_product_2_asin = %s OR top_clicked_product_3_asin = %s)
            """
            cur.execute(count_query, (latest_date, query, query, query))
        
        total = cur.fetchone()['total']
        total_pages = (total + per_page - 1) // per_page
        
        # Get paginated results
        if search_type == 'search_term':
            cur.execute(base_query + f" LIMIT {per_page} OFFSET {offset}", (latest_date, search_param))
        elif search_type == 'brand':
            cur.execute(base_query + f" LIMIT {per_page} OFFSET {offset}", (latest_date, query, query, query))
        else:  # asin
            cur.execute(base_query + f" LIMIT {per_page} OFFSET {offset}", (latest_date, query, query, query))
        
        results = cur.fetchall()
        
        return render_template('search_results.html', 
                             results=results, 
                             query=query,
                             search_type=search_type,
                             page=page,
                             total_pages=total_pages,
                             total=total,
                             latest_date=latest_date)
    finally:
        cur.close()
        conn.close()

@app.route('/search/detail/<path:search_term>')
@login_required
def search_detail(search_term):
    """Show detail page with graph for a search term"""
    search_term = unquote(search_term)
    
    conn = get_postgres_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        # Get all data for this search term across all dates
        cur.execute("""
            SELECT reporting_date, search_frequency_rank
            FROM amz_search_data
            WHERE search_term = %s
            AND reporting_date IS NOT NULL 
            AND reporting_date != ''
            ORDER BY reporting_date ASC
        """, (search_term,))
        
        data_points = cur.fetchall()
        
        if not data_points:
            flash(f'No data found for search term: {search_term}', 'error')
            return redirect(url_for('search'))
        
        # Prepare data for Chart.js
        dates = [str(row['reporting_date']) for row in data_points]
        ranks = [row['search_frequency_rank'] for row in data_points]
        
        return render_template('search_detail.html', 
                             search_term=search_term,
                             dates=dates,
                             ranks=ranks)
    finally:
        cur.close()
        conn.close()

if __name__ == '__main__':
    app.run(debug=True, port=5003)

