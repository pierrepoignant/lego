#!/usr/bin/env python3
"""
Streamlit app to explore LEGO database financials
"""

import streamlit as st
import pymysql
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import os
import configparser

# Page configuration
st.set_page_config(
    page_title="LEGO Financial Dashboard",
    page_icon="📊",
    layout="wide"
)

def get_config():
    """Read configuration from config.ini"""
    config = configparser.ConfigParser()
    config_path = os.path.join(os.path.dirname(__file__), 'config.ini')
    config.read(config_path)
    return config

def check_authentication():
    """Check if user is authenticated"""
    config = get_config()
    auth_username = config.get('auth', 'username', fallback='admin')
    auth_password = config.get('auth', 'password', fallback='admin')
    
    # Initialize session state
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    
    # If not authenticated, show login form
    if not st.session_state.authenticated:
        st.title("🔒 Login Required")
        st.markdown("Please enter your credentials to access the LEGO Financial Dashboard")
        
        with st.form("login_form"):
            username = st.text_input("Username", key="username")
            password = st.text_input("Password", type="password", key="password")
            submit = st.form_submit_button("Login")
            
            if submit:
                if username == auth_username and password == auth_password:
                    st.session_state.authenticated = True
                    st.success("✅ Successfully logged in!")
                    st.rerun()
                else:
                    st.error("❌ Invalid username or password")
        
        st.stop()  # Stop execution if not authenticated

def get_connection():
    """Create database connection - don't cache as connections can timeout"""
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

@st.cache_data(ttl=600)
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
    return categories

@st.cache_data(ttl=600)
def get_brands():
    """Get list of all brands ordered by position (ascending), excluding 'stock' group"""
    conn = get_connection()
    cursor = conn.cursor()
    
    query = """
        SELECT b.id, b.brand
        FROM brand b
        WHERE (b.`group` IS NULL OR b.`group` != 'stock')
        ORDER BY b.position ASC, b.brand
    """
    
    cursor.execute(query)
    brands = cursor.fetchall()
    cursor.close()
    # Return only id and brand name
    return [(brand[0], brand[1]) for brand in brands]

@st.cache_data(ttl=600)
def get_metrics():
    """Get list of all available metrics"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT metric FROM financials_summary_monthly_brand ORDER BY metric")
    metrics = [row[0] for row in cursor.fetchall()]
    cursor.close()
    return metrics

@st.cache_data(ttl=3600)  # Cache for 1 hour since marketplaces don't change often
def get_marketplaces():
    """Get list of all marketplaces (alphabetically ordered)"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT marketplace FROM financials_summary_monthly_brand WHERE marketplace != 'ALL' ORDER BY marketplace")
    marketplaces = [row[0] for row in cursor.fetchall()]
    cursor.close()
    return marketplaces

@st.cache_data(ttl=600, hash_funcs={list: lambda x: str(sorted(x))})
def get_financial_data(brand_id, metrics, marketplace=None, category_id=None):
    """Get financial data for selected brand and metrics - v4 using summary tables"""
    # Validate inputs - multiple checks to be safe
    if not metrics:
        return pd.DataFrame()  # Return empty dataframe if no metrics selected
    
    if len(metrics) == 0:
        return pd.DataFrame()
    
    # Filter out any empty strings from metrics
    metrics = [m for m in metrics if m and str(m).strip() != '']
    
    if not metrics or len(metrics) == 0:
        return pd.DataFrame()
    
    conn = get_connection()
    
    if not conn:
        return pd.DataFrame()
    
    # Build query using the optimized summary table
    if brand_id is None:
        # Query for all brands
        query = """
            SELECT 
                s.metric,
                s.month,
                SUM(s.total_value) as total_value
            FROM financials_summary_monthly_brand s
            WHERE s.metric IN ({})
            AND YEAR(s.month) IN (2024, 2025)
        """.format(','.join(['%s'] * len(metrics)))
        
        params = list(metrics)  # Create a new list copy
        
        # Add category filter if specified
        if category_id:
            query += " AND s.category_id = %s"
            params.append(category_id)
    else:
        # Query for specific brand
        query = """
            SELECT 
                s.metric,
                s.month,
                SUM(s.total_value) as total_value
            FROM financials_summary_monthly_brand s
            WHERE s.brand_id = %s
            AND s.metric IN ({})
            AND YEAR(s.month) IN (2024, 2025)
        """.format(','.join(['%s'] * len(metrics)))
        
        params = [brand_id] + metrics
    
    if marketplace:
        query += " AND s.marketplace = %s"
        params.append(marketplace)
    else:
        # If no marketplace specified, use the 'ALL' aggregate
        query += " AND s.marketplace = 'ALL'"
    
    query += """
        GROUP BY s.metric, s.month
        ORDER BY s.metric, s.month
    """
    
    df = pd.read_sql(query, conn, params=params)
    conn.close()
    return df

def create_comparison_chart(df, metrics, brand_name):
    """Create line charts comparing 2024 vs 2025 by month"""
    from plotly.subplots import make_subplots
    
    # Prepare data
    df = df.copy()
    df['year'] = pd.to_datetime(df['month']).dt.year
    df['month_num'] = pd.to_datetime(df['month']).dt.month
    df['month_name'] = pd.to_datetime(df['month']).dt.strftime('%B')
    
    # Month order for x-axis
    month_order = ['January', 'February', 'March', 'April', 'May', 'June', 
                   'July', 'August', 'September', 'October', 'November', 'December']
    
    # Create subplots - one row per metric
    num_metrics = len(metrics)
    fig = make_subplots(
        rows=num_metrics, 
        cols=1,
        subplot_titles=[f'{metric} - 2024 vs 2025' for metric in metrics],
        vertical_spacing=0.15
    )
    
    # Colors
    color_2024 = '#1f77b4'  # Blue
    color_2025 = '#d62728'  # Red
    
    for idx, metric in enumerate(metrics):
        # Case-insensitive metric matching
        metric_data = df[df['metric'].str.lower() == metric.lower()].copy()
        
        if metric_data.empty:
            continue
        
        # Pivot data to get months as rows, years as columns
        pivot_data = metric_data.pivot_table(
            index='month_name', 
            columns='year', 
            values='total_value',
            aggfunc='sum'
        ).reindex(month_order)
        
        # Add 2024 line
        if 2024 in pivot_data.columns:
            fig.add_trace(
                go.Scatter(
                    name='2024',
                    x=pivot_data.index,
                    y=pivot_data[2024],
                    mode='lines+markers',
                    line=dict(color=color_2024, width=3),
                    marker=dict(size=8, color=color_2024),
                    showlegend=(idx == 0),  # Only show legend for first metric
                    hovertemplate='<b>%{x}</b><br>2024: $%{y:,.0f}<extra></extra>'
                ),
                row=idx+1, col=1
            )
        
        # Add 2025 line
        if 2025 in pivot_data.columns:
            fig.add_trace(
                go.Scatter(
                    name='2025',
                    x=pivot_data.index,
                    y=pivot_data[2025],
                    mode='lines+markers',
                    line=dict(color=color_2025, width=3),
                    marker=dict(size=8, color=color_2025),
                    showlegend=(idx == 0),  # Only show legend for first metric
                    hovertemplate='<b>%{x}</b><br>2025: $%{y:,.0f}<extra></extra>'
                ),
                row=idx+1, col=1
            )
        
        # Update y-axis label for this subplot
        fig.update_yaxes(title_text="Value ($)", row=idx+1, col=1)
    
    # Update layout
    height = 500 * num_metrics  # Adjust height based on number of metrics
    fig.update_layout(
        title_text=f'{brand_name} - Monthly Performance Comparison',
        height=height,
        template='plotly_white',
        legend=dict(
            orientation="h",
            yanchor="top",
            y=1.02,
            xanchor="left",
            x=0
        ),
        hovermode='x unified'
    )
    
    # Update all x-axes to show month names at an angle
    fig.update_xaxes(tickangle=-45)
    
    return fig

def calculate_yoy_comparison(df, metrics):
    """Calculate year-over-year comparison statistics
    Compares:
    - 12 months of 2024 (Jan 2024 to Dec 2024)
    - Last 12 months (Nov 2024 to Oct 2025)
    """
    stats = []
    
    for metric in metrics:
        # Case-insensitive metric matching
        metric_data = df[df['metric'].str.lower() == metric.lower()].copy()
        
        if metric_data.empty:
            continue
        
        metric_data['month_date'] = pd.to_datetime(metric_data['month'])
        
        # 12 months of 2024: January 2024 to December 2024
        total_2024 = metric_data[
            (metric_data['month_date'] >= '2024-01-01') & 
            (metric_data['month_date'] <= '2024-12-31')
        ]['total_value'].sum()
        
        # Last 12 months: November 2024 to October 2025
        total_ltm = metric_data[
            (metric_data['month_date'] >= '2024-11-01') & 
            (metric_data['month_date'] <= '2025-10-31')
        ]['total_value'].sum()
        
        # Calculate YoY change
        if total_2024 > 0:
            yoy_change = ((total_ltm - total_2024) / total_2024) * 100
        else:
            yoy_change = 0
        
        stats.append({
            'metric': metric,
            'total_2024': total_2024,
            'total_ltm': total_ltm,
            'difference': total_ltm - total_2024,
            'yoy_change': yoy_change
        })
    
    return pd.DataFrame(stats)

@st.cache_data(ttl=600)
def get_brand_exploration_data():
    """Get comprehensive brand data for exploration page (excluding 'stock' group) - using summary tables"""
    conn = get_connection()
    
    # Build query using the optimized summary table
    query = """
        SELECT 
            b.id,
            b.brand,
            b.url,
            -- Net Revenue 2024
            COALESCE(SUM(CASE 
                WHEN LOWER(s.metric) = 'net revenue'
                AND YEAR(s.month) = 2024 
                THEN s.total_value 
                ELSE 0 
            END), 0) as revenue_2024,
            -- Net Revenue LTM (November 2024 to October 2025)
            COALESCE(SUM(CASE 
                WHEN LOWER(s.metric) = 'net revenue'
                AND s.month >= '2024-11-01'
                AND s.month <= '2025-10-31'
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
            -- CM3 LTM (November 2024 to October 2025)
            COALESCE(SUM(CASE 
                WHEN LOWER(s.metric) = 'cm3'
                AND s.month >= '2024-11-01'
                AND s.month <= '2025-10-31'
                THEN s.total_value 
                ELSE 0 
            END), 0) as cm3_ltm
        FROM brand b
        LEFT JOIN financials_summary_monthly_brand s 
            ON b.id = s.brand_id 
            AND s.marketplace = 'ALL'
        WHERE (b.`group` IS NULL OR b.`group` != 'stock')
        GROUP BY b.id, b.brand, b.url
        ORDER BY revenue_ltm DESC
    """
    
    df = pd.read_sql(query, conn)
    conn.close()
    
    # Calculate derived metrics
    df['yoy_growth'] = df.apply(
        lambda row: ((row['revenue_ltm'] - row['revenue_2024']) / row['revenue_2024'] * 100) 
        if row['revenue_2024'] > 0 else 0, 
        axis=1
    )
    
    df['ebitda_2024'] = df.apply(
        lambda row: (row['cm3_2024'] / row['revenue_2024'] * 100) 
        if row['revenue_2024'] > 0 else 0, 
        axis=1
    )
    
    df['ebitda_ltm'] = df.apply(
        lambda row: (row['cm3_ltm'] / row['revenue_ltm'] * 100) 
        if row['revenue_ltm'] > 0 else 0, 
        axis=1
    )
    
    return df

@st.cache_data(ttl=600)
def get_category_exploration_data():
    """Get comprehensive category data for exploration page (excluding 'stock' group) - using summary tables"""
    conn = get_connection()
    
    # Build query using the optimized category summary table
    query = """
        SELECT 
            s.category_id as id,
            c.category,
            -- Net Revenue 2024
            COALESCE(SUM(CASE 
                WHEN LOWER(s.metric) = 'net revenue'
                AND YEAR(s.month) = 2024 
                THEN s.total_value 
                ELSE 0 
            END), 0) as revenue_2024,
            -- Net Revenue LTM (November 2024 to October 2025)
            COALESCE(SUM(CASE 
                WHEN LOWER(s.metric) = 'net revenue'
                AND s.month >= '2024-11-01'
                AND s.month <= '2025-10-31'
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
            -- CM3 LTM (November 2024 to October 2025)
            COALESCE(SUM(CASE 
                WHEN LOWER(s.metric) = 'cm3'
                AND s.month >= '2024-11-01'
                AND s.month <= '2025-10-31'
                THEN s.total_value 
                ELSE 0 
            END), 0) as cm3_ltm,
            -- Count of brands in this category
            MAX(s.brand_count) as brand_count
        FROM financials_summary_monthly_category s
        INNER JOIN category c ON s.category_id = c.id
        GROUP BY s.category_id, c.category
        ORDER BY revenue_ltm DESC
    """
    
    df = pd.read_sql(query, conn)
    conn.close()
    
    # Calculate derived metrics
    df['yoy_growth'] = df.apply(
        lambda row: ((row['revenue_ltm'] - row['revenue_2024']) / row['revenue_2024'] * 100) 
        if row['revenue_2024'] > 0 else 0, 
        axis=1
    )
    
    df['ebitda_2024'] = df.apply(
        lambda row: (row['cm3_2024'] / row['revenue_2024'] * 100) 
        if row['revenue_2024'] > 0 else 0, 
        axis=1
    )
    
    df['ebitda_ltm'] = df.apply(
        lambda row: (row['cm3_ltm'] / row['revenue_ltm'] * 100) 
        if row['revenue_ltm'] > 0 else 0, 
        axis=1
    )
    
    return df

# Check authentication before showing the app
check_authentication()

# Custom CSS for brand colors with white background
st.markdown("""
<style>
    /* Force white background for main content */
    .main {
        background-color: white !important;
    }
    
    .stApp {
        background-color: white !important;
    }
    
    [data-testid="stAppViewContainer"] {
        background-color: white !important;
    }
    
    /* Primary buttons and interactive elements */
    .stButton>button {
        background: linear-gradient(135deg, #5570ED 0%, #FF79E2 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        font-weight: 600;
        transition: all 0.2s ease;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 15px rgba(255, 121, 226, 0.4);
    }
    
    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #04122C 0%, #5570ED 100%);
    }
    [data-testid="stSidebar"] .stMarkdown {
        color: white;
    }
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] span,
    [data-testid="stSidebar"] div {
        color: white !important;
    }
    [data-testid="stSidebar"] .stSelectbox label,
    [data-testid="stSidebar"] .stMultiselect label {
        color: white !important;
        font-weight: 600;
    }
    
    /* Radio buttons */
    .stRadio > label {
        color: #5570ED;
        font-weight: 600;
    }
    
    /* Selectbox */
    .stSelectbox label {
        color: #5570ED;
        font-weight: 600;
    }
    
    /* Headers */
    h1, h2, h3 {
        color: #04122C;
    }
    
    /* Metric values */
    [data-testid="stMetricValue"] {
        color: #5570ED;
    }
    
    /* Links */
    a {
        color: #5570ED;
    }
    a:hover {
        color: #FF79E2;
    }
    
    /* Text color for visibility */
    .stMarkdown, p, span, label {
        color: #04122C;
    }
</style>
""", unsafe_allow_html=True)

# Main app
st.title("📊 LEGO Financial Dashboard")

# Quick navigation buttons at the top
st.markdown("### Quick Navigation")
col1, col2, col3 = st.columns(3)

if 'selected_page' not in st.session_state:
    st.session_state.selected_page = "Performance Comparison"

with col1:
    button_type = "primary" if st.session_state.selected_page == "Performance Comparison" else "secondary"
    if st.button("📈 Performance Comparison", use_container_width=True, type=button_type, key="nav_perf"):
        st.session_state.selected_page = "Performance Comparison"
        st.rerun()

with col2:
    button_type = "primary" if st.session_state.selected_page == "Brand Exploration" else "secondary"
    if st.button("🏢 Brand Exploration", use_container_width=True, type=button_type, key="nav_brand"):
        st.session_state.selected_page = "Brand Exploration"
        st.rerun()

with col3:
    button_type = "primary" if st.session_state.selected_page == "Category Exploration" else "secondary"
    if st.button("📦 Category Exploration", use_container_width=True, type=button_type, key="nav_cat"):
        st.session_state.selected_page = "Category Exploration"
        st.rerun()

# Set page from session state
page = st.session_state.selected_page

st.markdown("---")

# Sidebar for filters
st.sidebar.header("Filters")

# Logout button
if st.sidebar.button("🚪 Logout", help="Logout and clear session"):
    st.session_state.authenticated = False
    st.rerun()

# Cache clear button
if st.sidebar.button("🔄 Clear Cache", help="Clear cached data and refresh"):
    st.cache_data.clear()
    st.sidebar.success("Cache cleared! Refreshing...")
    st.rerun()

# Brand selection - only for Performance Comparison
if page == "Performance Comparison":
    brands = get_brands()
    brand_dict = {brand[1]: brand[0] for brand in brands}
    brand_names = ["All Brands"] + list(brand_dict.keys())

    selected_brand_name = st.sidebar.selectbox(
        "Select Brand (ordered by position)",
        options=brand_names,
        index=0
    )
    selected_brand_id = None if selected_brand_name == "All Brands" else brand_dict[selected_brand_name]

    # Category selection (optional)
    categories = get_categories()
    category_dict = {cat[1]: cat[0] for cat in categories}
    category_filter = st.sidebar.selectbox(
        "Filter by Category (Optional)",
        options=["All Categories"] + list(category_dict.keys()),
        index=0
    )
    category_value = None if category_filter == "All Categories" else category_dict[category_filter]

    # Marketplace selection (optional)
    marketplaces = get_marketplaces()
    marketplace_filter = st.sidebar.selectbox(
        "Filter by Marketplace (Optional)",
        options=["All"] + marketplaces,
        index=0
    )
    marketplace_value = None if marketplace_filter == "All" else marketplace_filter

    # Metric selection
    available_metrics = get_metrics()

    # Set "Net revenue" as default if available, otherwise use first metric
    default_metric = []
    if available_metrics:
        # Try both "Net revenue" and "Net Revenue" (case variations)
        if "Net revenue" in available_metrics:
            default_metric = ["Net revenue"]
        elif "Net Revenue" in available_metrics:
            default_metric = ["Net Revenue"]
        elif available_metrics[0]:
            default_metric = [available_metrics[0]]

    selected_metrics = st.sidebar.multiselect(
        "Select Metrics (1-2)",
        options=available_metrics,
        default=default_metric,
        max_selections=2
    )

    # Filter out any None or empty values
    selected_metrics = [m for m in selected_metrics if m and str(m).strip()]

    # Safety check - if selected_metrics is empty after filtering, don't proceed
    if not selected_metrics and default_metric:
        selected_metrics = default_metric

# Main content
if page == "Performance Comparison":
    st.markdown("### Explore brand performance metrics comparing 2024 vs 2025")
    
    if not selected_metrics or len(selected_metrics) == 0:
        st.info("👈 Please select at least one metric from the sidebar to view the chart.")
    elif any(not m or str(m).strip() == '' for m in selected_metrics):
        st.warning("⚠️ Invalid metric selected. Please choose a valid metric from the sidebar.")
    else:
        # Get data
        with st.spinner("Loading data..."):
            try:
                df = get_financial_data(selected_brand_id, selected_metrics, marketplace_value, category_value)
            except Exception as e:
                st.error(f"Error loading data: {e}")
                df = pd.DataFrame()
        
        if not df.empty:
            # Display chart
            fig = create_comparison_chart(df, selected_metrics, selected_brand_name)
            st.plotly_chart(fig, use_container_width=True)
            
            # Year-over-year comparison statistics
            st.subheader("📈 Year-over-Year Comparison")
            
            stats_df = calculate_yoy_comparison(df, selected_metrics)
            
            if not stats_df.empty:
                # Display metrics in columns
                cols = st.columns(len(selected_metrics))
                
                for idx, row in stats_df.iterrows():
                    with cols[idx]:
                        ltm_k = row['total_ltm'] / 1000
                        st.metric(
                            label=row['metric'],
                            value=f"${ltm_k:,.1f}K" if row['total_ltm'] >= 0 else f"-${abs(ltm_k):,.1f}K",
                            delta=f"{row['yoy_change']:.1f}% vs 2024"
                        )
                        st.caption(f"2024 (Jan-Dec): ${row['total_2024'] / 1000:,.1f}K")
                        st.caption(f"LTM (Nov 24-Oct 25): ${row['total_ltm'] / 1000:,.1f}K")
                        st.caption(f"Difference: ${row['difference'] / 1000:,.1f}K")
            
            # Detailed data table
            with st.expander("📋 View Detailed Data by Month"):
                # Restructure data to have months in rows, metrics in columns
                pivot_df = df.copy()
                pivot_df['year'] = pd.to_datetime(pivot_df['month']).dt.year
                pivot_df['month_name'] = pd.to_datetime(pivot_df['month']).dt.strftime('%B')
                
                # Create a comprehensive table with months in rows
                month_order = ['January', 'February', 'March', 'April', 'May', 'June', 
                              'July', 'August', 'September', 'October', 'November', 'December']
                
                # Initialize results dictionary
                table_data = []
                
                for month in month_order:
                    row_data = {'Month': month}
                    
                    for metric in selected_metrics:
                        # Get 2024 value (case-insensitive)
                        val_2024 = pivot_df[
                            (pivot_df['metric'].str.lower() == metric.lower()) & 
                            (pivot_df['month_name'] == month) & 
                            (pivot_df['year'] == 2024)
                        ]['total_value'].sum()
                        
                        # Get 2025 value (case-insensitive)
                        val_2025 = pivot_df[
                            (pivot_df['metric'].str.lower() == metric.lower()) & 
                            (pivot_df['month_name'] == month) & 
                            (pivot_df['year'] == 2025)
                        ]['total_value'].sum()
                        
                        # Calculate YoY
                        if val_2024 > 0:
                            yoy = ((val_2025 - val_2024) / val_2024) * 100
                        else:
                            yoy = 0 if val_2025 == 0 else float('inf')
                        
                        # Add to row (convert to thousands)
                        row_data[f'{metric} 2024 (K)'] = val_2024 / 1000
                        row_data[f'{metric} 2025 (K)'] = val_2025 / 1000
                        row_data[f'{metric} YoY %'] = yoy
                    
                    table_data.append(row_data)
                
                # Convert to DataFrame
                result_df = pd.DataFrame(table_data)
                
                # Format the dataframe for display
                format_dict = {'Month': '{}'}
                for metric in selected_metrics:
                    format_dict[f'{metric} 2024 (K)'] = '${:,.1f}'
                    format_dict[f'{metric} 2025 (K)'] = '${:,.1f}'
                    format_dict[f'{metric} YoY %'] = '{:.1f}%'
                
                # Apply styling with conditional formatting for YoY
                def highlight_yoy(val):
                    if isinstance(val, (int, float)):
                        if val > 0:
                            return 'color: green'
                        elif val < 0:
                            return 'color: red'
                    return ''
                
                # Style the dataframe
                styled_df = result_df.style.format(format_dict)
                
                # Apply color to YoY columns
                for metric in selected_metrics:
                    styled_df = styled_df.applymap(
                        highlight_yoy, 
                        subset=[f'{metric} YoY %']
                    )
                
                st.dataframe(styled_df, use_container_width=True, height=500)
        else:
            st.warning(f"No data available for {selected_brand_name} with selected filters.")

elif page == "Brand Exploration":
    st.markdown("### Comprehensive brand performance analysis")
    
    with st.spinner("Loading brand exploration data..."):
        try:
            exploration_df = get_brand_exploration_data()
        except Exception as e:
            st.error(f"Error loading data: {e}")
            exploration_df = pd.DataFrame()
    
    if not exploration_df.empty:
        # Summary statistics
        st.subheader("📊 Portfolio Overview")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Total Brands",
                len(exploration_df)
            )
        
        with col2:
            st.metric(
                "Total Revenue 2024 (K)",
                f"${exploration_df['revenue_2024'].sum() / 1000:,.1f}"
            )
        
        with col3:
            st.metric(
                "Total Revenue LTM (K)",
                f"${exploration_df['revenue_ltm'].sum() / 1000:,.1f}"
            )
        
        with col4:
            avg_yoy = exploration_df['yoy_growth'].mean()
            st.metric(
                "Avg YoY Growth",
                f"{avg_yoy:.1f}%"
            )
        
        st.markdown("---")
        
        # Main table
        st.subheader("🏢 Brand Performance Table")
        
        # Select columns to display
        display_df = exploration_df[[
            'brand',
            'url',
            'revenue_2024',
            'revenue_ltm',
            'yoy_growth',
            'ebitda_2024',
            'ebitda_ltm'
        ]].copy()
        
        # Rename columns for better display
        display_df.columns = [
            'Brand',
            'Store URL',
            'Revenue 2024',
            'Revenue LTM',
            'YoY Growth %',
            'Brand EBITDA 2024 %',
            'Brand EBITDA LTM %'
        ]
        
        # Format revenues in thousands for better readability with thousands separators
        display_df['Revenue 2024 (K)'] = display_df['Revenue 2024'].apply(lambda x: f"${x/1000:,.1f}")
        display_df['Revenue LTM (K)'] = display_df['Revenue LTM'].apply(lambda x: f"${x/1000:,.1f}")
        display_df = display_df.drop(columns=['Revenue 2024', 'Revenue LTM'])
        
        # Reorder columns
        display_df = display_df[['Brand', 'Store URL', 'Revenue 2024 (K)', 'Revenue LTM (K)', 
                                 'YoY Growth %', 'Brand EBITDA 2024 %', 'Brand EBITDA LTM %']]
        
        # Configure columns - make URL clickable as a link column
        column_config = {
            "Store URL": st.column_config.LinkColumn(
                "🔗",
                help="Click to open brand store in new tab",
                display_text="🔗",
                width="small"
            ),
            "Revenue 2024 (K)": st.column_config.TextColumn(
                "Revenue 2024 (K)",
                help="Revenue in thousands of dollars"
            ),
            "Revenue LTM (K)": st.column_config.TextColumn(
                "Revenue LTM (K)",
                help="Revenue in thousands of dollars"
            ),
            "YoY Growth %": st.column_config.NumberColumn(
                "YoY Growth %",
                format="%.1f%%"
            ),
            "Brand EBITDA 2024 %": st.column_config.NumberColumn(
                "Brand EBITDA 2024 %",
                format="%.1f%%"
            ),
            "Brand EBITDA LTM %": st.column_config.NumberColumn(
                "Brand EBITDA LTM %",
                format="%.1f%%"
            )
        }
        
        st.dataframe(
            display_df, 
            use_container_width=True, 
            height=600,
            column_config=column_config,
            hide_index=True
        )
        
        # Download button
        csv = display_df.to_csv(index=False)
        st.download_button(
            label="📥 Download Brand Data as CSV",
            data=csv,
            file_name="brand_exploration.csv",
            mime="text/csv"
        )
    else:
        st.warning("No brand data available for the selected filters.")

elif page == "Category Exploration":
    st.markdown("### Comprehensive category performance analysis")
    
    with st.spinner("Loading category exploration data..."):
        try:
            category_df = get_category_exploration_data()
        except Exception as e:
            st.error(f"Error loading data: {e}")
            category_df = pd.DataFrame()
    
    if not category_df.empty:
        # Summary statistics
        st.subheader("📊 Portfolio Overview")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Total Categories",
                len(category_df)
            )
        
        with col2:
            st.metric(
                "Total Revenue 2024 (K)",
                f"${category_df['revenue_2024'].sum() / 1000:,.1f}"
            )
        
        with col3:
            st.metric(
                "Total Revenue LTM (K)",
                f"${category_df['revenue_ltm'].sum() / 1000:,.1f}"
            )
        
        with col4:
            avg_yoy = category_df['yoy_growth'].mean()
            st.metric(
                "Avg YoY Growth",
                f"{avg_yoy:.1f}%"
            )
        
        st.markdown("---")
        
        # Main table
        st.subheader("📦 Category Performance Table")
        
        # Select columns to display
        display_df = category_df[[
            'category',
            'brand_count',
            'revenue_2024',
            'revenue_ltm',
            'yoy_growth',
            'ebitda_2024',
            'ebitda_ltm'
        ]].copy()
        
        # Rename columns for better display
        display_df.columns = [
            'Category',
            'Brand Count',
            'Revenue 2024',
            'Revenue LTM',
            'YoY Growth %',
            'Category EBITDA 2024 %',
            'Category EBITDA LTM %'
        ]
        
        # Format revenues in thousands for better readability with thousands separators
        display_df['Revenue 2024 (K)'] = display_df['Revenue 2024'].apply(lambda x: f"${x/1000:,.1f}")
        display_df['Revenue LTM (K)'] = display_df['Revenue LTM'].apply(lambda x: f"${x/1000:,.1f}")
        display_df = display_df.drop(columns=['Revenue 2024', 'Revenue LTM'])
        
        # Reorder columns
        display_df = display_df[['Category', 'Brand Count', 'Revenue 2024 (K)', 'Revenue LTM (K)', 
                                 'YoY Growth %', 'Category EBITDA 2024 %', 'Category EBITDA LTM %']]
        
        # Configure columns
        column_config = {
            "Brand Count": st.column_config.NumberColumn(
                "Brand Count",
                help="Number of brands in this category",
                format="%d"
            ),
            "Revenue 2024 (K)": st.column_config.TextColumn(
                "Revenue 2024 (K)",
                help="Revenue in thousands of dollars"
            ),
            "Revenue LTM (K)": st.column_config.TextColumn(
                "Revenue LTM (K)",
                help="Revenue in thousands of dollars"
            ),
            "YoY Growth %": st.column_config.NumberColumn(
                "YoY Growth %",
                format="%.1f%%"
            ),
            "Category EBITDA 2024 %": st.column_config.NumberColumn(
                "Category EBITDA 2024 %",
                format="%.1f%%"
            ),
            "Category EBITDA LTM %": st.column_config.NumberColumn(
                "Category EBITDA LTM %",
                format="%.1f%%"
            )
        }
        
        st.dataframe(
            display_df, 
            use_container_width=True, 
            height=600,
            column_config=column_config,
            hide_index=True
        )
        
        # Download button
        csv = display_df.to_csv(index=False)
        st.download_button(
            label="📥 Download Category Data as CSV",
            data=csv,
            file_name="category_exploration.csv",
            mime="text/csv"
        )
    else:
        st.warning("No category data available for the selected filters.")

# Footer
st.sidebar.markdown("---")
st.sidebar.markdown("### Database Info")
try:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM brand")
    brand_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM asin")
    asin_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM financials")
    financial_count = cursor.fetchone()[0]
    cursor.close()
    
    st.sidebar.text(f"Brands: {brand_count}")
    st.sidebar.text(f"Products: {asin_count:,}")
    st.sidebar.text(f"Records: {financial_count:,}")
except Exception as e:
    st.sidebar.error(f"Database error: {e}")

