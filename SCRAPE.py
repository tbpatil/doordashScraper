import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import json
import time
import random
import re

class DoorDashScraper:
    def __init__(self, chrome_profile_path=None):
        self.driver = None
        self.chrome_profile_path = chrome_profile_path
        # Master storage for all items found during the active scroll
        self.master_menu = {} 
        self.seen_hashes = set() # To prevent duplicates
        self.setup_driver()
    
    def setup_driver(self):
        options = uc.ChromeOptions()
        if self.chrome_profile_path:
            options.add_argument(f"--user-data-dir={self.chrome_profile_path}")
        
        options.add_argument("--window-size=1920,1080")
        options.add_argument('--no-first-run')
        options.add_argument('--no-service-autorun')
        options.add_argument('--password-store=basic')
        
        print("Starting undetected browser...")
        self.driver = uc.Chrome(options=options, version_main=None)

    def scrape_restaurant(self, url):
        print(f"Navigating to: {url}")
        self.driver.get(url)
        
        print("\n!!! CHECK BROWSER !!!")
        print("Waiting 10 seconds for Cloudflare/Page Load...")
        time.sleep(10)
        
        # 1. Identify Categories First (so we know where to put items)
        soup_initial = BeautifulSoup(self.driver.page_source, 'lxml')
        categories_map = self._map_categories(soup_initial)
        
        # 2. ACTIVE SCRAPE: Vertical Scroll
        # We scroll down slowly, parsing visible items at every step
        self._active_vertical_scrape(categories_map)
        
        # 3. ACTIVE SCRAPE: Horizontal Carousels
        # We find carousels and scroll them sideways, parsing at every step
        self._active_horizontal_scrape(categories_map)
        
        # 4. Final Review Extraction
        reviews = self._extract_reviews(BeautifulSoup(self.driver.page_source, 'lxml'))
        
        return {
            'restaurant_info': self._extract_info(soup_initial),
            'menu_categories': self.master_menu,
            'reviews': reviews
        }

    def _map_categories(self, soup):
        """Creates a map of Line Numbers -> Category Names"""
        headers_map = []
        for h2 in soup.find_all('h2', attrs={'role': 'heading'}):
            text = h2.get_text().strip()
            if len(text) > 2 and text != "Menu":
                headers_map.append({'line': h2.sourceline or 0, 'name': text})
        
        headers_map.sort(key=lambda x: x['line'])
        print(f"Detected {len(headers_map)} categories.")
        return headers_map

    def _active_vertical_scrape(self, headers_map):
        """Scrolls down page in small chunks, scraping visible items."""
        print("Starting Active Vertical Scrape...")
        
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        
        # Scroll loop
        for i in range(20): # Adjust range for very long menus
            # 1. Capture current view
            self._parse_current_view(headers_map)
            
            # 2. Scroll down by ~800 pixels (approx one screen)
            self.driver.execute_script("window.scrollBy(0, 800);")
            time.sleep(1.5) # Wait for load
            
            # 3. Check if reached bottom
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            current_scroll = self.driver.execute_script("return window.scrollY + window.innerHeight")
            
            if current_scroll >= new_height:
                # Double check by waiting a bit (lazy load might add length)
                time.sleep(2)
                new_height = self.driver.execute_script("return document.body.scrollHeight")
                if current_scroll >= new_height:
                    break
        
        # Scroll back to top to prepare for horizontal check
        self.driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(2)

    def _active_horizontal_scrape(self, headers_map):
        """Finds carousels and scrolls them sideways while scraping."""
        print("Starting Active Horizontal Scrape...")
        
        # Re-find carousels (DOM might have changed)
        potential_carousels = self.driver.find_elements(By.XPATH, "//div[contains(@class, 'sc-')]")
        
        processed_count = 0
        for div in potential_carousels:
            try:
                # Check if scrollable
                is_scrollable = self.driver.execute_script(
                    "return arguments[0].scrollWidth > arguments[0].clientWidth", div
                )
                
                if is_scrollable:
                    processed_count += 1
                    # It's a carousel! Scroll it left-to-right
                    self._process_single_carousel(div, headers_map)
            except:
                continue
        print(f"Scraped {processed_count} carousels.")

    def _process_single_carousel(self, div_element, headers_map):
        """Scrolls a single carousel to the end, scraping at each step."""
        prev_scroll = -1
        attempts = 0
        
        while attempts < 10: # Safety break
            # 1. Scrape current view of this carousel
            # We grab the page source again to get the updated DOM state
            self._parse_current_view(headers_map)
            
            # 2. Check position
            curr_scroll = self.driver.execute_script("return arguments[0].scrollLeft", div_element)
            if curr_scroll == prev_scroll:
                break # Reached end
            prev_scroll = curr_scroll
            
            # 3. Scroll Right
            self.driver.execute_script("arguments[0].scrollLeft += 800;", div_element)
            time.sleep(0.8) # Wait for items to render
            attempts += 1

    def _parse_current_view(self, headers_map):
        """Parses the CURRENT state of the DOM and adds new items to master_menu"""
        soup = BeautifulSoup(self.driver.page_source, 'lxml')
        all_items = soup.find_all('div', attrs={'role': 'button'})
        
        for item_div in all_items:
            try:
                # 1. Validate Item
                raw_label = item_div.get('aria-label')
                if not raw_label: continue
                
                name = raw_label.split('$')[0].strip()
                
                # Deduplication Hash
                item_hash = f"{name}"
                if item_hash in self.seen_hashes:
                    continue
                
                # 2. Extract Data
                price = None
                price_tag = item_div.find(string=re.compile(r'\$\d+'))
                if price_tag: price = price_tag.strip()

                image = None
                img_tag = item_div.find('img')
                if img_tag: image = img_tag.get('src')
                
                # 3. Determine Category (Positional)
                item_line = item_div.sourceline or 0
                assigned_category = "Uncategorized"
                
                if headers_map:
                    # Items with line number 0 (sometimes happens with dynamic elements) 
                    # usually belong to the top carousel
                    if item_line == 0 and headers_map:
                         assigned_category = headers_map[0]['name']
                    else:
                        headers_above = [h for h in headers_map if h['line'] <= item_line]
                        if headers_above:
                            assigned_category = headers_above[-1]['name']
                        else:
                            assigned_category = headers_map[0]['name']

                # 4. Add to Master List
                if assigned_category not in self.master_menu:
                    self.master_menu[assigned_category] = []
                
                self.master_menu[assigned_category].append({
                    'name': name,
                    'price': price,
                    'image': image
                })
                
                self.seen_hashes.add(item_hash)
                
            except:
                continue

    def _extract_info(self, soup):
        name = soup.find('h1')
        return {'name': name.get_text().strip() if name else "Unknown"}

    def _extract_reviews(self, soup):
        rating = "None"
        try:
            rating_tag = soup.find('span', string=re.compile(r'^\d\.\d$'))
            if rating_tag: rating = rating_tag.get_text()
        except: pass
        return {'overall_rating': rating}

    def close(self):
        try: self.driver.quit()
        except: pass

def main():
    url = "https://www.doordash.com/store/mcdonald's-davis-720446/1025484/?event_type=autocomplete&pickup=false"
    profile_path = "/Users/apple/Documents/uthsc/doordashScraper"
    
    scraper = DoorDashScraper(chrome_profile_path=profile_path)
    try:
        data = scraper.scrape_restaurant(url)
        if data:
            print("\n" + "="*50)
            print(f"SUCCESS: {data['restaurant_info']['name']}")
            
            total = 0
            for cat, items in data['menu_categories'].items():
                print(f"\n📁 {cat} ({len(items)} items)")
                total += len(items)
                
            print(f"\nTOTAL ITEMS SCRAPED: {total}")
            
            with open('doordash_final_v12.json', 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
    finally:
        scraper.close()

if __name__ == "__main__":
    main()