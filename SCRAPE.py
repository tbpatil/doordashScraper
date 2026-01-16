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
        
        # 1b. Also create a map using Selenium for more accurate positioning
        selenium_sections = self._map_categories_selenium()
        
        # 2. ACTIVE SCRAPE: Vertical Scroll
        # We scroll down slowly, parsing visible items at every step
        self._active_vertical_scrape(categories_map, selenium_sections)
        
        # 3. ACTIVE SCRAPE: Horizontal Carousels
        # We find carousels and scroll them sideways, parsing at every step
        self._active_horizontal_scrape(categories_map, selenium_sections)
        
        # 4. Final Review Extraction
        reviews = self._extract_reviews(BeautifulSoup(self.driver.page_source, 'lxml'))
        
        # 5. Reorganize items into proper sections
        organized_menu = self._reorganize_by_sections()
        
        # Get restaurant info with URL
        restaurant_info = self._extract_info(soup_initial, url)
        
        return {
            'restaurant_info': restaurant_info,
            'menu_categories': organized_menu,
            'reviews': reviews
        }
    
    def _map_categories_selenium(self):
        """Create section map using Selenium for accurate positioning"""
        sections_map = []
        try:
            # Find section headers using Selenium - be more specific to get menu sections
            headers = self.driver.find_elements(By.CSS_SELECTOR, 
                "h2[role='heading'], h2.sc-fubCfw, h2[class*='heading'], h2[class*='Title'], h3[role='heading']")
            
            # Filter out non-menu sections (keep Most Ordered and Most Popular)
            excluded_sections = ['Trending Restaurants', 'Top Dishes Near Me', 
                                'Trending Categories', 'Nearby Cities', 'Get to Know Us', 
                                'Let Us Help You', 'Doing Business', 'Menu', 'Navigation', 'Header', 'Footer']
            
            for header in headers:
                try:
                    section_name = header.text.strip()
                    if (section_name and len(section_name) > 2 and 
                        section_name not in excluded_sections and
                        section_name.lower() not in ['menu', 'navigation', 'header', 'footer']):
                        location = header.location['y']
                        sections_map.append({
                            'name': section_name,
                            'y_position': location,
                            'element': header
                        })
                except:
                    continue
            
            # Sort by position
            sections_map.sort(key=lambda x: x['y_position'])
            print(f"Selenium detected {len(sections_map)} menu sections: {[s['name'] for s in sections_map]}")
        except Exception as e:
            print(f"Error mapping categories with Selenium: {e}")
        
        return sections_map

    def _map_categories(self, soup):
        """Creates a map of Line Numbers -> Category Names with improved detection"""
        headers_map = []
        
        # Filter out non-menu sections (keep Most Ordered and Most Popular)
        excluded_sections = ['Trending Restaurants', 'Top Dishes Near Me', 
                            'Trending Categories', 'Nearby Cities', 'Get to Know Us', 
                            'Let Us Help You', 'Doing Business', 'Menu', 'Navigation', 'Header', 'Footer']
        
        # Try multiple selectors for section headers
        header_selectors = [
            ('h2', {'role': 'heading'}),
            ('h2', {}),
            ('h3', {'role': 'heading'}),
            ('h3', {}),
            ('div', {'class': re.compile(r'.*[Tt]itle.*')}),
            ('div', {'data-testid': re.compile(r'.*section.*|.*category.*')})
        ]
        
        seen_headers = set()
        for tag, attrs in header_selectors:
            for header in soup.find_all(tag, attrs=attrs):
                try:
                    text = header.get_text().strip()
                    # Filter out generic headers, duplicates, and non-menu sections
                    if (text and len(text) > 2 and 
                        text not in excluded_sections and
                        text.lower() not in ['menu', 'navigation', 'header', 'footer'] and
                        text not in seen_headers):
                        line_num = header.sourceline or 0
                        headers_map.append({'line': line_num, 'name': text})
                        seen_headers.add(text)
                except:
                    continue
        
        # Remove duplicates and sort by line number
        unique_headers = {}
        for h in headers_map:
            if h['name'] not in unique_headers or h['line'] < unique_headers[h['name']]['line']:
                unique_headers[h['name']] = h
        
        headers_map = list(unique_headers.values())
        headers_map.sort(key=lambda x: x['line'])
        print(f"Detected {len(headers_map)} menu categories: {[h['name'] for h in headers_map]}")
        return headers_map

    def _active_vertical_scrape(self, headers_map, selenium_sections):
        """Scrolls down page in small chunks, scraping visible items."""
        print("Starting Active Vertical Scrape...")
        
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        
        # Scroll loop - increased range and better scrolling
        scroll_attempts = 0
        max_scroll_attempts = 50
        
        while scroll_attempts < max_scroll_attempts:
            # 1. Capture current view
            self._parse_current_view(headers_map, selenium_sections)
            
            # Re-map sections periodically
            if scroll_attempts % 5 == 0 and scroll_attempts > 0:
                soup_temp = BeautifulSoup(self.driver.page_source, 'lxml')
                headers_map = self._map_categories(soup_temp)
                selenium_sections = self._map_categories_selenium()
            
            # 2. Scroll down by ~600 pixels (smaller increments to catch more)
            self.driver.execute_script("window.scrollBy(0, 600);")
            time.sleep(1.0) # Wait for load
            
            # 3. Check if reached bottom
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            current_scroll = self.driver.execute_script("return window.scrollY + window.innerHeight")
            
            if current_scroll >= new_height - 100:  # Within 100px of bottom
                # Double check by waiting a bit (lazy load might add length)
                time.sleep(2)
                new_height = self.driver.execute_script("return document.body.scrollHeight")
                if current_scroll >= new_height - 100:
                    # One final parse at the bottom
                    self._parse_current_view(headers_map, selenium_sections)
                    break
            
            scroll_attempts += 1
        
        print(f"Completed vertical scroll after {scroll_attempts} attempts")
        
        # Scroll back to top to prepare for horizontal check
        self.driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(2)

    def _active_horizontal_scrape(self, headers_map, selenium_sections):
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
                    self._process_single_carousel(div, headers_map, selenium_sections)
            except:
                continue
        print(f"Scraped {processed_count} carousels.")

    def _process_single_carousel(self, div_element, headers_map, selenium_sections):
        """Scrolls a single carousel to the end, scraping at each step."""
        prev_scroll = -1
        attempts = 0
        
        while attempts < 10: # Safety break
            # 1. Scrape current view of this carousel
            # We grab the page source again to get the updated DOM state
            self._parse_current_view(headers_map, selenium_sections)
            
            # 2. Check position
            curr_scroll = self.driver.execute_script("return arguments[0].scrollLeft", div_element)
            if curr_scroll == prev_scroll:
                break # Reached end
            prev_scroll = curr_scroll
            
            # 3. Scroll Right
            self.driver.execute_script("arguments[0].scrollLeft += 800;", div_element)
            time.sleep(0.8) # Wait for items to render
            attempts += 1

    def _parse_current_view(self, headers_map, selenium_sections):
        """Parses the CURRENT state of the DOM and adds new items to master_menu with all required fields."""
        soup = BeautifulSoup(self.driver.page_source, 'lxml')

        # Broaden the definition of a "menu item" so we don't miss anything.
        # Many DoorDash items are rendered as "image-action-card" containers,
        # and some use <a> tags instead of <div>.
        # Also look for items with aria-label containing $ (price indicator)
        all_items = soup.select(
            "div[role='button'][aria-label*='$'], "
            "a[role='button'][aria-label*='$'], "
            "div[data-testid='image-action-card-container'], "
            "a[data-testid='image-action-card-container'], "
            "div[role='button'][aria-label], "
            "a[role='button'][aria-label]"
        )
        
        # Filter to only items that look like menu items
        # Remove items that are clearly not menu items (navigation, buttons, etc.)
        filtered_items = []
        excluded_keywords = ['close', 'search', 'filter', 'sort', 'back', 'next', 'previous', 'cart', 'checkout', 'sign in', 'sign up']
        
        for item in all_items:
            aria_label = item.get('aria-label', '')
            if not aria_label:
                # If no aria-label but it's an image-action-card, keep it
                if item.get('data-testid') == 'image-action-card-container':
                    filtered_items.append(item)
                continue
            
            aria_lower = aria_label.lower()
            # Skip items with excluded keywords (likely navigation/UI elements)
            if any(keyword in aria_lower for keyword in excluded_keywords):
                continue
            
            # Keep items that:
            # 1. Have $ in aria-label (price indicator)
            # 2. Are image-action-cards (DoorDash's main menu item container)
            # 3. Have substantial aria-label (likely a menu item name)
            if ('$' in aria_label or 
                item.get('data-testid') == 'image-action-card-container' or
                (len(aria_label) > 5 and not aria_lower.startswith('button'))):
                filtered_items.append(item)
        
        all_items = filtered_items
        
        # Also get items using Selenium for better positioning and in case
        # some dynamic elements don't show up cleanly in page_source yet.
        try:
            selenium_items = self.driver.find_elements(
                By.CSS_SELECTOR,
                "div[role='button'][aria-label], "
                "a[role='button'][aria-label], "
                "[data-testid='image-action-card-container']"
            )
        except Exception:
            selenium_items = []
        
        # Create a mapping of aria-label to Selenium element for position lookup
        selenium_item_map = {}
        for sel_item in selenium_items:
            try:
                aria_label = sel_item.get_attribute('aria-label')
                if aria_label:
                    selenium_item_map[aria_label] = sel_item
            except:
                continue
        
        for item_div in all_items:
            try:
                # 1. Extract item data with all required fields
                item_data = self._extract_item_data(item_div)
                if not item_data or not item_data.get('name'):
                    continue
                
                # 2. Deduplication Hash
                # Use both name and price in the hash so we don't accidentally
                # drop items that share the same name but have different sizes/prices.
                item_hash = f"{item_data['name']}|{item_data.get('price')}"
                if item_hash in self.seen_hashes:
                    continue
                
                # 3. Determine Category (Positional) - improved logic using both methods
                assigned_category = "Featured Items"  # Default category
                
                # Try Selenium-based positioning first (more accurate for dynamic content)
                if selenium_sections:
                    try:
                        # Find corresponding Selenium element
                        aria_label = item_div.get('aria-label')
                        if aria_label and aria_label in selenium_item_map:
                            sel_element = selenium_item_map[aria_label]
                            item_y = sel_element.location['y']
                            
                            # Find the section this item belongs to
                            # Find the last section header that appears before this item
                            for section in reversed(selenium_sections):
                                if item_y >= section['y_position']:
                                    assigned_category = section['name']
                                    break
                    except Exception as e:
                        pass
                
                # Fallback to BeautifulSoup line-based method
                if assigned_category == "Featured Items" and headers_map:
                    item_line = item_div.sourceline or 0
                    # Find the closest header that appears before this item
                    best_header = None
                    best_distance = float('inf')
                    
                    for header in headers_map:
                        header_line = header['line']
                        if item_line >= header_line:
                            # Item is after this header
                            distance = item_line - header_line
                            if distance < best_distance:
                                best_distance = distance
                                best_header = header
                    
                    if best_header:
                        assigned_category = best_header['name']
                    elif headers_map and len(headers_map) > 0:
                        # If item is before first header, use first header
                        assigned_category = headers_map[0]['name']
                
                # Final fallback: if still "Featured Items", try to use context
                # Don't assign to "Most Ordered" or "Most Popular" by default - let reorganization handle it
                if assigned_category == "Featured Items":
                    # Try to find any valid menu section from headers_map (excluding Most Ordered/Most Popular)
                    if headers_map and len(headers_map) > 0:
                        for header in headers_map:
                            header_name = header['name']
                            # Skip generic/fallback sections and Most Ordered/Most Popular (let reorganization handle those)
                            if header_name not in ['Individual Items', 'Uncategorized', 'Most Ordered', 'Most Popular']:
                                assigned_category = header_name
                                break

                # 4. Add to Master List
                if assigned_category not in self.master_menu:
                    self.master_menu[assigned_category] = []
                
                self.master_menu[assigned_category].append(item_data)
                self.seen_hashes.add(item_hash)
                
                # Debug: print category assignment for first few items
                if len(self.seen_hashes) <= 5:
                    print(f"  Item '{item_data['name']}' assigned to '{assigned_category}'")
                
            except Exception as e:
                print(f"Error parsing item: {e}")
                continue
    
    def _extract_item_data(self, item_div):
        """Extract all required fields from an item div"""
        item_data = {
            'name': None,
            'description': None,
            'price': None,
            'rating': None,
            'most_liked_tag': None,
            'image': None,
            'url': None
        }
        
        try:
            # Extract name from aria-label (most reliable)
            raw_label = item_div.get('aria-label')
            if raw_label:
                # Name is usually everything before the $ sign
                if '$' in raw_label:
                    item_data['name'] = raw_label.split('$')[0].strip()
                else:
                    item_data['name'] = raw_label.strip()
            
            # If no name from aria-label, try other methods
            if not item_data['name']:
                # Try finding name in spans or divs
                name_selectors = [
                    'span[class*="name"]',
                    'div[class*="name"]',
                    'h3', 'h4',
                    'span[class*="ItemName"]',
                    'div[class*="ItemName"]'
                ]
                for selector in name_selectors:
                    name_elem = item_div.select_one(selector)
                    if name_elem:
                        name_text = name_elem.get_text().strip()
                        if name_text and len(name_text) > 0:
                            item_data['name'] = name_text
                            break
            
            # Extract price - multiple methods
            # Method 1: From aria-label
            if raw_label and '$' in raw_label:
                price_match = re.search(r'\$[\d.]+', raw_label)
                if price_match:
                    item_data['price'] = price_match.group()
            
            # Method 2: Search for price pattern in text content
            if not item_data['price']:
                price_text = item_div.get_text()
                price_match = re.search(r'\$[\d.]+', price_text)
                if price_match:
                    item_data['price'] = price_match.group()
            
            # Method 3: Look for specific price elements
            if not item_data['price']:
                price_elem = item_div.find(string=re.compile(r'\$[\d.]+'))
                if price_elem:
                    price_match = re.search(r'\$[\d.]+', price_elem)
                    if price_match:
                        item_data['price'] = price_match.group()
            
            # Method 4: Look in spans with price-related classes
            if not item_data['price']:
                price_selectors = [
                    'span[class*="price"]',
                    'div[class*="price"]',
                    'span[class*="Price"]',
                    '[data-testid*="price"]'
                ]
                for selector in price_selectors:
                    price_elem = item_div.select_one(selector)
                    if price_elem:
                        price_text = price_elem.get_text()
                        price_match = re.search(r'\$[\d.]+', price_text)
                        if price_match:
                            item_data['price'] = price_match.group()
                            break
            
            # Extract description
            desc_selectors = [
                'p[class*="description"]',
                'span[class*="description"]',
                'div[class*="description"]',
                '[data-testid*="description"]',
                'p[class*="Description"]'
            ]
            for selector in desc_selectors:
                desc_elem = item_div.select_one(selector)
                if desc_elem:
                    desc_text = desc_elem.get_text().strip()
                    if desc_text and len(desc_text) > 0:
                        item_data['description'] = desc_text
                        break
            
            # Extract rating (e.g., "84% liked by 175 people" or star ratings)
            rating_selectors = [
                'span[class*="rating"]',
                'div[class*="rating"]',
                'span[class*="Rating"]',
                'span[class*="like"]',
                'div[class*="like"]',
                'span[class*="percentage"]',
                '[data-testid*="rating"]',
                'span[aria-label*="star"]'
            ]
            for selector in rating_selectors:
                rating_elem = item_div.select_one(selector)
                if rating_elem:
                    rating_text = rating_elem.get_text().strip()
                    # Look for percentage or "liked" pattern
                    if '%' in rating_text or 'liked' in rating_text.lower() or 'star' in rating_text.lower():
                        item_data['rating'] = rating_text
                        break
            
            # Extract "#1 most liked" tag or similar badges
            tag_selectors = [
                'div[data-testid*="tag"]',
                'div[data-testid*="badge"]',
                'div[class*="Tag"]',
                'span[class*="tag"]',
                'div[class*="badge"]',
                'span[class*="badge"]',
                'div[class*="Badge"]',
                'div[class*="promo"]',
                'span[class*="promo"]'
            ]
            for selector in tag_selectors:
                tag_elems = item_div.select(selector)
                for tag_elem in tag_elems:
                    tag_text = tag_elem.get_text().strip()
                    if tag_text:
                        # Prioritize "#1 most liked" type tags
                        if '#' in tag_text and 'most liked' in tag_text.lower():
                            item_data['most_liked_tag'] = tag_text
                            break
                        # Also check for other promotional tags
                        elif 'most liked' in tag_text.lower() or 'most' in tag_text.lower():
                            if not item_data['most_liked_tag'] or 'most liked' not in item_data['most_liked_tag'].lower():
                                item_data['most_liked_tag'] = tag_text
                        # Other promotional tags
                        elif len(tag_text) < 50 and tag_text not in ['$', '']:
                            if not item_data['most_liked_tag']:
                                item_data['most_liked_tag'] = tag_text
                if item_data['most_liked_tag'] and 'most liked' in item_data['most_liked_tag'].lower():
                    break
            
            # Extract image URL
            img_tag = item_div.find('img')
            if img_tag:
                img_src = img_tag.get('src')
                if img_src:
                    item_data['image'] = img_src
        
        except Exception as e:
            print(f"Error extracting item data: {e}")
        
        return item_data

    def _extract_info(self, soup, url):
        """Extract restaurant information including name, URL, and cuisine"""
        info = {
            'name': None,
            'url': url,
            'cuisine': None,
            'price_range': None
        }
        
        # Extract restaurant name
        try:
            name = soup.find('h1')
            if name:
                info['name'] = name.get_text().strip()
        except:
            pass
        
        # Extract cuisine and price range - try multiple selectors
        try:
            # Look for cuisine information
            cuisine_selectors = [
                "span[class*='cuisine']",
                "div[class*='cuisine']",
                "[data-testid*='cuisine']",
                "[class*='Cuisine']"
            ]
            
            for selector in cuisine_selectors:
                try:
                    elements = soup.select(selector)
                    for elem in elements:
                        text = elem.get_text().strip()
                        # Filter for reasonable cuisine text
                        if text and len(text) < 100 and 'cuisine' in text.lower():
                            info['cuisine'] = text
                            break
                except:
                    continue
            
            # Also try to extract from page text - look for patterns like "Fast Food", "American", etc.
            if not info['cuisine']:
                page_text = soup.get_text()
                # Common cuisine patterns
                cuisine_patterns = ['Fast Food', 'American', 'Italian', 'Chinese', 'Mexican', 'Japanese']
                for pattern in cuisine_patterns:
                    if pattern in page_text[:5000]:  # Check first 5000 chars
                        info['cuisine'] = pattern
                        break
            
            # Extract price range (if available) - look for $ symbols indicating price level
            price_indicators = soup.find_all(string=re.compile(r'\$\$\$|\$\$|\$'))
            if price_indicators:
                # DoorDash sometimes shows price range like "$$" or "$"
                price_text = price_indicators[0].strip()
                if price_text:
                    info['price_range'] = price_text
                    
        except Exception as e:
            print(f"Error extracting restaurant info: {e}")
        
        return info
    
    def _reorganize_by_sections(self):
        """Reorganize all scraped items into proper sections based on item names and detected sections"""
        # Define category keywords for intelligent categorization
        # Order matters - more specific categories first
        category_keywords = {
            'Happy Meal': ['happy meal'],
            'Fish': ['fish', 'filet-o-fish'],
            'Fries': ['fries', 'french fries'],
            'Shareables': ['pack', '40 pc', 'combo pack', 'chicken pack', 'burger pack', 'favorites for 4', 'classic', 'quarter pounder pack', 'big mac pack'],
            'McCafé® Coffees': ['latte', 'frappé', 'frappe', 'cappuccino', 'mocha', 'caramel', 'café', 'premium roast', 'french vanilla', 'iced french vanilla', 'iced caramel', 'iced mocha', 'iced latte', 'iced coffee', 'premium hot chocolate', 'premium roast'],
            'Sweets & Treats': ['mcflurry', 'shake', 'cookie', 'sundae', 'ice cream', 'holiday pie', 'apple pie', 'strawberry & crème', 'vanilla shake', 'chocolate shake', 'strawberry shake'],
            'Burgers': ['burger', 'quarter pounder', 'big mac', 'mcdouble', 'double', 'cheeseburger', 'hamburger', 'daily double', 'bacon quarter', 'triple', 'bacon mcdouble'],
            'Chicken': ['chicken', 'mcnuggets', 'mccrispy', 'mcchicken', 'chicken strips', 'nuggets', 'snack wrap', 'mccrispy strips', 'mccrispy™ strips', 'mccrispy™ meal', 'spicy mccrispy', 'deluxe mccrispy', 'chicken mcnugget', 'piece mccrispy', 'mccrispy™ strips meal'],
            'Beverages': ['coke', 'sprite', 'dr pepper', 'diet', 'iced tea', 'lemonade', 'juice', 'water', 'smoothie', 'fanta', 'powerade', 'orange juice', 'apple juice', 'milk', 'hot tea', 'dasani', 'chocolate milk', 'hi-c', 'sweet iced tea', 'unsweetened iced tea', 'frozen'],
            'Condiments': ['napkin', 'spoon', 'fork', 'ketchup', 'mustard', 'mayo', 'salt', 'pepper', 'sugar', 'creamer', 'straw', 'syrup', 'dipping sauce', 'salsa', 'preserve', 'stirrer', 'splenda', 'butter', 'hot mustard', 'strip dip'],
            'Sides & More': ['apple slices', 'salad', 'bacon strips', 'apple'],
            'Extra Value Meals': ['meal']  # Items with "Meal" in name
        }
        
        # Final organized menu
        organized = {}
        
        # Get all items from current master_menu
        # Collect all items together, but track which were explicitly in "Most Ordered" or "Most Popular"
        most_ordered_item_names = set()
        most_popular_item_names = set()
        all_items = []
        
        # First pass: track items that were explicitly in Most Ordered/Most Popular
        for section_name, items in self.master_menu.items():
            if section_name == 'Most Ordered':
                for item in items:
                    item_key = f"{item.get('name')}|{item.get('price')}"
                    most_ordered_item_names.add(item_key)
                    all_items.append(item)
            elif section_name == 'Most Popular':
                for item in items:
                    item_key = f"{item.get('name')}|{item.get('price')}"
                    most_popular_item_names.add(item_key)
                    all_items.append(item)
            else:
                all_items.extend(items)
        
        # Remove duplicates based on name+price
        seen = set()
        unique_items = []
        for item in all_items:
            item_key = f"{item.get('name')}|{item.get('price')}"
            if item_key not in seen:
                seen.add(item_key)
                unique_items.append(item)
        
        # Categorize each item
        for item in unique_items:
            item_key = f"{item.get('name')}|{item.get('price')}"
            item_name = item.get('name', '').lower()
            categorized = False
            is_meal = 'meal' in item_name
            has_promo_tag = item.get('most_liked_tag') is not None
            
            # Check if this item was explicitly in "Most Ordered" or "Most Popular" during scraping
            was_in_most_ordered = item_key in most_ordered_item_names
            was_in_most_popular = item_key in most_popular_item_names
            
            # Priority 1: Items explicitly in "Most Ordered" or "Most Popular" stay there
            if was_in_most_ordered:
                if 'Most Ordered' not in organized:
                    organized['Most Ordered'] = []
                organized['Most Ordered'].append(item)
                categorized = True
                continue
            elif was_in_most_popular:
                if 'Most Popular' not in organized:
                    organized['Most Popular'] = []
                organized['Most Popular'].append(item)
                categorized = True
                continue
            
            # Priority 2: Happy Meal (most specific)
            if 'happy meal' in item_name:
                if 'Happy Meal' not in organized:
                    organized['Happy Meal'] = []
                organized['Happy Meal'].append(item)
                categorized = True
                continue
            
            # Priority 3: Find content category FIRST (before meals/featured logic)
            # This allows items to be in both their content category AND meals/featured
            # Check Chicken first (before Shareables) since "40 pc" matches Shareables but chicken items should be in Chicken
            content_category = None
            shareable_category = None
            
            # First, check if it's a chicken item (before checking Shareables)
            if any(kw in item_name for kw in ['mccrispy', 'mcchicken', 'mcnuggets', 'chicken', 'nuggets', 'snack wrap']):
                content_category = 'Chicken'
            
            # Check Shareables (items can be in both Chicken AND Shareables)
            if any(kw in item_name for kw in ['pack', '40 pc', 'combo pack', 'chicken pack', 'burger pack', 'favorites for 4', 'classic', 'quarter pounder pack', 'big mac pack']) and not any(kw in item_name for kw in ['& 2 large fries', '& 2 medium fries']):
                shareable_category = 'Shareables'
            
            # If not chicken, check other content categories
            if not content_category:
                for category, keywords in category_keywords.items():
                    if category in ['Extra Value Meals', 'Happy Meal', 'Chicken', 'Shareables']:
                        continue  # Skip these (already handled)
                    
                    for keyword in keywords:
                        if keyword in item_name:
                            # Skip "pie" keyword for Sweets if item contains "piece" (likely chicken strips)
                            if category == 'Sweets & Treats' and keyword == 'pie' and 'piece' in item_name:
                                continue
                            content_category = category
                            break
                    
                    if content_category:
                        break
            
            # Priority 4: Meals go to "Extra Value Meals" (unless Happy Meal)
            # Also add to content category if applicable
            if is_meal:
                if 'Extra Value Meals' not in organized:
                    organized['Extra Value Meals'] = []
                organized['Extra Value Meals'].append(item)
                categorized = True
                
                # Also add meals to their content category (Chicken, Burgers, Fish, etc.)
                if content_category and content_category in ['Chicken', 'Burgers', 'Fish', 'Fries']:
                    if content_category not in organized:
                        organized[content_category] = []
                    if item not in organized[content_category]:
                        organized[content_category].append(item)
                
                # Also add to Shareables if applicable
                if shareable_category:
                    if shareable_category not in organized:
                        organized[shareable_category] = []
                    if item not in organized[shareable_category]:
                        organized[shareable_category].append(item)
            
            # Priority 5: Items with promotional tags go to "Featured Items"
            # Also add to content category if applicable
            elif has_promo_tag:
                if 'Featured Items' not in organized:
                    organized['Featured Items'] = []
                organized['Featured Items'].append(item)
                categorized = True
                
                # Also add featured items to their content category
                if content_category:
                    if content_category not in organized:
                        organized[content_category] = []
                    if item not in organized[content_category]:
                        organized[content_category].append(item)
                
                # Also add to Shareables if applicable
                if shareable_category:
                    if shareable_category not in organized:
                        organized[shareable_category] = []
                    if item not in organized[shareable_category]:
                        organized[shareable_category].append(item)
            
            # Priority 6: For non-meal, non-featured items, add to content category
            elif content_category or shareable_category:
                if content_category:
                    if content_category not in organized:
                        organized[content_category] = []
                    organized[content_category].append(item)
                    categorized = True
                
                # Also add to Shareables if applicable (items can be in both)
                if shareable_category:
                    if shareable_category not in organized:
                        organized[shareable_category] = []
                    if item not in organized[shareable_category]:
                        organized[shareable_category].append(item)
                    categorized = True
            
            # Final fallback: put in "Individual Items"
            if not categorized:
                if 'Individual Items' not in organized:
                    organized['Individual Items'] = []
                organized['Individual Items'].append(item)
        
        # Sort categories in preferred order (exactly as requested)
        preferred_order = [
            'Featured Items',
            'Most Ordered',
            'Extra Value Meals',
            'Burgers',
            'Chicken',
            'Fish',
            'Fries',
            'Happy Meal',
            'Beverages',
            'Sweets & Treats',
            'McCafé® Coffees',
            'Shareables',
            'Condiments',
            'Sides & More',
            'Individual Items',
            'Most Popular'
        ]
        
        # Items in Most Ordered/Most Popular are already handled in the categorization loop above
        
        # Create final ordered dictionary
        final_menu = {}
        for category in preferred_order:
            if category in organized and len(organized[category]) > 0:
                final_menu[category] = organized[category]
            # Always include "Most Ordered" and "Most Popular" even if empty
            elif category in ['Most Ordered', 'Most Popular']:
                final_menu[category] = []
        
        # Add any remaining categories not in preferred order
        for category, items in organized.items():
            if category not in final_menu and len(items) > 0:
                final_menu[category] = items
        
        # Ensure "Most Ordered" and "Most Popular" exist even if empty
        if 'Most Ordered' not in final_menu:
            final_menu['Most Ordered'] = []
        if 'Most Popular' not in final_menu:
            final_menu['Most Popular'] = []
        
        return final_menu

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