"""
Convert DoorDash JSON data to Excel and CSV formats for presentation
"""

import json
import csv
import pandas as pd
from pathlib import Path


def json_to_excel(json_file='doordash_final_v12.json', excel_file='doordash_menu_data.xlsx'):
    """
    Convert DoorDash JSON data to Excel format with multiple sheets.
    
    Args:
        json_file: Path to input JSON file
        excel_file: Path to output Excel file
    """
    print(f"Reading JSON file: {json_file}")
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Create Excel writer
    with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
        
        # Sheet 1: Restaurant Info
        restaurant_info = pd.DataFrame([data['restaurant_info']])
        restaurant_info.to_excel(writer, sheet_name='Restaurant Info', index=False)
        
        # Sheet 2: All Menu Items (flattened with section info)
        all_items = []
        for section_name, items in data['menu_categories'].items():
            for item in items:
                row = {
                    'Section': section_name,
                    'Name': item.get('name', ''),
                    'Description': item.get('description', ''),
                    'Price': item.get('price', ''),
                    'Rating': item.get('rating', ''),
                    '#1 Most Liked Tag': item.get('most_liked_tag', ''),
                    'Image URL': item.get('image', ''),
                    'Item URL': item.get('url', '')
                }
                all_items.append(row)
        
        all_items_df = pd.DataFrame(all_items)
        all_items_df.to_excel(writer, sheet_name='All Menu Items', index=False)
        
        # Sheet 3: Items by Section (each section gets its own sheet)
        for section_name, items in data['menu_categories'].items():
            if len(items) > 0:  # Only create sheets for sections with items
                section_items = []
                for item in items:
                    row = {
                        'Name': item.get('name', ''),
                        'Description': item.get('description', ''),
                        'Price': item.get('price', ''),
                        'Rating': item.get('rating', ''),
                        '#1 Most Liked Tag': item.get('most_liked_tag', ''),
                        'Image URL': item.get('image', ''),
                        'Item URL': item.get('url', '')
                    }
                    section_items.append(row)
                
                section_df = pd.DataFrame(section_items)
                # Excel sheet names must be <= 31 characters
                sheet_name = section_name[:31] if len(section_name) > 31 else section_name
                section_df.to_excel(writer, sheet_name=sheet_name, index=False)
        
        # Sheet: Summary Statistics
        summary_data = {
            'Metric': [
                'Restaurant Name',
                'Total Sections',
                'Total Items',
                'Sections with Items'
            ],
            'Value': [
                data['restaurant_info'].get('name', 'N/A'),
                len(data['menu_categories']),
                sum(len(items) for items in data['menu_categories'].values()),
                sum(1 for items in data['menu_categories'].values() if len(items) > 0)
            ]
        }
        
        # Add section breakdown
        for section_name, items in data['menu_categories'].items():
            summary_data['Metric'].append(f'Items in "{section_name}"')
            summary_data['Value'].append(len(items))
        
        summary_df = pd.DataFrame(summary_data)
        summary_df.to_excel(writer, sheet_name='Summary', index=False)
    
    print(f"Excel file created: {excel_file}")
    print(f"Total items exported: {sum(len(items) for items in data['menu_categories'].values())}")


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
    
    # Prepare CSV data
    rows = []
    for section_name, items in data['menu_categories'].items():
        for item in items:
            row = {
                'Restaurant Name': data['restaurant_info'].get('name', ''),
                'Restaurant URL': data['restaurant_info'].get('url', ''),
                'Cuisine': data['restaurant_info'].get('cuisine', ''),
                'Price Range': data['restaurant_info'].get('price_range', ''),
                'Section': section_name,
                'Item Name': item.get('name', ''),
                'Description': item.get('description', ''),
                'Price': item.get('price', ''),
                'Rating': item.get('rating', ''),
                '#1 Most Liked Tag': item.get('most_liked_tag', ''),
                'Image URL': item.get('image', ''),
                'Item URL': item.get('url', '')
            }
            rows.append(row)
    
    # Write to CSV
    if rows:
        fieldnames = ['Restaurant Name', 'Restaurant URL', 'Cuisine', 'Price Range', 
                     'Section', 'Item Name', 'Description', 'Price', 'Rating', 
                     '#1 Most Liked Tag', 'Image URL', 'Item URL']
        
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        
        print(f"CSV file created: {csv_file}")
        print(f"Total rows: {len(rows)}")
    else:
        print("No data to export")


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
