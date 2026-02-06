#!/usr/bin/env python3
"""Re-scrape all restaurants with fixed rating extraction"""

import json
import time
import re
import pandas as pd
from pathlib import Path
from SCRAPE import DoorDashScraper

DATA_DIR = Path("scraped_data_davis")
PROFILE_PATH = "/Users/apple/Documents/uthsc/doordashScraper"

print("=" * 70)
print("RE-SCRAPING ALL RESTAURANTS WITH FIXED RATING EXTRACTION")
print("=" * 70)

# Collect all restaurant URLs from existing JSON files
restaurants = []
for json_file in sorted(DATA_DIR.glob("*.json")):
    try:
        with open(json_file, 'r') as f:
            data = json.load(f)
        
        name = data.get('restaurant_info', {}).get('name', json_file.stem)
        url = data.get('restaurant_info', {}).get('url')
        
        if url:
            restaurants.append({
                'name': name,
                'url': url,
                'file': json_file
            })
    except:
        continue

print(f"Found {len(restaurants)} restaurants to re-scrape")
print("-" * 70)

successful = 0
failed = 0

for i, rest in enumerate(restaurants, 1):
    print(f"\n[{i}/{len(restaurants)}] {rest['name'][:40]}")
    print(f"   URL: {rest['url'][:60]}...")
    
    try:
        scraper = DoorDashScraper(chrome_profile_path=PROFILE_PATH)
        data = scraper.scrape_restaurant(rest['url'])
        
        if data and data.get('menu_categories'):
            total_items = sum(len(items) for items in data['menu_categories'].values())
            if total_items > 0:
                # Count ratings
                ratings_count = 0
                for section, items in data['menu_categories'].items():
                    for item in items:
                        if item.get('rating_percentage') != 'NA':
                            ratings_count += 1
                
                # Save updated JSON
                with open(rest['file'], 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                
                print(f"   ✅ {total_items} items, {ratings_count} with ratings")
                successful += 1
            else:
                print(f"   ⚠️ No items found")
                failed += 1
        else:
            print(f"   ❌ No data")
            failed += 1
    except Exception as e:
        print(f"   ❌ Error: {str(e)[:60]}")
        failed += 1
    finally:
        try:
            scraper.close()
        except:
            pass
    
    # Delay between restaurants
    if i < len(restaurants):
        time.sleep(15)

print("\n" + "=" * 70)
print(f"RE-SCRAPE COMPLETE: {successful} success, {failed} failed")
print("=" * 70)

# Regenerate Excel
print("\n📊 REGENERATING EXCEL FILE...")

with pd.ExcelWriter('davis_all_restaurants.xlsx', engine='openpyxl') as writer:
    for json_file in sorted(DATA_DIR.glob("*.json")):
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
            
            restaurant_name = data['restaurant_info'].get('name', json_file.stem)
            if not restaurant_name:
                continue
            
            sheet_name = re.sub(r'[/\\*?\[\]:]', '', str(restaurant_name))[:31]
            
            existing = list(writer.sheets.keys()) if hasattr(writer, 'sheets') else []
            base_name = sheet_name
            counter = 1
            while sheet_name in existing:
                sheet_name = f"{base_name[:28]}_{counter}"
                counter += 1
            
            reviews = data.get('reviews', {})
            store_rating = reviews.get('overall_rating') or 'NA'
            
            all_items = []
            for section_name, items in data['menu_categories'].items():
                for item in items:
                    row = {
                        'Restaurant': restaurant_name,
                        'Store Rating': store_rating,
                        'Section': section_name,
                        'Item Name': item.get('name', ''),
                        'Price': item.get('price') or 'NA',
                        'Rating %': item.get('rating_percentage', 'NA'),
                        'Rating Count': item.get('rating_count', 'NA'),
                        'Promo Tag': item.get('most_liked_tag') or ''
                    }
                    all_items.append(row)
            
            if all_items:
                df = pd.DataFrame(all_items)
                df.to_excel(writer, sheet_name=sheet_name, index=False)
        except Exception as e:
            print(f"   ❌ Excel error: {json_file.name}: {e}")

print("\n🎉 DONE! Excel file updated: davis_all_restaurants.xlsx")
