# Quick Command Reference

## 🗑️ Flush Financial Data

To **flush all financial data** (removes all records from the `financials` table):

```bash
python manage_data.py flush
```

This will:
- ✅ Delete ALL financial records from the database
- ✅ Keep all brands intact
- ✅ Keep all ASINs intact
- ✅ Show you how many records were deleted

---

## 📥 Import Commands

### Import infinite.csv
```bash
python manage_data.py import-infinite
```

### Import razor.csv
```bash
python manage_data.py import-razor
```

### Flush then Import (recommended)
```bash
# Flush and import infinite
python manage_data.py flush import-infinite

# Flush and import razor
python manage_data.py flush import-razor
```

---

## 🔒 Duplicate Prevention

### ✅ Brands
- **Always checks** if brand name exists before inserting
- If exists: Returns existing brand ID
- If not exists: Creates new brand

### ✅ ASINs
- **Always checks** if ASIN exists before inserting
- If exists: Returns existing ASIN ID (and updates brand/status if provided)
- If not exists: Creates new ASIN

**Implementation in `db_utils.py`:**

```python
# Brand: Checks by brand name (UNIQUE constraint)
get_or_create_brand(cursor, brand_name)

# ASIN: Checks by asin value (UNIQUE constraint)
get_or_create_asin(cursor, asin_value, product_id, brand_id, status)
```

### Database Constraints
The database schema also enforces uniqueness:
- `brand.brand` - UNIQUE constraint
- `asin.asin` - UNIQUE constraint

This provides **double protection** against duplicates!

---

## 📊 Check Database Status

```bash
# Quick check
python check_database.py

# Detailed summary
python summary_report.py
```

---

## 🎯 Common Workflows

### First Time Setup
```bash
python init_database.py
python manage_data.py import-infinite
```

### Update Data (Replace All Financial Data)
```bash
python manage_data.py flush import-infinite
```

### Add Razor Data
```bash
python manage_data.py import-razor
```

### Replace Everything
```bash
python manage_data.py flush import-infinite import-razor
```

---

## ⚠️ Important Notes

1. **Flushing only removes financial data** - Your brands and ASINs are preserved
2. **Imports are additive** - If you import twice without flushing, you'll duplicate financial records (but not brands/ASINs)
3. **Always flush before reimporting** to avoid duplicate financial data
4. **Brands and ASINs are never duplicated** thanks to the check-before-insert logic and UNIQUE constraints

