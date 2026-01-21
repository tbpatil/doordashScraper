"""
DoorDash Zipcode Scraper
Automatically scrapes all restaurants in a given area and saves to Excel.

Usage:
    python scrape_zipcode.py                    # Uses default (Davis, CA)
    python scrape_zipcode.py --city "davis-ca"  # Specify city
    python scrape_zipcode.py --limit 10         # Limit to 10 restaurants
"""

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import json
import time
import random
import re
import pandas as pd
import argparse
from pathlib import Path
from datetime import datetime

# Import the main scraper
from SCRAPE import DoorDashScraper


def get_restaurant_urls(city_slug="davis-ca", limit=None, profile_path=None):
    """
    Get all restaurant URLs from a DoorDash city page.
    
    Args:
        city_slug: City identifier like "davis-ca", "sacramento-ca"
        limit: Max number of restaurants to return (None = all)
        profile_path: Chrome profile path
    
    Returns:
        List of (restaurant_name, url) tuples
    """
    options = uc.ChromeOptions()
    if profile_path:
        options.add_argument(f"--user-data-dir={profile_path}")
    options.add_argument("--window-size=1920,1080")
    
    print(f"🔍 Finding restaurants in {city_slug}...")
    driver = uc.Chrome(options=options, version_main=None)
    
    try:
        url = f"https://www.doordash.com/food-delivery/{city_slug}-restaurants/"
        driver.get(url)
        time.sleep(10)  # Wait for Cloudflare/page load
        
        # Scroll to load more restaurants
        print("   Scrolling to load all restaurants...")
        last_height = driver.execute_script("return document.body.scrollHeight")
        scroll_attempts = 0
        
        while scroll_attempts < 20:
            driver.execute_script("window.scrollBy(0, 800);")
            time.sleep(1.5)
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height
            scroll_attempts += 1
        
        # Find restaurant links
        restaurants = driver.find_elements(By.CSS_SELECTOR, 'a[href*="/store/"]')
        
        seen = set()
        results = []
        
        for r in restaurants:
            href = r.get_attribute('href')
            # Get restaurant name from aria-label or text
            name = r.get_attribute('aria-label') or ''
            if not name:
                name = r.text.split('\n')[0] if r.text else ''
            
            # Clean up the name
            name = name.strip()
            
            # Filter valid restaurant links
            if (href and '/store/' in href and 
                href not in seen and 
                name and len(name) > 2 and
                'delivery' not in name.lower()):
                
                seen.add(href)
                results.append((name, href))
                
                if limit and len(results) >= limit:
                    break
        
        print(f"   Found {len(results)} restaurants")
        return results
        
    finally:
        driver.quit()


def scrape_multiple_restaurants(restaurant_list, profile_path, output_dir="scraped_data", delay_between=30):
    """
    Scrape multiple restaurants and save each to JSON.
    
    Args:
        restaurant_list: List of (name, url) tuples
        profile_path: Chrome profile path
        output_dir: Directory to save JSON files
        delay_between: Seconds to wait between restaurants
    
    Returns:
        List of successfully scraped JSON file paths
    """
    Path(output_dir).mkdir(exist_ok=True)
    scraped_files = []
    
    print(f"\n🍽️  Scraping {len(restaurant_list)} restaurants...")
    print(f"   Delay between restaurants: {delay_between} seconds")
    print("="*60)
    
    for i, (name, url) in enumerate(restaurant_list, 1):
        print(f"\n[{i}/{len(restaurant_list)}] {name}")
        print(f"   URL: {url}")
        
        # Create safe filename
        safe_name = re.sub(r'[^\w\s-]', '', name).strip().replace(' ', '_')[:50]
        json_file = Path(output_dir) / f"{safe_name}.json"
        
        # Skip if already scraped
        if json_file.exists():
            print(f"   ⏭️  Already scraped, skipping...")
            scraped_files.append(str(json_file))
            continue
        
        try:
            scraper = DoorDashScraper(chrome_profile_path=profile_path)
            data = scraper.scrape_restaurant(url)
            
            if data:
                with open(json_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                
                total_items = sum(len(items) for items in data['menu_categories'].values())
                rating = data.get('reviews', {}).get('overall_rating', 'N/A')
                print(f"   ✅ Success: {total_items} items, Rating: {rating}")
                scraped_files.append(str(json_file))
            else:
                print(f"   ❌ Failed: No data returned")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        finally:
            try:
                scraper.close()
            except:
                pass
        
        # Delay before next restaurant (except for last one)
        if i < len(restaurant_list):
            print(f"   ⏳ Waiting {delay_between}s before next restaurant...")
            time.sleep(delay_between)
    
    return scraped_files


def combine_to_excel(json_files, excel_file="doordash_all_restaurants.xlsx"):
    """
    Combine multiple restaurant JSON files into one Excel file.
    Each restaurant gets its own sheet.
    """
    print(f"\n📊 Creating combined Excel: {excel_file}")
    
    with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
        for json_file in json_files:
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                restaurant_name = data['restaurant_info'].get('name', 'Restaurant')
                # Excel sheet names: max 31 chars, no special chars
                sheet_name = re.sub(r'[/\\*?\[\]:]', '', restaurant_name)[:31]
                
                # Make unique if duplicate
                existing = list(writer.sheets.keys()) if hasattr(writer, 'sheets') else []
                if sheet_name in existing:
                    sheet_name = f"{sheet_name[:28]}_{len(existing)}"
                
                reviews = data.get('reviews', {})
                store_rating = reviews.get('overall_rating', '')
                
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
                
                # Remove empty columns (but keep Rating columns with NA)
                cols_to_keep = []
                for col in df.columns:
                    if 'Rating' in col:
                        cols_to_keep.append(col)
                    elif df[col].apply(lambda x: x is not None and str(x).strip() not in ['', 'None']).any():
                        cols_to_keep.append(col)
                df = df[cols_to_keep]
                
                df.to_excel(writer, sheet_name=sheet_name, index=False)
                print(f"   ✅ {sheet_name}: {len(all_items)} items")
                
            except Exception as e:
                print(f"   ❌ Error with {json_file}: {e}")
    
    print(f"\n✅ Excel saved: {excel_file}")


def main():
    parser = argparse.ArgumentParser(description='Scrape DoorDash restaurants by city/zipcode')
    parser.add_argument('--city', default='davis-ca', help='City slug (e.g., davis-ca, sacramento-ca)')
    parser.add_argument('--limit', type=int, default=None, help='Max restaurants to scrape')
    parser.add_argument('--delay', type=int, default=30, help='Seconds between restaurants')
    parser.add_argument('--output', default='doordash_all_restaurants.xlsx', help='Output Excel file')
    parser.add_argument('--profile', default='/Users/apple/Documents/uthsc/doordashScraper', help='Chrome profile path')
    
    args = parser.parse_args()
    
    print("="*60)
    print("🚀 DoorDash Zipcode Scraper")
    print("="*60)
    print(f"City: {args.city}")
    print(f"Limit: {args.limit or 'All'}")
    print(f"Delay: {args.delay}s between restaurants")
    print(f"Output: {args.output}")
    print("="*60)
    
    # Step 1: Get restaurant URLs
    restaurants = get_restaurant_urls(
        city_slug=args.city,
        limit=args.limit,
        profile_path=args.profile
    )
    
    if not restaurants:
        print("❌ No restaurants found!")
        return
    
    # Show restaurant list
    print(f"\n📋 Restaurants to scrape:")
    for i, (name, url) in enumerate(restaurants, 1):
        print(f"   {i}. {name}")
    
    # Confirm
    print(f"\n⚠️  This will scrape {len(restaurants)} restaurants.")
    print(f"   Estimated time: ~{len(restaurants) * 3} minutes")
    input("   Press Enter to continue (Ctrl+C to cancel)...")
    
    # Step 2: Scrape each restaurant
    scraped_files = scrape_multiple_restaurants(
        restaurants,
        profile_path=args.profile,
        delay_between=args.delay
    )
    
    # Step 3: Combine into Excel
    if scraped_files:
        combine_to_excel(scraped_files, args.output)
        print(f"\n🎉 Done! Scraped {len(scraped_files)} restaurants.")
        print(f"   Excel file: {args.output}")
    else:
        print("\n❌ No restaurants were successfully scraped.")


if __name__ == "__main__":
    main()
