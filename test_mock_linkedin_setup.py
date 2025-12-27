"""
Test Mock LinkedIn Setup
Verify that mock mode is enabled and working correctly
"""

import config
from utils.mock_linkedin_data import generate_mock_candidates, mock_search_linkedin_candidates

def test_mock_mode():
    """Test that mock mode is properly configured"""
    print("=" * 60)
    print("🧪 MOCK LINKEDIN SETUP TEST")
    print("=" * 60)
    
    # 1. Check config
    print(f"\n1️⃣ Configuration Check:")
    print(f"   USE_MOCK_LINKEDIN_DATA: {config.USE_MOCK_LINKEDIN_DATA}")
    
    if config.USE_MOCK_LINKEDIN_DATA:
        print("   ✅ MOCK MODE ENABLED - No scraping costs!")
    else:
        print("   ⚠️  LIVE MODE - Will use real scraping")
    
    # 2. Test mock data generation
    print(f"\n2️⃣ Testing Mock Data Generation:")
    
    # Test different roles
    roles = [
        ("data_scientist", "San Francisco, CA"),
        ("data_engineer", "New York, NY"),
        ("software_engineer", "Seattle, WA")
    ]
    
    for role, location in roles:
        print(f"\n   Testing {role} in {location}:")
        candidates = generate_mock_candidates(
            job_role=role,
            num_candidates=3,
            location=location
        )
        
        print(f"   Generated {len(candidates)} candidates:")
        for idx, candidate in enumerate(candidates, 1):
            print(f"      {idx}. {candidate['name']} - {candidate['headline']}")
            print(f"         Skills: {len(candidate.get('skills', []))} | Experience: {len(candidate.get('experience', []))} positions")
    
    # 3. Test mock search function
    print(f"\n3️⃣ Testing Mock Search Function:")
    search_results = mock_search_linkedin_candidates(
        job_title="Data Scientist",  # Changed from job_role to job_title
        location="San Jose, CA",
        num_candidates=5
    )
    
    print(f"   Found {len(search_results)} profile URLs:")
    for url in search_results[:3]:
        print(f"      - {url}")
    
    print("\n" + "=" * 60)
    print("✅ MOCK SETUP TEST COMPLETE")
    print("=" * 60)
    print("\n💡 Next Steps:")
    print("   1. Start the FastAPI server: uvicorn main:app --reload")
    print("   2. Test LinkedIn Scout endpoint: POST /api/v1/linkedin/scout")
    print("   3. Verify mock profiles are returned (no scraping)")
    print("\n")

if __name__ == "__main__":
    test_mock_mode()
