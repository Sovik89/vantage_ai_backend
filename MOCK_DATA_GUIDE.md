# Mock LinkedIn Data - Testing & Demo Guide

## Overview

The mock LinkedIn data system allows you to test the entire LinkedIn Scout pipeline **without consuming API credits** or hitting rate limits. Perfect for:

✅ **Testing** the JD matching algorithm  
✅ **Demo** to stakeholders without real LinkedIn scraping  
✅ **Development** without worrying about API costs  
✅ **CI/CD** automated testing with consistent results  

---

## Quick Start

### Enable Mock Mode

In `config.py`, set:

```python
USE_MOCK_LINKEDIN_DATA = True  # Mock mode
# or
USE_MOCK_LINKEDIN_DATA = False  # Real LinkedIn scraping
```

### Test It

```bash
# Test mock data generator
python utils/mock_linkedin_data.py

# Start backend with mock mode
uvicorn main:app --reload
```

### Use LinkedIn Scout API

```bash
POST /api/linkedin/scout
{
  "job_description": "Looking for Senior Data Scientist with 5+ years experience in ML...",
  "location": "San Francisco, CA",
  "num_candidates": 10,
  "open_to_work_only": false
}
```

**Result**: Receives 10 realistic mock profiles instantly, no API calls!

---

## Mock Data Features

### ✨ Realistic Profile Generation

The mock generator creates profiles with:

- **Names**: Mix of diverse first/last names (US, Indian, Chinese, Hispanic)
- **Titles**: Role-appropriate (Data Scientist, ML Engineer, etc.)
- **Companies**: Real tech companies (Google, Meta, Amazon, etc.)
- **Locations**: Major tech hubs (SF, Seattle, NYC, Bangalore, etc.)
- **Experience**: 2-4 realistic positions with durations
- **Education**: Top universities with relevant degrees
- **Skills**: 8-15 relevant skills per role
- **About**: Auto-generated professional summaries

### 📊 Supported Job Roles

The system auto-detects job role from description:

| Job Description Contains | Generates Profiles For |
|--------------------------|------------------------|
| "data scientist", "machine learning" | Data Scientists/ML Engineers |
| "data engineer" | Data Engineers |
| "software engineer" | Software Engineers |
| "hr", "people operations" | HR Professionals |

### 🎯 Smart Matching

- Location preferences respected (when provided)
- Number of candidates configurable
- Experience levels varied (2-10 years)
- Mix of current/past companies

---

## API Response Example

### Input Request

```json
{
  "job_description": "Senior Data Scientist role requiring Python, ML, and cloud experience",
  "location": "San Jose, CA",
  "num_candidates": 5
}
```

### Mock Output (Sample)

```json
{
  "job_id": "linkedin_scout_abc123",
  "status": "completed",
  "results": [
    {
      "result_id": "result_xyz789",
      "profile_url": "https://www.linkedin.com/in/emmasmith567/",
      "full_name": "Emma Smith",
      "headline": "Senior Data Scientist at Google",
      "location": "San Jose, CA",
      "match_score": 92,
      "overall_reasoning": "Strong match with 6 years ML experience, Python expertise...",
      "created_at": "2025-11-15T10:30:00Z"
    },
    ...
  ]
}
```

---

## Code Architecture

### Files Modified

1. **`utils/mock_linkedin_data.py`** (NEW)
   - `generate_mock_profile()` - Single profile generator
   - `generate_mock_candidates()` - Batch generator
   - `mock_search_linkedin_candidates()` - Search mock
   - `mock_scrape_linkedin_profiles()` - Profile scraping mock

2. **`config.py`**
   - Added `USE_MOCK_LINKEDIN_DATA` toggle

3. **`routers/linkedin_scout.py`**
   - Checks `USE_MOCK_LINKEDIN_DATA` before scraping
   - Falls back to real scrapers when disabled

### Integration Points

```python
# In linkedin_scout.py

if config.USE_MOCK_LINKEDIN_DATA:
    # Use mock data
    from utils.mock_linkedin_data import mock_search_linkedin_candidates
    urls = mock_search_linkedin_candidates(...)
else:
    # Use real scrapers
    from utils.scrapingbee_linkedin_client import search_linkedin_candidates
    urls = search_linkedin_candidates(...)
```

---

## Testing Checklist

### ✅ Unit Testing

```bash
# Test data generator
python utils/mock_linkedin_data.py
```

Expected output:
- ✅ Single profile generation
- ✅ Batch candidate generation (5 profiles)
- ✅ Mock search returns URLs
- ✅ Mock scraping returns full profiles

### ✅ Integration Testing

1. Set `USE_MOCK_LINKEDIN_DATA = True`
2. Start backend: `uvicorn main:app --reload`
3. Call `/api/linkedin/scout` with sample JD
4. Verify:
   - ✅ Returns results instantly (< 30 seconds)
   - ✅ 10 candidates returned
   - ✅ Each has name, headline, skills, experience
   - ✅ Match scores calculated correctly
   - ✅ Results saved to BigQuery

### ✅ Real Scraping Verification

1. Set `USE_MOCK_LINKEDIN_DATA = False`
2. Restart backend
3. Call same endpoint
4. Verify:
   - ✅ Uses ScrapingBee/Scrape.do
   - ✅ Real LinkedIn URLs
   - ✅ Longer processing time (60-120s)

---

## Mock vs Real Comparison

| Feature | Mock Mode | Real Scraping |
|---------|-----------|---------------|
| **Speed** | < 5 seconds | 60-120 seconds |
| **Cost** | $0.00 | $0.02-0.10 per candidate |
| **Reliability** | 100% success | 70-95% success |
| **Data Quality** | Synthetic but realistic | Real LinkedIn data |
| **Rate Limits** | None | Provider-dependent |
| **Use Case** | Testing, demos, development | Production |

---

## Customization

### Add Custom Names

Edit `mock_linkedin_data.py`:

```python
FIRST_NAMES = [
    "Emma", "Liam", ..., 
    "YourName",  # Add here
]
```

### Add Custom Companies

```python
COMPANIES = [
    "Google", "Meta", ...,
    "YourCompany",  # Add here
]
```

### Add Custom Skills

```python
SKILLS_BY_ROLE = {
    "data_scientist": [
        "Python", "ML", ...,
        "YourSkill",  # Add here
    ]
}
```

### Adjust Profile Complexity

```python
# In generate_mock_profile()

num_positions = random.randint(2, 4)  # Change range
num_skills = random.randint(8, 15)    # Change range
```

---

## Production Deployment

### Recommended Setup

```python
# config.py - Production
USE_MOCK_LINKEDIN_DATA = False  # Real scraping

# config.py - Staging/Dev
USE_MOCK_LINKEDIN_DATA = True   # Mock data
```

### Environment Variables

```bash
# .env
USE_MOCK_LINKEDIN_DATA=false  # Production
USE_MOCK_LINKEDIN_DATA=true   # Dev/Test
```

Load in config:

```python
import os
USE_MOCK_LINKEDIN_DATA = os.getenv('USE_MOCK_LINKEDIN_DATA', 'false').lower() == 'true'
```

---

## Troubleshooting

### Issue: Mock mode not activating

**Check**:
```python
# In config.py
print(f"Mock mode: {USE_MOCK_LINKEDIN_DATA}")
```

**Solution**: Ensure `USE_MOCK_LINKEDIN_DATA = True` (not string)

### Issue: Getting real data despite mock mode

**Check**: Did you restart the backend after changing config?

**Solution**: 
```bash
# Stop uvicorn (Ctrl+C)
# Restart
uvicorn main:app --reload
```

### Issue: Not enough diverse candidates

**Solution**: Increase data pools in `mock_linkedin_data.py`
- Add more names
- Add more companies
- Add more skills

---

## Future Enhancements

Potential improvements:

- [ ] Load mock data from JSON files
- [ ] Configurable mock data distribution
- [ ] Mock data with configurable match scores
- [ ] Time-series experience generation
- [ ] Mock data versioning/snapshots
- [ ] Faker library integration for more realistic data
- [ ] Mock resume/CV file generation

---

## Summary

✅ Mock mode bypasses all real LinkedIn scraping  
✅ Generates realistic profiles for testing  
✅ Zero API costs, instant results  
✅ Perfect for demos and development  
✅ Toggle on/off with single config variable  

**Next Steps**:
1. Enable mock mode: `USE_MOCK_LINKEDIN_DATA = True`
2. Test endpoint: `POST /api/linkedin/scout`
3. Verify results in logs and BigQuery
4. Switch to real mode when ready for production
