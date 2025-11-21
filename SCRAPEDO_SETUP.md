# Scrape.do Setup Guide for LinkedIn Scouting

## Overview

Scrape.do is now the **recommended scraping service** for LinkedIn profile extraction, offering:

- ✅ **Better Success Rate**: ~85-95% vs ScraperAPI's ~30-40% and ScrapingBee's ~70-85%
- ✅ **Automatic CAPTCHA Solving**: Built-in CAPTCHA handling
- ✅ **110M+ Proxy Network**: Residential, mobile, and datacenter proxies across 150 countries
- ✅ **Smart Retry Logic**: Automatic retries with IP rotation on failures
- ✅ **JavaScript Rendering**: Full headless browser support for dynamic content
- ✅ **Cost Effective**: Only pay for successful requests (2xx status codes)

## Setup Instructions

### 1. Sign Up for Scrape.do

1. Visit [https://scrape.do/](https://scrape.do/)
2. Click "Sign Up" or visit [https://dashboard.scrape.do/sign-up](https://dashboard.scrape.do/sign-up)
3. Create a **free account** (includes free tier credits)

### 2. Get Your API Token

1. Log in to your dashboard: [https://dashboard.scrape.do/](https://dashboard.scrape.do/)
2. Navigate to the **API Token** section
3. Copy your API token (automatically generated on signup)

### 3. Configure the Backend

Edit `vantage_api/config.py`:

```python
# Scrape.do settings (recommended for LinkedIn)
SCRAPEDO_API_KEY = "your_scrapedo_token_here"  # Replace with your actual token

# LinkedIn scraping service selection
LINKEDIN_SCRAPER = "scrapedo"  # Options: "scrapedo", "scrapingbee", "scraperapi"
```

### 4. Test the Setup

Run the test script to verify your configuration:

```bash
cd vantage_api
python -c "from utils.scrapedo_linkedin_client import LinkedInScrapeDoClient; client = LinkedInScrapeDoClient(); print('✅ Scrape.do client initialized successfully')"
```

## Usage

The LinkedIn scout will automatically use Scrape.do when configured. No code changes needed!

### Basic LinkedIn Profile Scraping

```python
from utils.scrapedo_linkedin_client import scrape_linkedin_profiles

# Scrape single or multiple profiles
profile_urls = [
    "https://www.linkedin.com/in/williamhgates/",
    "https://www.linkedin.com/in/satyanadella/"
]

profiles = scrape_linkedin_profiles(profile_urls, use_super_proxy=True)

for profile in profiles:
    print(f"Name: {profile['name']}")
    print(f"Headline: {profile['headline']}")
    print(f"Experience: {len(profile['experience'])} positions")
```

### LinkedIn Search

```python
from utils.scrapedo_linkedin_client import search_linkedin_candidates

# Search for candidates
profile_urls = search_linkedin_candidates(
    job_title="Data Scientist",
    location="San Francisco, CA",
    num_candidates=10,
    open_to_work=True,
    use_super_proxy=True  # Recommended for LinkedIn
)

print(f"Found {len(profile_urls)} candidates")
```

## Key Parameters

### For Profile Scraping

- **`use_super_proxy=True`**: Use residential/mobile proxies (recommended for LinkedIn)
  - **Cost**: 5x concurrency units per request
  - **Success Rate**: ~95% vs ~70% with datacenter proxies

### For Search

- **`use_super_proxy=True`**: Default for searches (highly recommended)
- **`geoCode='us'`**: Target US-based proxies (automatically set)

## API Cost Considerations

### Concurrency Units

1. **Standard Request** (no rendering): 1 unit
2. **JavaScript Rendering** (`render=true`): 5 units
3. **Super Proxy** (residential/mobile): Multiply by cost factor

### LinkedIn Scraping Costs

- **Profile Scraping**: ~5 units per profile (with render + super proxy)
- **Search Page**: ~5 units per search (with render + super proxy)
- **Total for 10 candidates**: ~55 units (1 search + 10 profiles)

### Free Tier

- Check your plan limits in the [dashboard](https://dashboard.scrape.do/)
- Monitor usage to avoid overages
- Only successful requests (2xx) consume credits

## Comparison with Other Services

| Feature | Scrape.do | ScrapingBee | ScraperAPI |
|---------|-----------|-------------|------------|
| LinkedIn Success Rate | **85-95%** | 70-85% | 30-40% |
| Proxy Network | 110M+ IPs | 10M+ IPs | Limited |
| CAPTCHA Solving | ✅ Built-in | ✅ Built-in | ❌ Manual |
| JavaScript Rendering | ✅ Full browser | ✅ Full browser | ✅ Basic |
| IP Rotation | ✅ Automatic | ✅ Automatic | ⚠️ Limited |
| Cost Model | Pay per success | Pay per request | Pay per request |
| Geographic Targeting | 150 countries | 120 countries | Limited |

## Troubleshooting

### Issue: "Scrape.do API key not found"

**Solution**: Make sure you've set `SCRAPEDO_API_KEY` in `config.py`

### Issue: Low success rate

**Solution**: 
1. Enable super proxy: `use_super_proxy=True`
2. Increase timeout: The default is 60s, LinkedIn may need longer
3. Check your API credits in the dashboard

### Issue: "Rate limit exceeded"

**Solution**: 
1. Add delays between requests (already implemented: 2s)
2. Check your plan limits in the dashboard
3. Upgrade to a higher tier if needed

### Issue: Empty search results

**Solution**:
1. Verify the search URL is correct
2. Try different keywords or locations
3. LinkedIn may be blocking the search - use direct profile URLs instead

## Advanced Configuration

### Custom Wait Times

Modify `scrapedo_linkedin_client.py` to adjust wait times:

```python
params = {
    'token': self.api_key,
    'url': profile_url,
    'render': 'true',
    'customWait': 5000,  # Increase from 3000 to 5000ms
    'waitUntil': 'networkidle2',  # or 'load', 'domcontentloaded'
}
```

### Session Persistence

For maintaining the same IP across requests:

```python
params['sessionId'] = 12345  # Use any integer as session identifier
```

### Geographic Targeting

Target specific countries:

```python
params['geoCode'] = 'uk'  # UK, 'de' for Germany, 'ca' for Canada, etc.
```

## API Playground

Test your requests in the interactive playground:
[https://dashboard.scrape.do/playground](https://dashboard.scrape.do/playground)

## Documentation

Full API documentation:
[https://scrape.do/documentation/](https://scrape.do/documentation/)

## Support

- **Dashboard**: [https://dashboard.scrape.do/](https://dashboard.scrape.do/)
- **Documentation**: [https://scrape.do/documentation/](https://scrape.do/documentation/)
- **Support**: Contact via dashboard

---

## Quick Start Checklist

- [ ] Sign up at scrape.do
- [ ] Copy API token from dashboard
- [ ] Update `SCRAPEDO_API_KEY` in config.py
- [ ] Set `LINKEDIN_SCRAPER = "scrapedo"` in config.py
- [ ] Test with a LinkedIn profile URL
- [ ] Monitor usage in dashboard
- [ ] Enjoy higher success rates! 🚀
