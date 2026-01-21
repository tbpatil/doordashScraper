"""
Convert DoorDash JSON data to Excel and CSV formats
- Single sheet per restaurant with all menu items
- Focus on ratings and promos (no image/item URLs)
"""

import json
import csv
import pandas as pd
from pathlib import Path


def json_to_excel(json_file='doordash_final_v12.json', excel_file='doordash_menu_data.xlsx'):
    """
    Convert DoorDash JSON data to Excel format.
    Each restaurant gets its own sheet with all menu items.
    
    Args:
        json_file: Path to input JSON file
        excel_file: Path to output Excel file
    """
    print(f"Reading JSON file: {json_file}")
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Create Excel writer
    with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
        
        # Get restaurant name for sheet name
        restaurant_name = data['restaurant_info'].get('name', 'Restaurant')
        # Excel sheet names must be <= 31 characters and can't contain certain chars
        sheet_name = restaurant_name[:31].replace('/', '-').replace('\\', '-').replace('*', '').replace('?', '').replace('[', '').replace(']', '')
        
        # Get restaurant-level info
        reviews = data.get('reviews', {})
        store_rating = reviews.get('overall_rating', '')
        store_total_ratings = reviews.get('total_ratings', '')
        
        # Build all items into a single list
        all_items = []
        for section_name, items in data['menu_categories'].items():
            for item in items:
                rating_pct = item.get('rating_percentage')
                rating_cnt = item.get('rating_count')
                row = {
                    'Restaurant': restaurant_name,
                    'Store Rating': store_rating,
                    'Section': section_name,
                    'Item Name': item.get('name', ''),
                    'Price': item.get('price', ''),
                    'Rating %': rating_pct if rating_pct and rating_pct != 'NA' and str(rating_pct).strip() else 'NA',
                    'Rating Count': rating_cnt if rating_cnt and rating_cnt != 'NA' and str(rating_cnt).strip() else 'NA',
                    'Promo Tag': item.get('most_liked_tag') or ''
                }
                all_items.append(row)
        
        # Create DataFrame
        df = pd.DataFrame(all_items)
        
        # Remove columns that are completely empty (but keep Rating columns with NA)
        cols_to_keep = []
        for col in df.columns:
            # Always keep Rating columns (they have NA for items without ratings)
            if 'Rating' in col:
                cols_to_keep.append(col)
            else:
                # Check if column has any non-empty values
                has_data = df[col].apply(lambda x: x is not None and str(x).strip() != '' and str(x) != 'None').any()
                if has_data:
                    cols_to_keep.append(col)
        
        df = df[cols_to_keep]
        df.to_excel(writer, sheet_name=sheet_name, index=False)
        
        # Auto-adjust column widths
        worksheet = writer.sheets[sheet_name]
        for idx, col in enumerate(df.columns):
            max_length = max(
                df[col].astype(str).map(len).max() if len(df) > 0 else 0,
                len(col)
            ) + 2
            # Cap at 50 characters
            max_length = min(max_length, 50)
            worksheet.column_dimensions[chr(65 + idx)].width = max_length
        
        print(f"Columns included: {', '.join(cols_to_keep)}")
    
    print(f"Excel file created: {excel_file}")
    print(f"Sheet: {sheet_name}")
    print(f"Total items: {len(all_items)}")
    
    # Count items with ratings
    items_with_ratings = sum(1 for item in all_items if item.get('Rating Count'))
    print(f"Items with ratings: {items_with_ratings}")


def json_to_csv(json_file='doordash_final_v12.json', csv_file='doordash_menu_data.csv'):
    """
    Convert DoorDash JSON data to CSV format.
    
    Args:
        json_file: Path to input JSON file
        csv_file: Path to output CSV file
    """
    print(f"Reading JSON file: {json_file}")
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Get restaurant-level info
    reviews = data.get('reviews', {})
    restaurant_name = data['restaurant_info'].get('name', '')
    store_rating = reviews.get('overall_rating', '')
    store_total_ratings = reviews.get('total_ratings', '')
    
    # Prepare CSV data
    rows = []
    for section_name, items in data['menu_categories'].items():
        for item in items:
            rating_pct = item.get('rating_percentage')
            rating_cnt = item.get('rating_count')
            row = {
                'Restaurant': restaurant_name,
                'Store Rating': store_rating,
                'Section': section_name,
                'Item Name': item.get('name', ''),
                'Price': item.get('price', ''),
                'Rating %': rating_pct if rating_pct and rating_pct != 'NA' and str(rating_pct).strip() else 'NA',
                'Rating Count': rating_cnt if rating_cnt and rating_cnt != 'NA' and str(rating_cnt).strip() else 'NA',
                'Promo Tag': item.get('most_liked_tag') or ''
            }
            rows.append(row)
    
    # Write to CSV
    if rows:
        fieldnames = ['Restaurant', 'Store Rating',
                     'Section', 'Item Name', 'Price', 
                     'Rating %', 'Rating Count', 'Promo Tag']
        
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        
        print(f"CSV file created: {csv_file}")
        print(f"Total rows: {len(rows)}")
    else:
        print("No data to export")


def combine_json_files_to_excel(json_files, excel_file='doordash_all_restaurants.xlsx'):
    """
    Combine multiple restaurant JSON files into a single Excel file.
    Each restaurant gets its own sheet.
    
    Args:
        json_files: List of paths to JSON files
        excel_file: Path to output Excel file
    """
    print(f"Combining {len(json_files)} restaurants into {excel_file}")
    
    with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
        for json_file in json_files:
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Get restaurant name for sheet name
                restaurant_name = data['restaurant_info'].get('name', 'Restaurant')
                sheet_name = restaurant_name[:31].replace('/', '-').replace('\\', '-').replace('*', '').replace('?', '').replace('[', '').replace(']', '')
                
                # Make sheet name unique if duplicate
                existing_sheets = writer.sheets.keys() if hasattr(writer, 'sheets') else []
                if sheet_name in existing_sheets:
                    sheet_name = f"{sheet_name[:28]}_{len(existing_sheets)}"
                
                # Get restaurant-level info
                reviews = data.get('reviews', {})
                store_rating = reviews.get('overall_rating', '')
                store_total_ratings = reviews.get('total_ratings', '')
                
                # Build all items
                all_items = []
                for section_name, items in data['menu_categories'].items():
                    for item in items:
                        rating_pct = item.get('rating_percentage')
                        rating_cnt = item.get('rating_count')
                        row = {
                            'Restaurant': restaurant_name,
                            'Store Rating': store_rating,
                            'Section': section_name,
                            'Item Name': item.get('name', ''),
                            'Price': item.get('price', ''),
                            'Rating %': rating_pct if rating_pct and rating_pct != 'NA' and str(rating_pct).strip() else 'NA',
                            'Rating Count': rating_cnt if rating_cnt and rating_cnt != 'NA' and str(rating_cnt).strip() else 'NA',
                            'Promo Tag': item.get('most_liked_tag') or ''
                        }
                        all_items.append(row)
                
                df = pd.DataFrame(all_items)
                df.to_excel(writer, sheet_name=sheet_name, index=False)
                print(f"  Added: {restaurant_name} ({len(all_items)} items)")
                
            except Exception as e:
                print(f"  Error processing {json_file}: {e}")
    
    print(f"\nExcel file created: {excel_file}")


if __name__ == "__main__":
    import sys
    
    json_file = 'doordash_final_v12.json'
    if len(sys.argv) > 1:
        json_file = sys.argv[1]
    
    print("="*60)
    print("DoorDash Data Export Tool")
    print("="*60)
    
    # Export to Excel
    try:
        json_to_excel(json_file)
    except ImportError:
        print("Warning: openpyxl not installed. Install with: pip install openpyxl")
        print("Skipping Excel export...")
    except Exception as e:
        print(f"Error creating Excel file: {e}")
    
    # Export to CSV
    try:
        json_to_csv(json_file)
    except Exception as e:
        print(f"Error creating CSV file: {e}")
    
    print("="*60)
    print("Export complete!")
