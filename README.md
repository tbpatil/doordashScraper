# DoorDash Scraper

A Selenium-based web scraper for extracting restaurant information, menu items, and reviews from DoorDash restaurant pages.

## Features

- **Restaurant Information**: Extracts restaurant name, URL, and cuisine type
- **Menu Items**: Scrapes all menu items with:
  - Item name
  - Price
  - Deals (e.g., "Free on $15+")
  - Ratings (e.g., "84% liked by 175 people")
  - Tags (e.g., "#1 most liked")
- **Reviews**: Extracts:
  - Overall rating (e.g., "4.5/5 stars")
  - Individual reviews with reviewer name, post date, and rating

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. The scraper uses ChromeDriver which will be automatically downloaded via `webdriver-manager`.

## Usage

### Basic Usage

```python
from doordash_scraper import DoorDashScraper

# Initialize scraper with Chrome profile to bypass Cloudflare
chrome_profile_path = "/Users/yourusername/ChromeProfile"  # Your Chrome profile path
scraper = DoorDashScraper(headless=False, chrome_profile_path=chrome_profile_path)

# Scrape a restaurant page
url = "https://www.doordash.com/store/mcdonald's-davis-720446/1025484/?event_type=autocomplete&pickup=false"
data = scraper.scrape_restaurant(url)

# Save to JSON
scraper.save_to_json(data, 'doordash_data.json')

# Close the browser
scraper.close()
```

### Using Chrome Profile to Bypass Cloudflare

To bypass Cloudflare protection, use a real Chrome profile:

1. **Option 1: Use your existing Chrome profile** (macOS):
   ```python
   chrome_profile_path = "~/Library/Application Support/Google/Chrome"
   scraper = DoorDashScraper(headless=False, chrome_profile_path=chrome_profile_path)
   ```

2. **Option 2: Create a separate profile directory**:
   ```python
   chrome_profile_path = "/Users/yourusername/ChromeProfile"
   scraper = DoorDashScraper(headless=False, chrome_profile_path=chrome_profile_path)
   ```

**Note**: Make sure Chrome is completely closed before running the scraper when using an existing profile, or use a separate profile directory to avoid conflicts.

### Run the Example

```bash
python doordash_scraper.py
```

## Output Format

The scraper returns a dictionary with the following structure:

```json
{
  "restaurant_info": {
    "name": "Restaurant Name",
    "url": "https://...",
    "cuisine": "Cuisine Type"
  },
  "menu_items": [
    {
      "name": "Item Name",
      "price": "$X.XX",
      "deals": "Free on $15+",
      "ratings": "84% liked by 175 people",
      "tags": "#1 most liked",
      "section": "Featured Items"
    }
  ],
  "reviews": {
    "overall_rating": "4.5/5 stars",
    "individual_reviews": [
      {
        "reviewer_name": "John D.",
        "post_date": "2 days ago",
        "rating": "5 stars"
      }
    ]
  }
}
```

## Notes

- The scraper uses multiple CSS selectors to handle different DoorDash page layouts
- It automatically scrolls the page to load dynamic content
- Reviews section is horizontally scrolled to load all reviews
- If you encounter issues finding elements, you may need to inspect the page HTML and provide specific CSS selectors or class names

## Troubleshooting

### Cloudflare Blocking

If you're getting blocked by Cloudflare:

1. Use a real Chrome profile (see "Using Chrome Profile to Bypass Cloudflare" above)
2. Make sure Chrome is completely closed before running the scraper
3. Consider using a separate Chrome profile directory to avoid conflicts

### Element Not Found

If the scraper doesn't find certain elements:

1. Run with `headless=False` to see what's happening
2. Inspect the DoorDash page HTML to find the correct selectors
3. Share the HTML/CSS tags with me and I can update the selectors accordingly

## Requirements

- Python 3.7+
- Chrome browser
- Selenium
- webdriver-manager