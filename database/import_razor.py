#!/usr/bin/env python3
"""
Module to import data from razor.csv into the database
Razor CSV format:
- Column 1: Asin => asin
- Column 2: Brand Name => brand
- Column 3: Marketplace
- Then financial data columns similar to infinite.csv
"""

import csv
from datetime import datetime
from db_utils import get_or_create_brand, get_or_create_asin

def parse_month(month_str):
    """Parse month string like 'Jan 24' or 'Jan-24' to date format"""
    try:
        # Try different formats
        for fmt in ['%b %y', '%b-%y', '%b %Y', '%b-%Y']:
            try:
                return datetime.strptime(month_str.strip(), fmt).date().replace(day=1)
            except:
                continue
        return None
    except:
        return None

def clean_value(value_str):
    """Clean financial value string and convert to decimal"""
    if not value_str or value_str.strip() in ['', '-', ' - ', '   ', '–']:
        return None
    # Remove spaces, dollar signs, parentheses (for negative values), and convert
    cleaned = value_str.replace(' ', '').replace('$', '').replace(',', '')
    
    # Handle parentheses for negative values
    if cleaned.startswith('(') and cleaned.endswith(')'):
        cleaned = '-' + cleaned[1:-1]
    
    try:
        return float(cleaned)
    except:
        return None

def import_razor_csv(connection, csv_file='razor.csv'):
    """Load data from razor.csv file into database"""
    cursor = connection.cursor()
    
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.reader(f, delimiter=';')
        
        # Read first two lines (headers)
        line1 = next(reader)  # Metrics
        line2 = next(reader)  # ASIN, Brand Name, Marketplace + Months
        
        # Razor CSV structure:
        # Column 0: ASIN
        # Column 1: Brand Name
        # Column 2: Marketplace
        # Column 3: Empty (separator)
        # Columns 4+: Financial data
        
        asin_col = 0
        brand_col = 1
        marketplace_col = 2
        financial_start_col = 4  # After the empty separator column
        
        # Parse financial columns (metrics and months)
        financial_columns = []
        current_metric = None
        for i in range(financial_start_col, len(line1)):
            if line1[i].strip():
                current_metric = line1[i].strip()
            month_str = line2[i].strip()
            if month_str and month_str != '':
                month_date = parse_month(month_str)
                if month_date:
                    financial_columns.append({
                        'index': i,
                        'metric': current_metric,
                        'month': month_date
                    })
        
        print(f"✓ Found {len(financial_columns)} financial data columns")
        
        # Process data rows
        row_count = 0
        financial_count = 0
        
        for row in reader:
            if not row or len(row) <= asin_col:
                continue
                
            asin_value = row[asin_col].strip()
            if not asin_value:
                continue
                
            brand_name = row[brand_col].strip() if len(row) > brand_col else ''
            marketplace = row[marketplace_col].strip() if len(row) > marketplace_col else ''
            
            # Get or create brand
            brand_id = get_or_create_brand(cursor, brand_name, group='razor')
            
            # Get or create asin (use asin as both asin and product_id)
            asin_id = get_or_create_asin(cursor, asin_value, asin_value, brand_id, '')
            
            # Insert financial data
            for col_info in financial_columns:
                col_idx = col_info['index']
                if col_idx < len(row):
                    value = clean_value(row[col_idx])
                    if value is not None:
                        cursor.execute(
                            """INSERT INTO financials 
                               (asin_id, marketplace, metric, month, value) 
                               VALUES (%s, %s, %s, %s, %s)""",
                            (asin_id, marketplace, col_info['metric'], 
                             col_info['month'], value)
                        )
                        financial_count += 1
            
            row_count += 1
            if row_count % 100 == 0:
                connection.commit()
                print(f"  Processed {row_count} rows, {financial_count} financial records...")
        
        connection.commit()
        print(f"✓ Loaded {row_count} products with {financial_count} financial records")
    
    cursor.close()
    return row_count, financial_count

