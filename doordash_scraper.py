"""
DoorDash Restaurant Page Scraper
Scrapes restaurant information, menu items, and reviews from DoorDash restaurant pages.

DYNAMIC WEBSITE CHALLENGES & SOLUTIONS:
========================================

DoorDash is a highly dynamic website that presents several challenges:

1. **JavaScript-Rendered Content**: 
   - Most menu items are loaded dynamically via JavaScript
   - Content may not be immediately available when page loads
   - SOLUTION: Uses Selenium with WebDriverWait and explicit waits
   - Uses human-like scrolling to trigger lazy loading

2. **Cloudflare Protection**:
   - DoorDash uses Cloudflare to detect automated access
   - May block headless browsers or automated tools
   - SOLUTION: Uses real Chrome profile with user-agent spoofing
   - Implements human-like delays and scrolling patterns

3. **Dynamic CSS Classes**:
   - DoorDash uses dynamically generated CSS class names (e.g., sc-62d4eb3a-21)
   - These classes change frequently, breaking selectors
   - SOLUTION: Uses multiple fallback selectors and aria-labels
   - Searches for patterns (like price patterns) in text content

4. **Lazy Loading**:
   - Menu items load as user scrolls
   - Horizontal carousels require scrolling to reveal items
   - SOLUTION: Implements comprehensive scrolling (vertical and horizontal)
   - Parses content at multiple scroll positions

5. **Price Extraction Issues**:
   - Prices may be in different locations (aria-label, spans, etc.)
   - Some items may not display prices until clicked
   - SOLUTION: Multiple extraction methods with fallbacks
   - Searches entire element text for price patterns

ALTERNATIVE SOLUTIONS IF ISSUES PERSIST:
=========================================

1. **API Approach** (if available):
   - Check if DoorDash has a public API
   - Use API endpoints instead of web scraping
   - More reliable but may require authentication

2. **Playwright with Stealth**:
   - Use playwright-stealth plugin
   - Better at bypassing bot detection
   - More modern than Selenium

3. **Proxy Rotation**:
   - Rotate IP addresses to avoid rate limiting
   - Use residential proxies for better success

4. **Browser Automation with Real Browser**:
   - Use undetected-chromedriver (already in SCRAPE.py)
   - Better at mimicking real user behavior

5. **Manual Inspection**:
   - Inspect page source after full load
   - Identify stable selectors (data-testid attributes preferred)
   - Update selectors when DoorDash changes structure

6. **Rate Limiting**:
   - Add delays between requests
   - Implement exponential backoff
   - Respect robots.txt

NOTE: This scraper may need selector updates if DoorDash changes their HTML structure.
Always test with headless=False first to visually verify what's being scraped.
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import json
import time
import random
from typing import Dict, List, Optional
import re


class DoorDashScraper:
    def __init__(self, headless: bool = False, chrome_profile_path: Optional[str] = None):
        """
        Initialize the DoorDash scraper.
        
        Args:
            headless: Run browser in headless mode (default: False)
            chrome_profile_path: Path to Chrome user data directory (default: None, uses default profile)
        """
        self.driver = None
        self.wait = None
        self.headless = headless
        self.chrome_profile_path = chrome_profile_path
        self.setup_driver()
    
    def setup_driver(self):
        """Setup Chrome driver with appropriate options."""
        options = webdriver.ChromeOptions()
        
        # Use real Chrome profile to bypass Cloudflare
        if self.chrome_profile_path:
            options.add_argument(f"--user-data-dir={self.chrome_profile_path}")
        
        # options.add_argument("--headless")  # run in background
        if self.headless:
            options.add_argument('--headless')
        
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        options.add_argument('user-agent = Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36')
        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        self.wait = WebDriverWait(self.driver, 20)
    
    def _human_delay(self, min_seconds: float = 1.0, max_seconds: float = 3.0):
        """
        Add a random delay to mimic human behavior.
        
        Args:
            min_seconds: Minimum delay in seconds
            max_seconds: Maximum delay in seconds
        """
        delay = random.uniform(min_seconds, max_seconds)
        time.sleep(delay)
    
    def _human_scroll(self, pixels: int = None):
        """
        Scroll the page in a human-like manner (gradual, not instant).
        
        Args:
            pixels: Number of pixels to scroll (if None, scrolls a random amount)
        """
        if pixels is None:
            pixels = random.randint(300, 800)
        
        # Scroll gradually using smooth scrolling
        self.driver.execute_script(f"window.scrollBy(0, {pixels});")
        self._human_delay(0.5, 1.5)
        
    def get_shadow_root(self, element):
        return self.driver.execute_script("return arguments[0].shadowRoot", element)

    
    def scrape_restaurant(self, url: str) -> Dict:
        """
        Scrape all information from a DoorDash restaurant page.
        
        Args:
            url: URL of the DoorDash restaurant page
            
        Returns:
            Dictionary containing restaurant info, menu items, and reviews
        """
        print(f"Scraping restaurant page: {url}")
        self.driver.get(url)
        
        # Wait for initial page load with human-like delay
        self._human_delay(3, 6)  # Random delay between 3-6 seconds
        
        # Scroll to load dynamic content
        self._scroll_page()
        
        # Small pause before extraction
        self._human_delay(1, 2)
        
        # Extract restaurant info
        print("Extracting restaurant information...")
        result = {
            'restaurant_info': self._extract_restaurant_info(url),
        }
        self._human_delay(1, 2)
        
        # Extract menu items organized by sections
        print("Extracting menu items...")
        result['menu_categories'] = self._extract_menu_items()
        self._human_delay(1, 2)
        
        # Extract reviews
        print("Extracting reviews...")
        result['reviews'] = self._extract_reviews()
        
        return result
    
    def _scroll_page(self):
        """Scroll the page to load dynamic content in a human-like manner."""
        print("Scrolling page to load content...")
        
        # Get initial page height
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        current_position = 0
        scroll_attempts = 0
        max_scroll_attempts = 50  # Prevent infinite loops
        
        while scroll_attempts < max_scroll_attempts:
            # Human-like scroll: scroll in chunks, not all at once
            scroll_amount = random.randint(400, 700)
            current_position += scroll_amount
            
            # Scroll gradually
            self._human_scroll(scroll_amount)
            
            # Occasionally pause longer (like a human reading)
            if random.random() < 0.3:  # 30% chance
                self._human_delay(1.5, 3.0)
            
            # Check if we've reached the bottom
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            scroll_position = self.driver.execute_script("return window.pageYOffset + window.innerHeight")
            
            # If page height increased, reset position tracking
            if new_height > last_height:
                last_height = new_height
                current_position = scroll_position
            
            # Check if we're at or near the bottom
            if scroll_position >= last_height - 100:
                # Sometimes scroll a bit more to trigger lazy loading
                self._human_scroll(random.randint(200, 400))
                self._human_delay(1, 2)
                
                # Check one more time if content loaded
                final_height = self.driver.execute_script("return document.body.scrollHeight")
                if final_height == last_height:
                    break
                last_height = final_height
            
            scroll_attempts += 1
        
        # Scroll back to top gradually (human-like)
        print("Scrolling back to top...")
        scroll_to_top_steps = random.randint(5, 10)
        total_height = self.driver.execute_script("return window.pageYOffset")
        step_size = total_height / scroll_to_top_steps
        
        for _ in range(scroll_to_top_steps):
            self.driver.execute_script(f"window.scrollBy(0, -{step_size});")
            self._human_delay(0.2, 0.5)
        
        # Final small delay at top
        self._human_delay(0.5, 1.0)
    
    def _extract_restaurant_info(self, url: str) -> Dict:
        """Extract restaurant information."""
        info = {
            'name': None,
            'url': url,
            'cuisine': None
        }
        
        try:
            # Restaurant name - try multiple selectors
            name_selectors = [
                "h1[data-testid='store-name']",
                "h1",
                "[data-testid='store-header-name']",
                ".store-name",
                "h1.sc-fubCfw"
            ]
            
            for selector in name_selectors:
                try:
                    name_element = self.wait.until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    # Small delay after finding element (human-like)
                    self._human_delay(0.3, 0.7)
                    info['name'] = name_element.text.strip()
                    if info['name']:
                        break
                except:
                    continue
            
            # Small delay before next extraction
            self._human_delay(0.5, 1.0)
            
            # Cuisine - try multiple selectors
            cuisine_selectors = [
                "[data-testid='store-cuisine']",
                ".cuisine",
                "[class*='cuisine']",
                "span[class*='StoreHeader']"
            ]
            
            for selector in cuisine_selectors:
                try:
                    cuisine_elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for elem in cuisine_elements:
                        text = elem.text.strip()
                        if text and len(text) < 100:  # Reasonable cuisine name length
                            info['cuisine'] = text
                            break
                    if info['cuisine']:
                        break
                except:
                    continue
            
        except Exception as e:
            print(f"Error extracting restaurant info: {e}")
        
        return info
    
    def _extract_menu_items(self) -> Dict:
        """Extract menu items organized by sections."""
        menu_categories = {}
        
        try:
            # First, find all section headers (h2 elements that mark menu categories)
            section_headers = self.driver.find_elements(
                By.CSS_SELECTOR,
                "h2[role='heading'], h2.sc-fubCfw, h2[class*='heading'], h2[class*='Title']"
            )
            
            # Also try to find sections by data-testid or other attributes
            alt_sections = self.driver.find_elements(
                By.CSS_SELECTOR,
                "[data-testid*='section'], [data-testid*='category'], [class*='MenuSection']"
            )
            
            # Get all menu item cards - DoorDash uses image-action-card-container
            all_cards = self.driver.find_elements(
                By.CSS_SELECTOR,
                "[data-testid='image-action-card-container'], [role='button'][aria-label*='$'], div[role='button']"
            )
            
            print(f"Found {len(section_headers)} section headers and {len(all_cards)} item cards")
            
            # If we found section headers, organize items by section
            if section_headers:
                # Create a map of section positions
                sections_map = []
                for header in section_headers:
                    try:
                        section_name = header.text.strip()
                        if section_name and len(section_name) > 1 and section_name.lower() != "menu":
                            # Get position of this header
                            location = header.location['y']
                            sections_map.append({
                                'name': section_name,
                                'y_position': location,
                                'element': header
                            })
                    except:
                        continue
                
                # Sort sections by position
                sections_map.sort(key=lambda x: x['y_position'])
                
                # Assign items to sections based on their position
                for card in all_cards:
                    try:
                        item_data = self._extract_item_details(card)
                        if item_data and item_data.get('name'):
                            # Get card position
                            card_location = card.location['y']
                            
                            # Find which section this item belongs to
                            assigned_section = "Featured Items"  # Default
                            for i, section in enumerate(sections_map):
                                if card_location >= section['y_position']:
                                    assigned_section = section['name']
                                else:
                                    break
                            
                            # Add to appropriate section
                            if assigned_section not in menu_categories:
                                menu_categories[assigned_section] = []
                            
                            menu_categories[assigned_section].append(item_data)
                    except Exception as e:
                        print(f"Error processing card: {e}")
                        continue
            else:
                # Fallback: if no sections found, try to extract all items and put in "Featured Items"
                print("No section headers found, using fallback method")
                for card in all_cards:
                    try:
                        item_data = self._extract_item_details(card)
                        if item_data and item_data.get('name'):
                            if "Featured Items" not in menu_categories:
                                menu_categories["Featured Items"] = []
                            menu_categories["Featured Items"].append(item_data)
                    except Exception as e:
                        continue
            
        except Exception as e:
            print(f"Error extracting menu items: {e}")
            import traceback
            traceback.print_exc()
        
        return menu_categories
    
    def _extract_item_details(self, item_element) -> Optional[Dict]:
        """Extract all details from a single menu item card."""
        try:
            item_data = {
                'name': None,
                'description': None,
                'price': None,
                'rating': None,
                'most_liked_tag': None,
                'image': None
            }
            
            # Method 1: Try aria-label (often contains name and price)
            try:
                aria_label = item_element.get_attribute('aria-label')
                if aria_label:
                    # Extract name (everything before $)
                    if '$' in aria_label:
                        item_data['name'] = aria_label.split('$')[0].strip()
                        # Try to extract price from aria-label
                        price_match = re.search(r'\$[\d.]+', aria_label)
                        if price_match and not item_data['price']:
                            item_data['price'] = price_match.group()
                    else:
                        item_data['name'] = aria_label.strip()
            except:
                pass
            
            # Method 2: Extract name from various selectors
            if not item_data['name']:
                name_selectors = [
                    "span.sc-62d4eb3a-21",
                    "span[class*='sc-62d4eb3a-21']",
                    "[data-testid='menu-item-name']",
                    "h3", "h4",
                    "span[class*='name']",
                    "div[class*='ItemName']",
                    "span[class*='ItemName']"
                ]
                
                for selector in name_selectors:
                    try:
                        name_elem = item_element.find_elements(By.CSS_SELECTOR, selector)
                        if name_elem:
                            name_text = name_elem[0].text.strip()
                            if name_text and len(name_text) > 0:
                                item_data['name'] = name_text
                                break
                    except:
                        continue
            
            # Extract price - try multiple methods
            if not item_data['price']:
                # Method 1: Look for price in specific spans
                price_selectors = [
                    "span.sc-62d4eb3a-10",
                    "span[class*='sc-62d4eb3a-10']",
                    "[data-testid='menu-item-price']",
                    "span[class*='price']",
                    "div[class*='price']",
                    "span[class*='Price']"
                ]
                
                for selector in price_selectors:
                    try:
                        price_elems = item_element.find_elements(By.CSS_SELECTOR, selector)
                        for price_elem in price_elems:
                            price_text = price_elem.text.strip()
                            # Look for price pattern ($X.XX or X.XX)
                            price_match = re.search(r'\$?[\d.]+', price_text)
                            if price_match:
                                price_val = price_match.group()
                                if not price_val.startswith('$'):
                                    price_val = '$' + price_val
                                item_data['price'] = price_val
                                break
                        if item_data['price']:
                            break
                    except:
                        continue
                
                # Method 2: Search all text in the element for price pattern
                if not item_data['price']:
                    try:
                        all_text = item_element.text
                        price_match = re.search(r'\$[\d.]+', all_text)
                        if price_match:
                            item_data['price'] = price_match.group()
                    except:
                        pass
            
            # Extract description
            description_selectors = [
                "[data-testid='menu-item-description']",
                "p[class*='description']",
                "span[class*='description']",
                "div[class*='description']",
                "p[class*='Description']"
            ]
            
            for selector in description_selectors:
                try:
                    desc_elems = item_element.find_elements(By.CSS_SELECTOR, selector)
                    if desc_elems:
                        desc_text = desc_elems[0].text.strip()
                        if desc_text and len(desc_text) > 0:
                            item_data['description'] = desc_text
                            break
                except:
                    continue
            
            # Extract rating (e.g., "84% liked by 175 people" or "4.5 stars")
            rating_selectors = [
                "[class*='rating']",
                "[class*='Rating']",
                "[class*='like']",
                "[class*='Like']",
                "span[class*='percentage']",
                "[data-testid*='rating']",
                "span[aria-label*='star']"
            ]
            
            for selector in rating_selectors:
                try:
                    rating_elems = item_element.find_elements(By.CSS_SELECTOR, selector)
                    for rating_elem in rating_elems:
                        rating_text = rating_elem.text.strip()
                        # Look for percentage pattern (84% liked) or star rating
                        if '%' in rating_text or 'liked' in rating_text.lower() or 'star' in rating_text.lower():
                            item_data['rating'] = rating_text
                            break
                    if item_data['rating']:
                        break
                except:
                    continue
            
            # Extract "#1 most liked" tag or similar badges
            tag_selectors = [
                "div[data-testid^='fios_offer']",
                "div.TagWrapper-sc-nj0mkn-2",
                "div[class*='Tag']",
                "span[class*='tag']",
                "div[class*='badge']",
                "span[class*='badge']",
                "div[class*='Badge']",
                "[data-testid*='tag']",
                "[data-testid*='badge']"
            ]
            
            for selector in tag_selectors:
                try:
                    tag_elems = item_element.find_elements(By.CSS_SELECTOR, selector)
                    for tag_elem in tag_elems:
                        tag_text = tag_elem.text.strip()
                        if tag_text:
                            # Check if it's a "#1 most liked" type tag
                            if '#' in tag_text or 'most liked' in tag_text.lower() or 'most' in tag_text.lower():
                                item_data['most_liked_tag'] = tag_text
                                break
                            # Also check for other promotional tags
                            elif len(tag_text) < 50 and tag_text not in ['$', '']:
                                # Might be a promo tag, but prioritize "#1 most liked"
                                if not item_data['most_liked_tag']:
                                    item_data['most_liked_tag'] = tag_text
                    if item_data['most_liked_tag'] and 'most liked' in item_data['most_liked_tag'].lower():
                        break
                except:
                    continue
            
            # Extract image URL
            try:
                img_el = item_element.find_element(By.CSS_SELECTOR, "img")
                img_src = img_el.get_attribute("src")
                if img_src:
                    item_data['image'] = img_src
            except:
                try:
                    # Try other image selectors
                    img_el = item_element.find_element(By.CSS_SELECTOR, "img.StyledImg-sc-mcg5q6-0")
                    img_src = img_el.get_attribute("src")
                    if img_src:
                        item_data['image'] = img_src
                except:
                    pass
            
            # Only return if we got at least a name
            if item_data['name']:
                return item_data
            
        except Exception as e:
            print(f"Error extracting item details: {e}")
            import traceback
            traceback.print_exc()
        
        return None
    
    def _extract_reviews(self) -> Dict:
        """Extract reviews section information."""
        reviews_data = {
            'overall_rating': None,
            'individual_reviews': []
        }
        
        try:
            # Overall rating (e.g., "4.5/5 stars")
            rating_selectors = [
                "[data-testid='store-rating']",
                "[class*='rating']",
                "[class*='Rating']",
                "[class*='overall-rating']",
                "span[class*='star']"
            ]
            
            for selector in rating_selectors:
                try:
                    rating_elems = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for rating_elem in rating_elems:
                        rating_text = rating_elem.text.strip()
                        # Look for X.X/5 or X.X stars pattern
                        if re.search(r'\d+\.?\d*\s*/\s*5', rating_text) or 'star' in rating_text.lower():
                            reviews_data['overall_rating'] = rating_text
                            break
                    if reviews_data['overall_rating']:
                        break
                except:
                    continue
            
            # Individual reviews (horizontal scrollable)
            # First, try to scroll the reviews section
            review_container_selectors = [
                "[data-testid='reviews-container']",
                "[class*='Review']",
                "[class*='review']",
                "[class*='Reviews']",
                "div[class*='ReviewCard']"
            ]
            
            review_container = None
            for selector in review_container_selectors:
                try:
                    review_container = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if review_container:
                        # Scroll horizontally to load more reviews (human-like)
                        print("Scrolling reviews section...")
                        max_scroll = review_container.get_attribute('scrollWidth')
                        current_scroll = 0
                        scroll_step = random.randint(300, 600)
                        
                        while current_scroll < max_scroll:
                            current_scroll += scroll_step
                            self.driver.execute_script(
                                f"arguments[0].scrollLeft = {current_scroll};",
                                review_container
                            )
                            self._human_delay(0.5, 1.2)
                            
                            # Check if more content loaded
                            new_max = review_container.get_attribute('scrollWidth')
                            if new_max > max_scroll:
                                max_scroll = new_max
                        
                        # Final delay after scrolling
                        self._human_delay(1, 2)
                        break
                except:
                    continue
            
            # Find individual review elements
            review_selectors = [
                "[data-testid='review']",
                "[class*='ReviewCard']",
                "[class*='review-card']",
                "[class*='ReviewItem']"
            ]
            
            reviews = []
            for selector in review_selectors:
                try:
                    if review_container:
                        reviews = review_container.find_elements(By.CSS_SELECTOR, selector)
                    else:
                        reviews = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if reviews:
                        break
                except:
                    continue
            
            # Extract individual review details
            for i, review in enumerate(reviews):
                review_data = {
                    'reviewer_name': None,
                    'post_date': None,
                    'rating': None
                }
                
                # Reviewer name
                name_selectors = [
                    "[data-testid='reviewer-name']",
                    "[class*='name']",
                    "[class*='Name']",
                    "span[class*='author']"
                ]
                
                for selector in name_selectors:
                    try:
                        name_elem = review.find_elements(By.CSS_SELECTOR, selector)
                        if name_elem:
                            review_data['reviewer_name'] = name_elem[0].text.strip()
                            break
                    except:
                        continue
                
                # Post date
                date_selectors = [
                    "[data-testid='review-date']",
                    "[class*='date']",
                    "[class*='Date']",
                    "time",
                    "span[class*='time']"
                ]
                
                for selector in date_selectors:
                    try:
                        date_elems = review.find_elements(By.CSS_SELECTOR, selector)
                        for date_elem in date_elems:
                            date_text = date_elem.text.strip()
                            if date_text and len(date_text) < 50:
                                review_data['post_date'] = date_text
                                break
                        if review_data['post_date']:
                            break
                    except:
                        continue
                
                # Rating
                rating_selectors = [
                    "[data-testid='review-rating']",
                    "[class*='rating']",
                    "[class*='star']",
                    "span[aria-label*='star']"
                ]
                
                for selector in rating_selectors:
                    try:
                        rating_elems = review.find_elements(By.CSS_SELECTOR, selector)
                        for rating_elem in rating_elems:
                            rating_text = rating_elem.text.strip()
                            # Look for star rating or numeric rating
                            if 'star' in rating_text.lower() or re.search(r'\d+\.?\d*', rating_text):
                                review_data['rating'] = rating_text
                                break
                        if review_data['rating']:
                            break
                    except:
                        continue
                
                # Only add if we got at least reviewer name or rating
                if review_data['reviewer_name'] or review_data['rating']:
                    reviews_data['individual_reviews'].append(review_data)
                
                # Add small delay every few reviews to mimic human reading
                if i > 0 and i % 3 == 0:
                    self._human_delay(0.2, 0.5)
            
        except Exception as e:
            print(f"Error extracting reviews: {e}")
            import traceback
            traceback.print_exc()
        
        return reviews_data
    
    def save_to_json(self, data: Dict, filename: str = 'doordash_data.json'):
        """Save scraped data to JSON file."""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"Data saved to {filename}")
    
    def close(self):
        """Close the browser driver."""
        if self.driver:
            self.driver.quit()


def main():
    """Example usage of the DoorDash scraper."""
    url = "https://www.doordash.com/store/mcdonald's-davis-720446/1025484/?event_type=autocomplete&pickup=false"
    
    # Use your Chrome profile path to bypass Cloudflare
    # On macOS, default Chrome profile is usually at:
    # ~/Library/Application Support/Google/Chrome
    # Or create a separate profile directory like: /Users/yourusername/ChromeProfile
    chrome_profile_path = "/Users/apple/ChromeProfile"  # Update this to your Chrome profile path
    
    scraper = DoorDashScraper(headless=False, chrome_profile_path=chrome_profile_path)
    
    try:
        data = scraper.scrape_restaurant(url)
        scraper.save_to_json(data, 'doordash_final_v12.json')
        
        # Print summary
        print("\n" + "="*50)
        print("SCRAPING SUMMARY")
        print("="*50)
        print(f"Restaurant: {data['restaurant_info']['name']}")
        print(f"Cuisine: {data['restaurant_info']['cuisine']}")
        
        # Count items by category
        total_items = 0
        for category, items in data.get('menu_categories', {}).items():
            print(f"{category}: {len(items)} items")
            total_items += len(items)
        print(f"Total Menu Items: {total_items}")
        
        print(f"Overall Rating: {data['reviews']['overall_rating']}")
        print(f"Individual Reviews: {len(data['reviews']['individual_reviews'])}")
        print("="*50)
        
    except Exception as e:
        print(f"Error during scraping: {e}")
        import traceback
        traceback.print_exc()
    finally:
        scraper.close()


if __name__ == "__main__":
    main()

