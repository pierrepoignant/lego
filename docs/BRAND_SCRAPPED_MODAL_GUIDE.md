# Brand Scrapped - Modal Overlay Guide

## Overview

The Brand Scrapped management page now uses a modern modal overlay popup for editing brand mappings instead of inline forms.

## How It Works

### 1. Opening the Modal

Click the **"Edit Mapping"** button on any row in the brand_scrapped table. This will open a centered modal overlay with a dark background.

### 2. Modal Contents

The modal displays:

#### Brand Information Box (Top)
- **Scrapped Brand Name**: The brand name as extracted from Amazon
- **Current Mapping**: Shows which official brand it's currently linked to (or "Not mapped")
- **ASINs Count**: Number of ASINs using this brand name

#### Section 1: Map to Existing Brand
- **Purpose**: Link the scraped brand to an existing brand in your brand table
- **Dropdown**: Shows all brands from the brand table (searchable)
- **Pre-selection**: If already mapped, the current brand is pre-selected
- **Action Button**: "Update Mapping" (purple button)

#### Section 2: Create New Brand (separated by "OR" divider)
- **Purpose**: Create a new brand entry using the scraped brand name
- **Brand Name Field**: Read-only, shows the name that will be created
- **Action Button**: "Create New Brand" (green button)
- **Safety**: Includes confirmation dialog before creating

### 3. Closing the Modal

You can close the modal in four ways:
1. Click the **×** button in the top-right corner
2. Click the **Cancel** button at the bottom
3. Press the **ESC** key on your keyboard
4. Click anywhere on the dark overlay outside the modal

## User Workflows

### Workflow A: Map to Existing Brand

**Scenario**: The scraped brand "AZMED" should map to existing brand "AZMED"

1. Click "Edit Mapping" on the AZMED row
2. Select "AZMED" from the dropdown
3. Click "Update Mapping"
4. ✓ Page refreshes with success message
5. ✓ Brand is now linked

### Workflow B: Handle Name Variations

**Scenario**: Scraped brand "AquaPaw" should map to existing "Aquapaw"

1. Click "Edit Mapping" on the AquaPaw row
2. Search and select "Aquapaw" from the dropdown
3. Click "Update Mapping"
4. ✓ Both variations now point to the same brand

### Workflow C: Create New Brand

**Scenario**: Scraped brand "NewBrandCo" doesn't exist in brand table

1. Click "Edit Mapping" on the NewBrandCo row
2. Scroll to "Create New Brand" section
3. Click "Create New Brand"
4. Confirm in the dialog
5. ✓ New brand created in brand table
6. ✓ Automatically linked to brand_scrapped entry

### Workflow D: Cancel Without Changes

1. Click "Edit Mapping" on any row
2. Decide not to make changes
3. Press ESC or click Cancel
4. ✓ Modal closes, no changes made

## Features

### Smart Pre-selection
- If a brand is already mapped, the dropdown automatically selects it
- Makes it easy to see current mapping or change to a different brand

### Form Validation
- Cannot submit mapping form without selecting a brand
- Shows alert if trying to submit empty selection

### Confirmation Dialogs
- Creating a new brand requires confirmation
- Prevents accidental brand creation
- Shows the brand name in the confirmation message

### Smooth Animations
- Modal fades in smoothly (200ms)
- Content slides up for modern feel (300ms)
- Dark overlay prevents interaction with background

### Accessibility
- ESC key support for quick closing
- Focus management
- Click-outside-to-close behavior
- Large, easy-to-click buttons

## Design Elements

### Colors
- **Purple (#667eea)**: Update Mapping button (primary action)
- **Green (#48bb78)**: Create New Brand button (secondary action)
- **Gray (#e2e8f0)**: Cancel button
- **Light Gray (#f7fafc)**: Info box background
- **Dark overlay**: rgba(0,0,0,0.6)

### Spacing
- Modal: 600px max width, 30px padding
- Responsive: 90% width on smaller screens
- Max height: 90vh with scroll if needed

### Typography
- Modal title: 1.5rem, bold
- Section headings: 1rem, semi-bold
- Body text: 0.875rem
- Buttons: 14px, semi-bold

## Tips

1. **Quick Search**: The brand dropdown is searchable - start typing to filter
2. **Keyboard Shortcuts**: Use TAB to navigate, ENTER to submit, ESC to close
3. **Review First**: Check the "Current Mapping" before making changes
4. **ASIN Count**: Use the ASIN count to prioritize which brands to map first
5. **Batch Work**: Use filters on the main page to work through unmapped brands systematically

## Technical Notes

- Modal uses fixed positioning with z-index 1000
- Body scroll is disabled when modal is open
- JavaScript handles all interactions (no page reloads for modal open/close)
- Forms POST to same backend routes as before
- Compatible with all modern browsers

## Comparison to Previous Version

### Before (Inline Editing)
- ❌ Dropdown and buttons in each table row
- ❌ Takes up table space
- ❌ Can be cluttered with many brands
- ❌ No clear separation between actions

### After (Modal Overlay)
- ✅ Clean table with just "Edit Mapping" button
- ✅ Focused interface for editing
- ✅ More space for additional fields in future
- ✅ Clear separation: map vs create
- ✅ Better user experience with animations
- ✅ Can see brand info while editing

## Support

For issues or questions about the modal interface, check:
- Console logs (F12 → Console tab)
- Network tab for form submissions
- Flash messages for success/error feedback

The modal is fully functional and ready to use at:
**http://127.0.0.1:5003/brand-scrapped**

