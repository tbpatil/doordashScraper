"""
Scrape all DoorDash restaurants in 95616 (Davis, CA)
Based on provided restaurant list.

Estimated time: ~60-75 minutes for 19 restaurants
"""

import json
import time
import re
import pandas as pd
from pathlib import Path
from datetime import datetime

from SCRAPE import DoorDashScraper

# Restaurants with valid DoorDash URLs
RESTAURANTS = [
    ("Yuchan Shokudo", "https://www.doordash.com/en/restaurants/yuchan-shokudo-davis"),
    ("Sam's Mediterranean Cuisine", "https://www.doordash.com/en/restaurants/sams-mediterranean-cuisine-davis"),
    ("Yang Kee Dumpling", "https://www.doordash.com/en/restaurants/yang-kee-dumpling-davis"),
    ("Sit Lo Saigon", "https://www.doordash.com/en/restaurants/sit-lo-saigon-davis"),
    ("Urban Plates", "https://www.doordash.com/en/restaurants/urban-plates-davis"),
    ("The Melt", "https://www.doordash.com/en/restaurants/the-melt-davis"),
    ("My Burma", "https://www.doordash.com/en/restaurants/my-burma-davis"),
    ("Mikuni", "https://www.doordash.com/en/restaurants/mikuni-davis"),
    ("Shanghai Town", "https://www.doordash.com/en/restaurants/shanghai-town-davis"),
    ("Paesanos", "https://www.doordash.com/en/restaurants/paesanos-davis"),
    ("Woodstock's Pizza", "https://www.doordash.com/en/restaurants/woodstocks-pizza-davis"),
    ("Taqueria Davis", "https://www.doordash.com/en/restaurants/taqueria-davis"),
    ("Dos Coyotes Border Cafe", "https://www.doordash.com/en/restaurants/dos-coyotes-border-cafe-davis"),
    ("Pho King 4", "https://www.doordash.com/en/restaurants/pho-king-4-davis"),
    ("In-N-Out Burger", "https://www.doordash.com/en/restaurants/in-n-out-burger-davis"),
    ("Panera Bread", "https://www.doordash.com/en/restaurants/panera-bread-davis"),
    ("Subway", "https://www.doordash.com/en/restaurants/subway-davis"),
    ("Panda Express", "https://www.doordash.com/en/restaurants/panda-express-davis"),
    ("Jamba Juice", "https://www.doordash.com/en/restaurants/jamba-juice-davis"),
]

PROFILE_PATH = "/Users/apple/Documents/uthsc/doordashScraper"
OUTPUT_DIR = "scraped_data_95616"
EXCEL_OUTPUT = "davis_95616_restaurants.xlsx"
DELAY_BETWEEN = 25  # seconds between restaurants


def scrape_all():
    """Scrape all restaurants and save to JSON files"""
    Path(OUTPUT_DIR).mkdir(exist_ok=True)
    
    successful = []
    failed = []
    
    print("="*60)
    print("🍽️  DAVIS 95616 RESTAURANT SCRAPER")
    print("="*60)
    print(f"Total restaurants: {len(RESTAURANTS)}")
    print(f"Estimated time: {len(RESTAURANTS) * 3.5:.0f} minutes")
    print(f"Output directory: {OUTPUT_DIR}")
    print(f"Excel file: {EXCEL_OUTPUT}")
    print("="*60)
    
    start_time = datetime.now()
    
    for i, (name, url) in enumerate(RESTAURANTS, 1):
        print(f"\n[{i}/{len(RESTAURANTS)}] {name}")
        print(f"   URL: {url}")
        
        # Create safe filename
        safe_name = re.sub(r'[^\w\s-]', '', name).strip().replace(' ', '_')[:50]
        json_file = Path(OUTPUT_DIR) / f"{safe_name}.json"
        
        # Skip if already scraped
        if json_file.exists():
            print(f"   ⏭️  Already scraped, skipping...")
            successful.append((name, str(json_file)))
            continue
        
        try:
            scraper = DoorDashScraper(chrome_profile_path=PROFILE_PATH)
            data = scraper.scrape_restaurant(url)
            
            if data:
                # Save JSON
                with open(json_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                
                total_items = sum(len(items) for items in data['menu_categories'].values())
                rating = data.get('reviews', {}).get('overall_rating', 'N/A')
                items_with_ratings = sum(
                    1 for items in data['menu_categories'].values() 
                    for item in items if item.get('rating_count') and item.get('rating_count') != 'NA'
                )
                
                print(f"   ✅ Success: {total_items} items, {items_with_ratings} with ratings, Store rating: {rating}")
                successful.append((name, str(json_file)))
            else:
                print(f"   ❌ Failed: No data returned")
                failed.append((name, url))
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
            failed.append((name, url))
        
        finally:
            try:
                scraper.close()
            except:
                pass
        
        # Delay before next restaurant
        if i < len(RESTAURANTS):
            print(f"   ⏳ Waiting {DELAY_BETWEEN}s before next...")
            time.sleep(DELAY_BETWEEN)
    
    elapsed = datetime.now() - start_time
    print("\n" + "="*60)
    print("📊 SCRAPING COMPLETE")
    print("="*60)
    print(f"Time taken: {elapsed}")
    print(f"Successful: {len(successful)}")
    print(f"Failed: {len(failed)}")
    
    if failed:
        print("\nFailed restaurants:")
        for name, url in failed:
            print(f"   - {name}: {url}")
    
    return successful, failed


def combine_to_excel(json_files):
    """Combine all JSON files into one Excel file"""
    print(f"\n📊 Creating Excel: {EXCEL_OUTPUT}")
    
    with pd.ExcelWriter(EXCEL_OUTPUT, engine='openpyxl') as writer:
        for name, json_file in json_files:
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                restaurant_name = data['restaurant_info'].get('name', name)
                # Excel sheet names: max 31 chars, no special chars
                sheet_name = re.sub(r'[/\\*?\[\]:]', '', restaurant_name)[:31]
                
                # Make unique if duplicate
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
                        rating_pct = item.get('rating_percentage')
                        rating_cnt = item.get('rating_count')
                        
                        row = {
                            'Restaurant': restaurant_name,
                            'Store Rating': store_rating,
                            'Section': section_name,
                            'Item Name': item.get('name', ''),
                            'Price': item.get('price') or 'NA',
                            'Rating %': rating_pct if rating_pct and rating_pct != 'NA' and str(rating_pct).strip() else 'NA',
                            'Rating Count': rating_cnt if rating_cnt and rating_cnt != 'NA' and str(rating_cnt).strip() else 'NA',
                            'Promo Tag': item.get('most_liked_tag') or ''
                        }
                        all_items.append(row)
                
                df = pd.DataFrame(all_items)
                df.to_excel(writer, sheet_name=sheet_name, index=False)
                
                # Count actual ratings
                actual_ratings = sum(1 for item in all_items if item['Rating Count'] != 'NA')
                print(f"   ✅ {sheet_name}: {len(all_items)} items, {actual_ratings} with ratings")
                
            except Exception as e:
                print(f"   ❌ Error with {json_file}: {e}")
    
    print(f"\n✅ Excel saved: {EXCEL_OUTPUT}")


def main():
    # Step 1: Scrape all restaurants
    successful, failed = scrape_all()
    
    # Step 2: Combine into Excel
    if successful:
        combine_to_excel(successful)
        print(f"\n🎉 Done! Scraped {len(successful)} restaurants.")
        print(f"   JSON files: {OUTPUT_DIR}/")
        print(f"   Excel file: {EXCEL_OUTPUT}")
    else:
        print("\n❌ No restaurants were successfully scraped.")


if __name__ == "__main__":
    main()
