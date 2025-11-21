"""
Test Real LinkedIn Scrapers (Production)
Tests actual scraping services with your API keys
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_scrapedo():
    """Test Scrape.do service"""
    print("\n" + "="*80)
    print("TEST 1: Scrape.do Service (Your Primary)")
    print("="*80)
    
    try:
        from utils.scrapedo_linkedin_client import scrape_linkedin_profiles
        import config
        
        print(f"API Key: {config.SCRAPEDO_API_KEY[:20]}...")
        print("Testing with a sample LinkedIn profile URL...")
        
        # Test with a public LinkedIn profile
        test_url = "https://www.linkedin.com/in/satyanadella"
        
        profiles = scrape_linkedin_profiles([test_url])
        
        if profiles and len(profiles) > 0:
            profile = profiles[0]
            print(f"✅ Scrape.do works!")
            print(f"   Name: {profile.get('full_name', 'N/A')}")
            print(f"   Headline: {profile.get('headline', 'N/A')[:80]}...")
            print(f"   Skills found: {len(profile.get('skills', []))}")
            return True
        else:
            print(f"❌ Scrape.do returned no data")
            return False
            
    except Exception as e:
        print(f"❌ Scrape.do failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_scrapingbee():
    """Test ScrapingBee service"""
    print("\n" + "="*80)
    print("TEST 2: ScrapingBee Service")
    print("="*80)
    
    try:
        from utils.scrapingbee_linkedin_client import scrape_linkedin_profiles
        import config
        
        print(f"API Key: {config.SCRAPINGBEE_API_KEY[:20]}...")
        print("Testing with a sample LinkedIn profile URL...")
        
        test_url = "https://www.linkedin.com/in/satyanadella"
        
        profiles = scrape_linkedin_profiles([test_url])
        
        if profiles and len(profiles) > 0:
            profile = profiles[0]
            print(f"✅ ScrapingBee works!")
            print(f"   Name: {profile.get('full_name', 'N/A')}")
            print(f"   Headline: {profile.get('headline', 'N/A')[:80]}...")
            return True
        else:
            print(f"❌ ScrapingBee returned no data")
            return False
            
    except Exception as e:
        print(f"❌ ScrapingBee failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_scraperapi():
    """Test ScraperAPI service"""
    print("\n" + "="*80)
    print("TEST 3: ScraperAPI Service")
    print("="*80)
    
    try:
        from utils.scraperapi_linkedin_client import scrape_linkedin_profiles
        import config
        
        print(f"API Key: {config.SCRAPERAPI_KEY[:20]}...")
        print("Testing with a sample LinkedIn profile URL...")
        
        test_url = "https://www.linkedin.com/in/satyanadella"
        
        profiles = scrape_linkedin_profiles([test_url])
        
        if profiles and len(profiles) > 0:
            profile = profiles[0]
            print(f"✅ ScraperAPI works!")
            print(f"   Name: {profile.get('full_name', 'N/A')}")
            print(f"   Headline: {profile.get('headline', 'N/A')[:80]}...")
            return True
        else:
            print(f"❌ ScraperAPI returned no data")
            return False
            
    except Exception as e:
        print(f"❌ ScraperAPI failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_rapidapi():
    """Test RapidAPI service"""
    print("\n" + "="*80)
    print("TEST 4: RapidAPI Service")
    print("="*80)
    
    try:
        from utils.rapidapi_linkedin_client import scrape_linkedin_profiles
        import config
        
        print(f"API Key: {config.RAPIDAPI_KEY[:20]}...")
        print("Testing with a sample LinkedIn profile URL...")
        
        test_url = "https://www.linkedin.com/in/satyanadella"
        
        profiles = scrape_linkedin_profiles([test_url])
        
        if profiles and len(profiles) > 0:
            profile = profiles[0]
            print(f"✅ RapidAPI works!")
            print(f"   Name: {profile.get('full_name', 'N/A')}")
            print(f"   Headline: {profile.get('headline', 'N/A')[:80]}...")
            return True
        else:
            print(f"❌ RapidAPI returned no data")
            return False
            
    except Exception as e:
        print(f"❌ RapidAPI failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Test all scraper services"""
    print("\n")
    print("🔍 " + "="*76)
    print("🔍 PRODUCTION LinkedIn Scraper Test")
    print("🔍 Testing with real API keys and real LinkedIn profile")
    print("🔍 " + "="*76)
    
    print("\nℹ️  Testing with Satya Nadella's public LinkedIn profile")
    print("   This is a well-known public profile, safe to test with")
    
    tests = [
        ("Scrape.do (Primary)", test_scrapedo),
        ("ScrapingBee", test_scrapingbee),
        ("ScraperAPI", test_scraperapi),
        ("RapidAPI", test_rapidapi)
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ Test '{name}' crashed: {e}")
            results.append((name, False))
    
    # Summary
    print("\n" + "="*80)
    print("PRODUCTION SCRAPER TEST RESULTS")
    print("="*80)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ WORKING" if result else "❌ FAILED"
        print(f"{status} - {name}")
    
    print(f"\n{'='*80}")
    print(f"Working scrapers: {passed}/{total}")
    print(f"{'='*80}\n")
    
    if passed > 0:
        print(f"✅ You have {passed} working scraper(s)! Production ready.")
        print("\n💡 Next steps:")
        print("   1. The LinkedIn Scout endpoint will use these scrapers automatically")
        print("   2. It tries them in order: Scrape.do → ScrapingBee → ScraperAPI → RapidAPI")
        print("   3. Test the full endpoint: POST /api/linkedin/scout")
    else:
        print("❌ No scrapers are working. Check:")
        print("   1. API keys are valid and have credits")
        print("   2. Network/firewall allows outbound requests")
        print("   3. Services are not rate-limited")


if __name__ == "__main__":
    main()
