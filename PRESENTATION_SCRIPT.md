# DoorDash Scraper - Presentation Script
## Video Call Presentation Guide with Segues

---

## 🎬 **OPENING (30 seconds)**

**Script:**
"Good [morning/afternoon], [Professor Name]. Thank you for taking the time to review my project today. I'm excited to present my DoorDash web scraper project - a tool I've built that extracts comprehensive menu data from DoorDash restaurant pages.

Today, I'll walk you through what we've achieved, the technical challenges we overcame, and the path forward for scaling this research project. Let me start by showing you the results."

**[Pause - let them acknowledge]**

---

## 📊 **SECTION 1: PROJECT OVERVIEW & RESULTS (2-3 minutes)**

**Segue:**
"Let me begin with an overview of what this scraper accomplishes."

**Script:**
"I've successfully developed a web scraper that extracts complete restaurant menu data from DoorDash. The scraper captures all the essential information we need:

**First**, restaurant-level data - including the restaurant name, URL, cuisine type, and price range.

**Second**, menu item details - for each item, we extract the name, description, price, customer ratings, promotional tags like '#1 most liked', and product images.

**And third**, the items are intelligently organized into 16 distinct menu sections - like Featured Items, Most Ordered, Extra Value Meals, Burgers, Chicken, and so on.

Let me show you what this looks like in practice."

**[ACTION: Open Excel file - `doordash_menu_data.xlsx`]**

**Segue:**
"Here's the Excel file with our scraped data from a McDonald's restaurant."

**Script:**
"As you can see, we have a multi-sheet workbook. The first sheet shows our Restaurant Information - we have the restaurant name, which is McDonald's, the full URL to the DoorDash page, the cuisine type - American, and the price range.

Now, if we look at the 'All Menu Items' sheet, you can see all 161 items we successfully scraped, with complete columns for section, name, description, price, rating, and promotional tags.

But what's really interesting is how we've organized this data. Let me show you the section breakdown..."

**[ACTION: Click through different sheet tabs]**

**Script:**
"Each menu section has its own dedicated sheet. For example, here's our Chicken section with 31 items - this includes everything from individual nuggets to complete meals. Our Burgers section has 26 items. Featured Items shows items with promotional tags.

And if we look at the Summary sheet, you can see the complete statistics - we extracted 161 items across 14 populated sections."

**Segue:**
"Now, you might be wondering - how did we achieve this level of data extraction?"

---

## 🔧 **SECTION 2: TECHNICAL CHALLENGES & SOLUTIONS (3-4 minutes)**

**Segue:**
"That brings me to the technical challenges we faced, and how we solved them."

**Script:**
"DoorDash presented several significant technical challenges, which I think are important to understand for this type of research project.

**Challenge number one: Dynamic Content Loading.** DoorDash uses JavaScript to dynamically load menu items as you scroll. Traditional scraping wouldn't capture this. Our solution was to implement comprehensive scrolling strategies - both vertical and horizontal scrolling - to ensure all content loads before extraction.

**Challenge two: Bot Detection.** DoorDash employs Cloudflare protection that blocks automated browsers. We solved this using specialized tools - specifically `undetected-chromedriver` combined with a real Chrome browser profile - which makes our scraper appear as a legitimate user.

**Challenge three: Dynamic CSS Classes.** The HTML structure uses randomly generated CSS class names that change frequently. For example, instead of stable class names, DoorDash uses classes like 'sc-62d4eb3a-21' that can't be relied upon. Our solution was to implement multiple selector fallbacks - we try CSS selectors, aria-label attributes, pattern matching in text content - essentially building redundancy into our extraction methods.

**And challenge four: Section Categorization.** Initially, all items were being dumped into a single category. We implemented intelligent keyword-based categorization that assigns items to the correct menu sections, and even allows items to appear in multiple relevant categories - like a chicken meal appearing in both 'Extra Value Meals' and 'Chicken'."

**Segue:**
"These solutions allowed us to achieve strong data completeness rates..."

**Script:**
"Let me give you some concrete numbers. In our test with a McDonald's restaurant, we extracted 149 to 161 menu items with:
- 100% name extraction rate
- Approximately 95% price extraction rate - which was a significant improvement from our initial 10% success rate
- Complete field coverage - all seven required data fields are implemented and captured

The items are properly organized across 16 distinct sections, with 14 of those sections containing items in our test case."

**Segue:**
"However, we did encounter some limitations that I think are important to address..."

---

## ⚠️ **SECTION 3: LIMITATIONS & CONCERNS (2-3 minutes)**

**Segue:**
"Let me be transparent about the challenges and limitations we face, particularly when it comes to scaling this project."

**Script:**
"There are several important considerations for this type of research project:

**First, DoorDash Restrictions.** DoorDash's Terms of Service likely prohibit automated scraping. While we've successfully bypassed their technical protections for individual restaurant scraping, large-scale scraping would face significant hurdles - potential IP blocking, account bans, and legal concerns. For research purposes, we'd need to implement respectful rate limiting and consider contacting DoorDash for potential API access or partnership.

**Second, Data Completeness.** Some fields like item descriptions are often null - this is because descriptions may only appear when you click on individual items, which would require additional interaction steps. Similarly, ratings may not always be visible in the main menu list view. This is a limitation we can work with, but it's important to acknowledge.

**Third, Infrastructure for Scaling.** Currently, our scraper works excellently for individual restaurants - each restaurant takes about 1 to 2 minutes to scrape. But if we wanted to scale this significantly, we'd need substantial infrastructure - multiple browser instances, proxy servers, queue management systems, and significant storage. I've calculated that scraping all USA restaurants would take approximately 6,000 to 10,000 hours of processing time.

**Which brings me to the most important consideration: scaling scope.**"

**Segue:**
"This leads to our recommended approach for next steps..."

---

## 🚀 **SECTION 4: NEXT STEPS & RECOMMENDATIONS (3-4 minutes)**

**Segue:**
"Given these considerations, let me propose a practical path forward for this research project."

**Script:**
"I believe the most effective approach is **targeted expansion** rather than attempting full USA coverage.

**Our current state:** We have a fully functional scraper that works perfectly for individual restaurants. This serves as an excellent proof of concept, and we've demonstrated all the required capabilities.

**For the next phase, I recommend focusing on scraping 100 to 500 restaurants** from specific chains or cities. This approach offers several advantages:

**One**, it's more manageable - we can build the infrastructure incrementally. We'd need to create a restaurant discovery system that searches DoorDash by location, extracts restaurant URLs, and builds a queue of targets.

**Two**, it's more practical for research - you get a substantial dataset that's still analyzable and meaningful, without the overwhelming scale of hundreds of thousands of restaurants.

**And three**, it demonstrates scalability concepts - we'd build a framework with queue-based processing, worker pools for parallel scraping, error handling, and progress tracking. This framework could theoretically scale further if needed.

**The implementation would involve:** First, building a restaurant discovery system - scraping DoorDash search results by city or ZIP code to collect restaurant URLs. Second, creating a queue-based processing framework that can handle multiple restaurants in parallel. And third, implementing error handling and progress tracking so we can monitor our collection process.

This would likely take 4 to 8 weeks to implement fully, but it would give us a solid research dataset of 100 to 500 restaurants - which I believe is the right scope for demonstrating the capabilities while remaining practical."

**Segue:**
"Now, I'd like to open this up for questions or discussion about the direction of this project..."

---

## ❓ **SECTION 5: QUESTIONS & DISCUSSION (Variable time)**

### **If Asked About Full USA Coverage:**

**Response:**
"That's a great question. Technically, it's possible - our scraper architecture could be scaled. However, there are practical barriers: we're looking at 300,000 to 500,000 restaurants across the USA, which would require approximately 6,000 to 10,000 hours of scraping time - that's 250 to 400 days even with parallel processing.

Additionally, we'd face infrastructure costs of roughly $800 to $2,700 per month for cloud servers, proxies, and storage. But more importantly, DoorDash's restrictions and Terms of Service make large-scale scraping problematic from both a technical and legal standpoint.

I think a better approach is to demonstrate scalability with a targeted sample - 100 to 500 restaurants gives us meaningful data while remaining practical and ethical. Would you like me to focus on a specific research question that this dataset could answer?"

---

### **If Asked About DoorDash Restrictions:**

**Response:**
"Yes, that's an important concern. We've successfully bypassed Cloudflare's technical protections using specialized tools and real browser profiles. However, aggressive large-scale scraping would likely trigger additional detection mechanisms - IP blocking, rate limiting, or account bans.

For a research project, I'd recommend implementing respectful rate limiting - perhaps one restaurant every 2 to 3 minutes, and using distributed IP addresses if we scale. We should also consider reaching out to DoorDash about potential API access or research partnerships. 

Are there specific research objectives where we could work within these constraints, or would you prefer we explore alternative data sources?"

---

### **If Asked About Data Accuracy:**

**Response:**
"Great question. Our data accuracy is strong for available fields: we achieve 100% name extraction and approximately 95% price extraction. For other fields like descriptions and ratings, the completeness depends on what's visible on the page - some restaurants show more detail than others.

However, for the fields that ARE visible, our extraction is very reliable. We use multiple fallback methods, so if one selector fails, we try alternatives. Would you like me to show you examples of the data quality, or discuss how we might improve extraction for fields that are currently less complete?"

---

### **If Asked About Timeline/Next Steps:**

**Response:**
"Absolutely. For the immediate next steps, I can have the multi-restaurant framework ready within 4 to 8 weeks. Here's how I'd break it down:

Week 1-2: Build the restaurant discovery system - creating a scraper that searches DoorDash by location and collects restaurant URLs.

Week 3-4: Implement the queue-based processing framework - setting up worker pools, error handling, and progress tracking.

Week 5-8: Run targeted data collection - scraping our selected restaurants and validating data quality.

Does this timeline work with your research schedule? And what would you like to prioritize - speed of implementation, or breadth of data collection?"

---

### **If Asked About Research Applications:**

**Response:**
"That's what makes this project exciting - the data has multiple research applications. We could analyze price variations across different locations or chains. We could study menu trends and regional preferences. We could look at promotional strategies - which items get featured tags, which sections are most popular.

With 100 to 500 restaurants, we'd have enough data for meaningful statistical analysis while keeping the scope manageable. What specific research questions are you most interested in exploring with this dataset?"

---

## 🎯 **SECTION 6: CLOSING (30 seconds)**

**Segue:**
"Let me wrap up with a summary of where we are and where we're headed."

**Script:**
"To summarize: We've successfully built a web scraper that extracts comprehensive menu data from DoorDash restaurant pages - with all required fields implemented and proper section organization. We've overcome significant technical challenges related to dynamic content and bot detection.

We have Excel and CSV exports ready for analysis, and a clear path forward for targeted expansion to 100 to 500 restaurants.

I'm happy to adjust the scope or focus based on your research priorities. Thank you for your time today, and I look forward to your feedback on the direction of this project."

**[Pause for final questions]**

**Script:**
"Thank you again. I'll send you the presentation materials and data files. Please let me know if you have any additional questions or if you'd like to discuss any specific aspect in more detail."

---

## 📝 **PRESENTATION CHECKLIST**

**Before the call:**
- [ ] Excel file open and ready (`doordash_menu_data.xlsx`)
- [ ] Presentation documents available for reference
- [ ] Test your screen sharing
- [ ] Have the Excel file organized (start on "Restaurant Info" sheet)

**During the call:**
- [ ] Speak clearly and at a moderate pace
- [ ] Pause after each section for questions
- [ ] Be prepared to navigate Excel sheets quickly
- [ ] Have backup responses ready for common questions

**Technical backup:**
- If Excel doesn't open: Have CSV file ready as backup
- If screen sharing fails: Offer to email files and walk through verbally
- If questions get technical: Reference the PROJECT_PRESENTATION.md document

---

## 💡 **PRESENTATION TIPS**

1. **Pacing**: Speak at about 150 words per minute - slightly slower than normal conversation
2. **Pauses**: Use pauses effectively after key points - don't rush
3. **Visuals**: When showing Excel, use the mouse cursor to point to specific data
4. **Energy**: Sound enthusiastic about the project - passion shows through
5. **Transparency**: Be honest about limitations - shows maturity and critical thinking
6. **Questions**: If you don't know an answer, say "That's a great question - let me think about that" rather than guessing

---

## 🎤 **TONAL GUIDANCE**

- **Confident but not arrogant**: "We successfully solved this" not "This was easy"
- **Transparent about challenges**: "We faced X challenge, and here's how we addressed it"
- **Open to direction**: "I'm happy to adjust based on your priorities"
- **Research-focused**: Frame everything in terms of research applications and data quality

---

**Good luck with your presentation!** 🎓

Remember: You've accomplished something technically challenging and valuable. Present with confidence, but be ready to discuss limitations and next steps honestly.
