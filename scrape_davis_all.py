"""
Scrape ALL DoorDash restaurants in Davis (95616)
Found 51 restaurants - estimated time: ~2.5-3 hours
"""

import json
import time
import re
import pandas as pd
from pathlib import Path
from datetime import datetime

from SCRAPE import DoorDashScraper

PROFILE_PATH = "/Users/apple/Documents/uthsc/doordashScraper"
OUTPUT_DIR = "scraped_data_davis"
EXCEL_OUTPUT = "davis_all_restaurants.xlsx"
DELAY_BETWEEN = 25  # seconds between restaurants


def load_restaurants():
    """Load restaurants from davis_restaurants.txt"""
    restaurants = []
    with open('davis_restaurants.txt', 'r') as f:
        for line in f:
            line = line.strip()
            if '|' in line:
                name, url = line.split('|', 1)
                restaurants.append((name, url))
    return restaurants


def scrape_all(restaurants):
    """Scrape all restaurants and save to JSON files"""
    Path(OUTPUT_DIR).mkdir(exist_ok=True)
    
    successful = []
    failed = []
    
    print("="*60)
    print("🍽️  DAVIS RESTAURANT SCRAPER")
    print("="*60)
    print(f"Total restaurants: {len(restaurants)}")
    print(f"Estimated time: {len(restaurants) * 3.5:.0f} minutes (~{len(restaurants) * 3.5 / 60:.1f} hours)")
    print(f"Output directory: {OUTPUT_DIR}")
    print(f"Excel file: {EXCEL_OUTPUT}")
    print("="*60)
    
    start_time = datetime.now()
    
    for i, (name, url) in enumerate(restaurants, 1):
        print(f"\n[{i}/{len(restaurants)}] {name}")
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
            
            if data and data.get('menu_categories'):
                # Check if we got actual data
                total_items = sum(len(items) for items in data['menu_categories'].values())
                
                if total_items > 0:
                    # Save JSON
                    with open(json_file, 'w', encoding='utf-8') as f:
                        json.dump(data, f, indent=2, ensure_ascii=False)
                    
                    rating = data.get('reviews', {}).get('overall_rating', 'N/A')
                    items_with_ratings = sum(
                        1 for items in data['menu_categories'].values() 
                        for item in items if item.get('rating_count') and item.get('rating_count') != 'NA'
                    )
                    
                    print(f"   ✅ Success: {total_items} items, {items_with_ratings} with ratings, Store: {rating}")
                    successful.append((name, str(json_file)))
                else:
                    print(f"   ⚠️  No menu items found")
                    failed.append((name, url, "No menu items"))
            else:
                print(f"   ❌ Failed: No data returned")
                failed.append((name, url, "No data"))
                
        except Exception as e:
            print(f"   ❌ Error: {str(e)[:100]}")
            failed.append((name, url, str(e)[:100]))
        
        finally:
            try:
                scraper.close()
            except:
                pass
        
        # Delay before next restaurant
        if i < len(restaurants):
            print(f"   ⏳ Waiting {DELAY_BETWEEN}s...")
            time.sleep(DELAY_BETWEEN)
        
        # Progress update every 10 restaurants
        if i % 10 == 0:
            elapsed = datetime.now() - start_time
            avg_time = elapsed.total_seconds() / i
            remaining = (len(restaurants) - i) * avg_time
            print(f"\n   📊 Progress: {i}/{len(restaurants)} ({i*100//len(restaurants)}%)")
            print(f"   ⏱️  Elapsed: {elapsed}")
            print(f"   ⏱️  Est. remaining: {remaining/60:.0f} minutes\n")
    
    elapsed = datetime.now() - start_time
    print("\n" + "="*60)
    print("📊 SCRAPING COMPLETE")
    print("="*60)
    print(f"Time taken: {elapsed}")
    print(f"Successful: {len(successful)}")
    print(f"Failed: {len(failed)}")
    
    if failed:
        print("\nFailed restaurants:")
        for name, url, reason in failed:
            print(f"   - {name}: {reason}")
    
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
                
                if all_items:
                    df = pd.DataFrame(all_items)
                    df.to_excel(writer, sheet_name=sheet_name, index=False)
                    
                    actual_ratings = sum(1 for item in all_items if item['Rating Count'] != 'NA')
                    print(f"   ✅ {sheet_name}: {len(all_items)} items, {actual_ratings} with ratings")
                
            except Exception as e:
                print(f"   ❌ Error with {json_file}: {e}")
    
    print(f"\n✅ Excel saved: {EXCEL_OUTPUT}")


def main():
    # Load restaurants
    restaurants = load_restaurants()
    print(f"Loaded {len(restaurants)} restaurants from davis_restaurants.txt")
    
    # Step 1: Scrape all restaurants
    successful, failed = scrape_all(restaurants)
    
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
