# Top ASIN Feature

This document describes the Top ASIN feature that allows you to organize and categorize your most important ASINs into buckets for better management and analysis.

## Overview

The Top ASIN feature introduces the concept of "Top ASIN Buckets" - a way to group and categorize important ASINs. This is useful for:

- Tracking high-priority products
- Organizing ASINs by strategic importance
- Creating custom categories for analysis
- Identifying key products across brands

## Database Schema

### Tables Created

1. **`top_asin_buckets`** - Stores bucket definitions
   - `id` (INT, PRIMARY KEY, AUTO_INCREMENT)
   - `name` (VARCHAR(255), UNIQUE) - Bucket name
   - `description` (VARCHAR(512), NULLABLE) - Optional description
   - `color` (VARCHAR(7), DEFAULT '#667eea') - Color code for visual identification
   - `created_at` (TIMESTAMP) - Creation timestamp

2. **`top_asins`** - Links ASINs to buckets
   - `id` (INT, PRIMARY KEY, AUTO_INCREMENT)
   - `asin_id` (INT, FOREIGN KEY → asin.id) - Reference to ASIN
   - `bucket_id` (INT, FOREIGN KEY → top_asin_buckets.id) - Reference to bucket
   - `created_at` (TIMESTAMP) - Creation timestamp
   - UNIQUE constraint on `(asin_id, bucket_id)` - Prevents duplicates
   - CASCADE delete on both foreign keys

## Installation

### Step 1: Run Database Migration

Run the migration script to create the required tables:

```bash
cd /Users/pierrepoignant/Coding/lego
python3 database/apply_top_asin_migration.py
```

Or manually execute the SQL:

```bash
mysql -h 127.0.0.1 -u root -p lego < database/create_top_asin_tables.sql
```

### Step 2: Restart Flask Application

If the Flask app is running, restart it to load the updated routes:

```bash
# Stop the current Flask app (Ctrl+C if running in terminal)
# Then restart:
python3 flask_app.py
```

## Features

### 1. Top ASINs Page (`/top-asins`)

#### New Functionality:
- **Checkbox Selection**: Each ASIN row now has a checkbox for selection
- **Select All**: Checkbox in the header to select/deselect all ASINs on the page
- **Bulk Actions Bar**: Shows the number of selected ASINs
- **Allocate Button**: Becomes enabled when one or more ASINs are selected
- **Bucket Badges**: ASINs already in buckets display colored badges below the ASIN code

#### Usage:
1. Navigate to http://127.0.0.1:5003/top-asins
2. Select one or more ASINs using checkboxes
3. Click "Allocate to Top ASIN Bucket" button
4. A modal popup appears with two options:
   - Select an existing bucket from dropdown
   - Create a new bucket by selecting "+ Create New Bucket"

### 2. Create New Bucket

When creating a new bucket in the modal:
1. Select "+ Create New Bucket" from the dropdown
2. Fill in the bucket details:
   - **Name** (required): Unique identifier for the bucket
   - **Description** (optional): Additional context about the bucket
   - **Color**: Visual color code (color picker)
3. Click "Allocate ASINs"
4. The bucket is created and selected ASINs are automatically allocated

### 3. ASIN Detail Page (`/asin/<asin_code>`)

The ASIN detail page now displays bucket information:
- **Location**: Directly below the ASIN number in the product header
- **Display**: Colored badges showing all buckets this ASIN belongs to
- **Styling**: Matches the color scheme defined for each bucket

## API Endpoints

### Create Top ASIN Bucket
```
POST /api/top-asin-buckets/create
Content-Type: application/json

{
  "name": "High Priority",
  "description": "Top performing ASINs",
  "color": "#667eea"
}

Response:
{
  "success": true,
  "bucket_id": 1,
  "name": "High Priority",
  "message": "Bucket created successfully"
}
```

### Allocate ASINs to Bucket
```
POST /api/top-asins/allocate
Content-Type: application/json

{
  "asin_ids": [123, 456, 789],
  "bucket_id": 1
}

Response:
{
  "success": true,
  "allocated_count": 3,
  "message": "Successfully allocated 3 ASIN(s) to bucket"
}
```

### Remove ASIN from Bucket
```
POST /api/top-asins/remove
Content-Type: application/json

{
  "asin_id": 123,
  "bucket_id": 1
}

Response:
{
  "success": true,
  "message": "ASIN removed from bucket successfully"
}
```

## User Interface Components

### Top ASINs Page Updates

**Bulk Actions Bar:**
- Checkbox for "Select All"
- Counter showing number of selected ASINs
- "Allocate to Top ASIN Bucket" button (disabled when no selection)

**Table Updates:**
- New checkbox column (first column)
- Bucket badges display below ASIN code (when applicable)

**Modal Popup:**
- Dropdown to select existing bucket or create new
- Dynamic form for creating new buckets
- Color picker for bucket visualization
- Validation for required fields

### ASIN Detail Page Updates

**Bucket Display:**
- Shows immediately below ASIN number
- Label: "Top ASIN Buckets:"
- Colored badges for each bucket
- Responsive layout

## Design Decisions

1. **Many-to-Many Relationship**: An ASIN can belong to multiple buckets
2. **Cascade Deletion**: Deleting a bucket removes all its ASIN associations
3. **Unique Constraint**: Prevents duplicate ASIN-bucket pairs
4. **Color Coding**: Visual identification makes buckets easy to distinguish
5. **Modal Interface**: Non-intrusive UI for bucket selection/creation
6. **Batch Operations**: Multiple ASINs can be allocated at once

## Future Enhancements

Potential improvements for consideration:

1. **Bucket Analytics**: Dashboard showing metrics aggregated by bucket
2. **Export Functionality**: Export ASINs by bucket to CSV/Excel
3. **Bucket Filters**: Filter Top ASINs page by bucket
4. **Remove from Bucket**: UI to remove ASINs from buckets on the detail page
5. **Bucket Management Page**: Dedicated page to view/edit/delete buckets
6. **Bucket Permissions**: Role-based access to buckets
7. **Historical Tracking**: Track when ASINs were added/removed from buckets

## Troubleshooting

### Migration Fails
- Ensure database connection is configured correctly in `config.ini`
- Check that MySQL server is running
- Verify you have permissions to create tables

### Buckets Not Showing
- Clear browser cache and reload
- Check browser console for JavaScript errors
- Verify tables were created: `SHOW TABLES LIKE 'top_%';`

### ASINs Not Allocating
- Check Flask logs for errors
- Verify ASIN IDs are correct
- Ensure bucket exists before allocation

## Technical Details

**Files Modified:**
- `flask_app.py` - Added routes and updated queries
- `templates/top_asins.html` - Added UI components and JavaScript
- `templates/view_asin.html` - Added bucket display

**Files Created:**
- `database/create_top_asin_tables.sql` - Migration SQL
- `database/apply_top_asin_migration.py` - Migration script
- `TOP_ASIN_FEATURE_README.md` - This documentation

**Technology Stack:**
- Backend: Flask, PyMySQL
- Frontend: HTML, CSS, JavaScript (Vanilla)
- Database: MySQL 8.0+
- Styling: Custom CSS with gradient themes

