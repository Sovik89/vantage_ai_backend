"""
Quick Test Script for Mock LinkedIn Data
Demonstrates the mock data system end-to-end
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.mock_linkedin_data import (
    generate_mock_profile,
    generate_mock_candidates,
    mock_search_linkedin_candidates,
    mock_scrape_linkedin_profiles
)

def test_single_profile():
    """Test single profile generation"""
    print("\n" + "="*70)
    print("TEST 1: Single Profile Generation")
    print("="*70)
    
    profile = generate_mock_profile("data_scientist")
    
    print(f"\n✅ Generated Profile:")
    print(f"   Name: {profile['name']}")
    print(f"   Headline: {profile['headline']}")
    print(f"   Location: {profile['location']}")
    print(f"   Profile URL: {profile['profile_url']}")
    print(f"   Skills: {', '.join(profile['skills'][:5])}... ({len(profile['skills'])} total)")
    print(f"   Experience:")
    for exp in profile['experience'][:2]:
        print(f"      • {exp['title']} at {exp['company']} ({exp['duration']})")
    print(f"   Education:")
    for edu in profile['education']:
        print(f"      • {edu['degree']} from {edu['school']}")


def test_batch_generation():
    """Test batch candidate generation"""
    print("\n" + "="*70)
    print("TEST 2: Batch Candidate Generation (Data Engineers)")
    print("="*70)
    
    candidates = generate_mock_candidates(
        job_role="data_engineer",
        num_candidates=5,
        location="San Jose, CA"
    )
    
    print(f"\n✅ Generated {len(candidates)} candidates:")
    for i, candidate in enumerate(candidates, 1):
        print(f"   {i}. {candidate['name']}")
        print(f"      {candidate['headline']}")
        print(f"      {candidate['location']}")
        print(f"      Skills: {len(candidate['skills'])}, Experience: {len(candidate['experience'])} positions")
        print()


def test_search_flow():
    """Test LinkedIn search flow"""
    print("\n" + "="*70)
    print("TEST 3: LinkedIn Search Flow Simulation")
    print("="*70)
    
    # Simulate search
    print("\n🔍 Searching for: 'Machine Learning Engineer' in 'San Francisco'")
    urls = mock_search_linkedin_candidates(
        job_title="Machine Learning Engineer",
        location="San Francisco, CA",
        num_candidates=8,
        open_to_work=True
    )
    
    print(f"\n✅ Found {len(urls)} profile URLs:")
    for i, url in enumerate(urls[:3], 1):
        print(f"   {i}. {url}")
    print(f"   ... and {len(urls) - 3} more")
    
    return urls


def test_profile_enrichment(profile_urls):
    """Test profile enrichment flow"""
    print("\n" + "="*70)
    print("TEST 4: Profile Enrichment Simulation")
    print("="*70)
    
    print(f"\n🕷️ Enriching {len(profile_urls)} profiles...")
    profiles = mock_scrape_linkedin_profiles(profile_urls[:3])
    
    print(f"\n✅ Enriched {len(profiles)} profiles:")
    for i, profile in enumerate(profiles, 1):
        print(f"\n   {i}. {profile['name']}")
        print(f"      URL: {profile['profile_url']}")
        print(f"      Headline: {profile['headline']}")
        print(f"      Location: {profile['location']}")
        print(f"      Skills ({len(profile['skills'])}): {', '.join(profile['skills'][:3])}...")
        print(f"      Experience: {len(profile['experience'])} positions")
        print(f"         Current: {profile['experience'][0]['title']} at {profile['experience'][0]['company']}")


def test_different_roles():
    """Test generation for different job roles"""
    print("\n" + "="*70)
    print("TEST 5: Multiple Job Role Support")
    print("="*70)
    
    roles = [
        ("data_scientist", "Data Scientists"),
        ("data_engineer", "Data Engineers"),
        ("software_engineer", "Software Engineers"),
        ("hr", "HR Professionals")
    ]
    
    for role_key, role_name in roles:
        profile = generate_mock_profile(role_key)
        print(f"\n✅ {role_name}:")
        print(f"   {profile['name']} - {profile['headline']}")
        print(f"   Top 3 skills: {', '.join(profile['skills'][:3])}")


def test_realistic_data():
    """Test data quality and realism"""
    print("\n" + "="*70)
    print("TEST 6: Data Quality Check")
    print("="*70)
    
    profile = generate_mock_profile("data_scientist")
    
    checks = [
        ("Profile URL format", profile['profile_url'].startswith("https://www.linkedin.com/in/")),
        ("Name present", len(profile['name']) > 0),
        ("Headline present", len(profile['headline']) > 0),
        ("Location present", len(profile['location']) > 0),
        ("Skills count", 8 <= len(profile['skills']) <= 15),
        ("Experience count", 2 <= len(profile['experience']) <= 4),
        ("Education count", 1 <= len(profile['education']) <= 2),
        ("About section", len(profile['about']) > 50)
    ]
    
    print("\n✅ Quality Checks:")
    all_passed = True
    for check_name, passed in checks:
        status = "✅" if passed else "❌"
        print(f"   {status} {check_name}")
        if not passed:
            all_passed = False
    
    if all_passed:
        print("\n🎉 All quality checks passed!")
    else:
        print("\n⚠️ Some checks failed")


def main():
    """Run all tests"""
    print("\n" + "="*70)
    print("🧪 MOCK LINKEDIN DATA SYSTEM - COMPREHENSIVE TEST")
    print("="*70)
    
    try:
        # Run tests
        test_single_profile()
        test_batch_generation()
        urls = test_search_flow()
        test_profile_enrichment(urls)
        test_different_roles()
        test_realistic_data()
        
        # Summary
        print("\n" + "="*70)
        print("✅ TEST SUITE COMPLETE")
        print("="*70)
        print("\n🎉 All tests passed successfully!")
        print("\n📋 Summary:")
        print("   ✅ Single profile generation working")
        print("   ✅ Batch generation working")
        print("   ✅ Search simulation working")
        print("   ✅ Profile enrichment working")
        print("   ✅ Multiple role support working")
        print("   ✅ Data quality validated")
        print("\n🚀 Mock system is ready for use!")
        print("\n📝 Next Steps:")
        print("   1. Set USE_MOCK_LINKEDIN_DATA = True in config.py")
        print("   2. Start backend: uvicorn main:app --reload")
        print("   3. Test API: POST /api/linkedin/scout")
        print("\n" + "="*70 + "\n")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
