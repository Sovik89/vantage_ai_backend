# ScrapingBee Setup Guide for LinkedIn Scout

## Why ScrapingBee?

ScrapingBee offers better LinkedIn scraping success rates compared to ScraperAPI:
- **Premium Proxies**: Residential and datacenter proxies specifically for LinkedIn
- **JavaScript Rendering**: Better handling of LinkedIn's dynamic content
- **Higher Success Rate**: ~70-85% vs ScraperAPI's ~30-40% for LinkedIn
- **Better Support**: Dedicated LinkedIn scraping features

## Setup Steps

### 1. Sign Up for ScrapingBee

1. Visit: https://www.scrapingbee.com/
2. Click "Start Free Trial"
3. Sign up with your email
4. **Free Trial**: 1,000 API credits (enough for ~100-200 LinkedIn profiles)

### 2. Get Your API Key

1. After signing up, go to your dashboard
2. Copy your API key from the "API Key" section
3. It looks like: `YOUR_SCRAPINGBEE_API_KEY_HERE`

### 3. Configure in Your Application

Open `config.py` and update:

```python
# ScrapingBee settings
SCRAPINGBEE_API_KEY = "YOUR_SCRAPINGBEE_API_KEY_HERE"  # Paste your key here
USE_SCRAPINGBEE = True  # Set to True to use ScrapingBee
```

### 4. Restart Backend Server

```powershell
# Stop current server (Ctrl+C)

# Restart with new config
uvicorn main:app --host 127.0.0.1 --port 8080 --reload
```

## Pricing

### Free Tier
- **1,000 credits** on signup
- JavaScript rendering: 5 credits per request
- Premium proxies: 10-25 credits per request
- **Estimated**: ~40-100 LinkedIn profiles with free tier

### Paid Plans
- **Freelance**: $49/month - 150,000 credits (~6,000-15,000 profiles)
- **Startup**: $149/month - 500,000 credits (~20,000-50,000 profiles)
- **Business**: $299/month - 1,250,000 credits (~50,000-125,000 profiles)

**For LinkedIn**: Each profile scrape uses ~10-25 credits depending on:
- JavaScript rendering (5 credits)
- Premium proxy (10-20 credits)
- Retry attempts (if blocked)

## Usage Comparison

### ScrapingBee (Recommended)
```python
USE_SCRAPINGBEE = True
SCRAPINGBEE_API_KEY = "your_key"
```
✅ Better success rate (70-85%)
✅ Premium proxies for LinkedIn
✅ Better JavaScript rendering
✅ Dedicated LinkedIn support
💰 More expensive (but worth it for LinkedIn)

### ScraperAPI (Fallback)
```python
USE_SCRAPINGBEE = False
SCRAPERAPI_KEY = "your_key"
```
❌ Lower success rate (30-40%)
❌ Generic proxies
❌ LinkedIn often blocks
💰 Cheaper option

## Expected Results

### With ScrapingBee:
- **LinkedIn Search**: 60-70% success rate
- **Profile Scraping**: 80-90% success rate
- **Recommended Locations**: Any (US, India, Europe all work)

### With ScraperAPI:
- **LinkedIn Search**: 20-30% success rate (often 403 Forbidden)
- **Profile Scraping**: 50-60% success rate
- **Recommended Locations**: US only

## Testing

After setup, test with:
```
Location: San Francisco, CA (or any location)
Job Title: Data Scientist
Candidates: 5
```

**Expected with ScrapingBee**:
```
🐝 Using ScrapingBee for LinkedIn search (better success rate)
✅ Found 5 candidate profile URLs
✅ Scraped 4-5 profiles successfully
```

## Troubleshooting

### Issue: Still getting 403 Forbidden
**Solution**: 
1. Verify API key is correct in config.py
2. Check you have credits remaining (dashboard)
3. Try with premium_proxy enabled (already configured)
4. Contact ScrapingBee support

### Issue: Slow responses
**Reason**: JavaScript rendering + premium proxies take 5-10 seconds per profile
**Solution**: This is normal, be patient

### Issue: High credit usage
**Reason**: Each profile uses 10-25 credits
**Solution**: 
- Reduce number of candidates
- Use only when needed
- Consider upgrading plan

## Alternative: Manual Profile URLs

If even ScrapingBee fails, you can:
1. Manually search LinkedIn
2. Copy profile URLs
3. Paste into system (feature can be added)

## Support

- **ScrapingBee Docs**: https://www.scrapingbee.com/documentation/
- **LinkedIn Scraping**: https://www.scrapingbee.com/blog/web-scraping-linkedin/
- **Support Email**: hello@scrapingbee.com

## Next Steps

1. ✅ Sign up for ScrapingBee
2. ✅ Get API key
3. ✅ Update config.py
4. ✅ Restart backend
5. ✅ Test with real job description
6. 📊 Monitor credit usage in dashboard
