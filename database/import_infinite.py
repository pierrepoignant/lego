#!/usr/bin/env python3
"""
Module to import data from infinite.csv into the database
"""

import csv
from datetime import datetime
from db_utils import get_or_create_brand, get_or_create_asin

def parse_month(month_str):
    """Parse month string like 'Jan-24' to date format"""
    try:
        return datetime.strptime(month_str, '%b-%y').date().replace(day=1)
    except:
        return None

def clean_value(value_str):
    """Clean financial value string and convert to decimal"""
    if not value_str or value_str.strip() in ['', '-', ' - ', '   ']:
        return None
    # Remove spaces, dollar signs, and convert
    cleaned = value_str.replace(' ', '').replace('$', '').replace(',', '')
    try:
        return float(cleaned)
    except:
        return None

def import_infinite_csv(connection, csv_file='infinite.csv'):
    """Load data from infinite.csv file into database"""
    cursor = connection.cursor()
    
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.reader(f, delimiter=';')
        
        # Read first two lines (headers)
        line1 = next(reader)  # Metrics
        line2 = next(reader)  # Product ID, Brand, MP, Status + Months
        
        # Find where actual data columns start (after blank cells)
        data_start = 0
        for i, cell in enumerate(line2):
            if cell.strip():
                data_start = i
                break
        
        # Extract column headers
        product_id_col = data_start
        brand_col = data_start + 1
        mp_col = data_start + 2
        status_col = data_start + 3
        financial_start_col = data_start + 4
        
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
            if not row or len(row) <= product_id_col:
                continue
                
            product_id = row[product_id_col].strip()
            if not product_id:
                continue
                
            brand_name = row[brand_col].strip() if len(row) > brand_col else ''
            marketplace = row[mp_col].strip() if len(row) > mp_col else ''
            status = row[status_col].strip() if len(row) > status_col else ''
            
            # Get or create brand
            brand_id = get_or_create_brand(cursor, brand_name, group='infinite')
            
            # Generate asin from product_id (or use product_id as asin for now)
            asin_value = f"ASIN-{product_id}"
            
            # Get or create asin
            asin_id = get_or_create_asin(cursor, asin_value, product_id, brand_id, status)
            
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

