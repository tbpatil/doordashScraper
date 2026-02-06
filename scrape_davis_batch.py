"""
Batch DoorDash scraper for Davis (95616).
Scrapes a slice of davis_restaurants.txt and generates a per-batch Excel file.
"""

import argparse
import json
import re
import time
from pathlib import Path
from datetime import datetime

import pandas as pd

from SCRAPE import DoorDashScraper

PROFILE_PATH = "/Users/apple/Documents/uthsc/doordashScraper"
OUTPUT_DIR = "scraped_data_davis"
DELAY_BETWEEN = 25  # seconds between restaurants


def load_restaurants(path="davis_restaurants.txt"):
    restaurants = []
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if "|" in line:
                name, url = line.split("|", 1)
                restaurants.append((name, url))
    return restaurants


def safe_filename(name):
    return re.sub(r"[^\w\s-]", "", name).strip().replace(" ", "_")[:50]


def normalize_rating_fields(item):
    rating_percent = item.get("rating_percent")
    rating_count = item.get("rating_count")

    if rating_percent is None:
        rating_percentage = item.get("rating_percentage")
        if isinstance(rating_percentage, str) and "%" in rating_percentage:
            try:
                rating_percent = int(rating_percentage.replace("%", "").strip())
            except Exception:
                rating_percent = None

    if rating_count is None:
        try:
            rating_count = int(item.get("rating_count"))
        except Exception:
            rating_count = None

    return rating_percent, rating_count


def scrape_batch(restaurants, start, count, overwrite, batch_id):
    Path(OUTPUT_DIR).mkdir(exist_ok=True)

    batch = restaurants[start:start + count]
    if not batch:
        print("No restaurants in this batch slice.")
        return [], []

    log_path = Path(f"scrape_davis_batch_{batch_id}.log")

    def log_line(line):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] {line}\n")

    successful = []
    failed = []
    skipped = []

    print("=" * 60)
    print("🍽️  DAVIS RESTAURANT BATCH SCRAPER")
    print("=" * 60)
    print(f"Batch ID: {batch_id}")
    print(f"Slice: start={start}, count={count}")
    print(f"Total in batch: {len(batch)}")
    print(f"Output directory: {OUTPUT_DIR}")
    print("=" * 60)

    for offset, (name, url) in enumerate(batch, start=0):
        idx = start + offset
        print(f"\n[{offset + 1}/{len(batch)}] ({idx}) {name}")
        print(f"   URL: {url}")

        json_file = Path(OUTPUT_DIR) / f"{safe_filename(name)}.json"

        if json_file.exists() and not overwrite:
            print("   ⏭️  Already scraped, skipping...")
            skipped.append((idx, name, url, str(json_file)))
            log_line(f"{idx}|{name}|{url}|SKIPPED|")
            continue

        scraper = None
        try:
            scraper = DoorDashScraper(chrome_profile_path=PROFILE_PATH)
            data = scraper.scrape_restaurant(url)

            if data and data.get("menu_categories"):
                total_items = sum(len(items) for items in data["menu_categories"].values())
                if total_items > 0:
                    with open(json_file, "w", encoding="utf-8") as f:
                        json.dump(data, f, indent=2, ensure_ascii=False)

                    items_with_ratings = sum(
                        1
                        for items in data["menu_categories"].values()
                        for item in items
                        if item.get("rating_count")
                    )

                    print(f"   ✅ Success: {total_items} items, {items_with_ratings} with ratings")
                    successful.append((idx, name, url, str(json_file)))
                    log_line(f"{idx}|{name}|{url}|SUCCESS|{total_items} items")
                else:
                    print("   ⚠️  No menu items found")
                    failed.append((idx, name, url, "No menu items"))
                    log_line(f"{idx}|{name}|{url}|FAIL|No menu items")
            else:
                print("   ❌ Failed: No data returned")
                failed.append((idx, name, url, "No data"))
                log_line(f"{idx}|{name}|{url}|FAIL|No data")

        except Exception as e:
            msg = str(e)[:200]
            print(f"   ❌ Error: {msg}")
            failed.append((idx, name, url, msg))
            log_line(f"{idx}|{name}|{url}|ERROR|{msg}")
        finally:
            try:
                if scraper:
                    scraper.close()
            except Exception:
                pass

        if offset + 1 < len(batch):
            print(f"   ⏳ Waiting {DELAY_BETWEEN}s...")
            time.sleep(DELAY_BETWEEN)

    print("\n" + "=" * 60)
    print("📊 BATCH COMPLETE")
    print("=" * 60)
    print(f"Successful: {len(successful)}")
    print(f"Failed: {len(failed)}")
    print(f"Skipped: {len(skipped)}")

    if failed:
        print("\nFailed restaurants:")
        for idx, name, url, reason in failed:
            print(f"   - ({idx}) {name}: {reason}")

    return successful, failed, skipped


def generate_batch_excel(restaurants, start, count, batch_id):
    batch = restaurants[start:start + count]
    if not batch:
        return None

    excel_name = f"davis_batch_{batch_id}_restaurants_{start}_{start + count - 1}.xlsx"

    summary_rows = []

    def sheet_safe_name(name, existing):
        base = re.sub(r"[\/\\*\[\]:?]", "", name)[:31]
        if not base:
            base = "Restaurant"
        sheet_name = base
        counter = 1
        while sheet_name in existing:
            suffix = f"_{counter}"
            sheet_name = f"{base[:31 - len(suffix)]}{suffix}"
            counter += 1
        return sheet_name

    for offset, (name, url) in enumerate(batch, start=0):
        idx = start + offset
        json_file = Path(OUTPUT_DIR) / f"{safe_filename(name)}.json"

        if not json_file.exists():
            summary_rows.append({
                "restaurant_name": name,
                "restaurant_url": url,
                "total_items": 0,
                "items_with_ratings": 0,
                "categories_count": 0
            })
            continue

        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            summary_rows.append({
                "restaurant_name": name,
                "restaurant_url": url,
                "total_items": 0,
                "items_with_ratings": 0,
                "categories_count": 0
            })
            continue

        restaurant_name = data.get("restaurant_info", {}).get("name") or name
        restaurant_url = data.get("restaurant_info", {}).get("url") or url
        categories = data.get("menu_categories", {})

        total_items = 0
        items_with_ratings = 0
        categories_count = len(categories.keys())
        restaurant_rows = []

        for category, items in categories.items():
            for item in items:
                total_items += 1
                rating_percent, rating_count = normalize_rating_fields(item)
                if rating_count:
                    items_with_ratings += 1

                restaurant_rows.append({
                    "restaurant_name": restaurant_name,
                    "restaurant_url": restaurant_url,
                    "category": category,
                    "item_name": item.get("name"),
                    "price": item.get("price"),
                    "description": item.get("description"),
                    "rating_percent": rating_percent,
                    "rating_count": rating_count,
                    "promo_tag": item.get("most_liked_tag")
                })

        summary_rows.append({
            "restaurant_name": restaurant_name,
            "restaurant_url": restaurant_url,
            "total_items": total_items,
            "items_with_ratings": items_with_ratings,
            "categories_count": categories_count
        })

        if restaurant_rows:
            summary_rows[-1]["sheet_name"] = restaurant_name

    with pd.ExcelWriter(excel_name, engine="openpyxl") as writer:
        pd.DataFrame(summary_rows).to_excel(writer, sheet_name="Summary", index=False)

        existing = set(writer.sheets.keys())
        for offset, (name, url) in enumerate(batch, start=0):
            json_file = Path(OUTPUT_DIR) / f"{safe_filename(name)}.json"
            if not json_file.exists():
                continue
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                continue

            restaurant_name = data.get("restaurant_info", {}).get("name") or name
            categories = data.get("menu_categories", {})
            restaurant_rows = []

            for category, items in categories.items():
                for item in items:
                    rating_percent, rating_count = normalize_rating_fields(item)
                    restaurant_rows.append({
                        "restaurant_name": restaurant_name,
                        "restaurant_url": data.get("restaurant_info", {}).get("url") or url,
                        "category": category,
                        "item_name": item.get("name"),
                        "price": item.get("price"),
                        "description": item.get("description"),
                        "rating_percent": rating_percent,
                        "rating_count": rating_count,
                        "promo_tag": item.get("most_liked_tag")
                    })

            if restaurant_rows:
                sheet_name = sheet_safe_name(restaurant_name, existing)
                existing.add(sheet_name)
                pd.DataFrame(restaurant_rows).to_excel(writer, sheet_name=sheet_name, index=False)

    print(f"\n✅ Batch Excel saved: {excel_name}")
    return excel_name


def main():
    parser = argparse.ArgumentParser(description="Batch DoorDash scraper for Davis (95616)")
    parser.add_argument("--start", type=int, default=0, help="0-based start index")
    parser.add_argument("--count", type=int, default=10, help="Number of restaurants to scrape")
    parser.add_argument("--overwrite", action="store_true", help="Re-scrape even if JSON exists")
    parser.add_argument("--batch_id", default="1", help="Batch id used in output naming")
    args = parser.parse_args()

    restaurants = load_restaurants()
    print(f"Loaded {len(restaurants)} restaurants from davis_restaurants.txt")

    successful, failed, skipped = scrape_batch(
        restaurants, args.start, args.count, args.overwrite, args.batch_id
    )

    generate_batch_excel(restaurants, args.start, args.count, args.batch_id)

    if successful:
        print(f"\n🎉 Done! Scraped {len(successful)} restaurants in this batch.")
        print(f"   JSON files: {OUTPUT_DIR}/")
    else:
        print("\n⚠️ No restaurants were successfully scraped in this batch.")


if __name__ == "__main__":
    main()
