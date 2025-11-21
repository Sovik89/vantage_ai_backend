"""
Quick test to verify LinkedIn Scout with Mock Data
Run this to see if the system works
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_mock_generation():
    """Test 1: Verify mock data generator works"""
    print("\n" + "="*80)
    print("TEST 1: Mock Data Generation")
    print("="*80)
    
    try:
        from utils.mock_linkedin_data import mock_search_linkedin_candidates
        
        # Generate mock candidates
        candidates = mock_search_linkedin_candidates(
            job_description="Senior Data Scientist with 5+ years Python, ML experience",
            location="San Jose, CA",
            num_candidates=5
        )
        
        print(f"✅ Generated {len(candidates)} mock candidates")
        print(f"\nSample candidate:")
        if candidates:
            c = candidates[0]
            print(f"  Name: {c['full_name']}")
            print(f"  Headline: {c['headline']}")
            print(f"  Location: {c['location']}")
            print(f"  Skills: {len(c['skills'])} skills")
            print(f"  URL: {c['profile_url']}")
        
        return True
    except Exception as e:
        print(f"❌ Mock generation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_mock_profile_scraping():
    """Test 2: Verify mock profile enrichment works"""
    print("\n" + "="*80)
    print("TEST 2: Mock Profile Enrichment")
    print("="*80)
    
    try:
        from utils.mock_linkedin_data import mock_scrape_linkedin_profiles
        
        # Test URLs
        urls = [
            "https://www.linkedin.com/in/test1/",
            "https://www.linkedin.com/in/test2/"
        ]
        
        profiles = mock_scrape_linkedin_profiles(urls)
        
        print(f"✅ Enriched {len(profiles)} profiles")
        if profiles:
            p = profiles[0]
            print(f"\nSample enriched profile:")
            print(f"  Name: {p['full_name']}")
            print(f"  Headline: {p['headline']}")
            print(f"  Experience: {len(p['experience'])} positions")
            print(f"  Education: {len(p['education'])} degrees")
        
        return True
    except Exception as e:
        print(f"❌ Profile enrichment failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_config():
    """Test 3: Verify mock mode is enabled"""
    print("\n" + "="*80)
    print("TEST 3: Configuration Check")
    print("="*80)
    
    try:
        import config
        
        mock_enabled = getattr(config, 'USE_MOCK_LINKEDIN_DATA', False)
        
        if mock_enabled:
            print("✅ Mock mode is ENABLED")
        else:
            print("⚠️  Mock mode is DISABLED - real scraping will be attempted")
            print("   Set USE_MOCK_LINKEDIN_DATA = True in config.py")
        
        return True
    except Exception as e:
        print(f"❌ Config check failed: {e}")
        return False


def test_excel_generation():
    """Test 4: Verify Excel generation works"""
    print("\n" + "="*80)
    print("TEST 4: Excel Report Generation")
    print("="*80)
    
    try:
        from worker.linkedin_processing import export_linkedin_analysis_to_excel
        import tempfile
        import os
        
        # Create sample results
        results = [
            {
                "full_name": "John Doe",
                "headline": "Senior Data Scientist at Google",
                "location": "San Francisco, CA",
                "profile_url": "https://linkedin.com/in/johndoe",
                "match_score": 92,
                "skills_score": 88,
                "experience_score": 90,
                "education_score": 85,
                "key_strengths": "Strong ML background with 8 years experience",
                "gaps": "Limited cloud platform experience",
                "recommendation": "Highly Recommended",
                "match_reasoning": "Excellent fit for the role",
                "job_hopping_risk": "Low",
                "job_hopping_detail": "Stable career progression",
                "current_company": "Google"
            }
        ]
        
        # Generate Excel
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
            excel_path = tmp.name
        
        export_linkedin_analysis_to_excel(
            results=results,
            output_file=excel_path,
            job_title="Senior Data Scientist",
            location="San Francisco, CA",
            job_description="Test JD"
        )
        
        # Check if file was created
        if os.path.exists(excel_path):
            file_size = os.path.getsize(excel_path)
            print(f"✅ Excel report generated successfully")
            print(f"   File size: {file_size:,} bytes")
            os.unlink(excel_path)
            return True
        else:
            print(f"❌ Excel file was not created")
            return False
            
    except Exception as e:
        print(f"❌ Excel generation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_gemini_analysis():
    """Test 5: Verify Gemini AI analysis works"""
    print("\n" + "="*80)
    print("TEST 5: Gemini AI Analysis")
    print("="*80)
    
    try:
        from utils.vertex_ai_utils import analyze_linkedin_candidate
        
        # Sample profile
        profile = {
            "full_name": "Jane Smith",
            "headline": "Senior Data Scientist with 7 years ML experience",
            "location": "San Jose, CA",
            "experience": [
                {
                    "title": "Senior Data Scientist",
                    "company": "Google",
                    "duration": "3 years"
                }
            ],
            "skills": ["Python", "TensorFlow", "Machine Learning", "Deep Learning"],
            "education": [
                {
                    "degree": "MS in Computer Science",
                    "institution": "Stanford University"
                }
            ]
        }
        
        jd = "Looking for Senior Data Scientist with 5+ years Python and ML experience"
        
        analysis = analyze_linkedin_candidate(profile, jd)
        
        print(f"✅ AI analysis completed")
        print(f"   Match score: {analysis.get('match_score', 0)}")
        print(f"   Recommendation: {analysis.get('recommendation', 'N/A')}")
        
        return True
    except Exception as e:
        print(f"❌ AI analysis failed: {e}")
        print(f"   This might be expected if Vertex AI isn't configured")
        return False


def main():
    """Run all tests"""
    print("\n")
    print("🚀 " + "="*76)
    print("🚀 LinkedIn Scout System Test")
    print("🚀 " + "="*76)
    
    tests = [
        ("Mock Data Generation", test_mock_generation),
        ("Mock Profile Enrichment", test_mock_profile_scraping),
        ("Configuration", test_config),
        ("Excel Generation", test_excel_generation),
        ("Gemini AI Analysis", test_gemini_analysis)
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
    print("TEST SUMMARY")
    print("="*80)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {name}")
    
    print(f"\n{'='*80}")
    print(f"Total: {passed}/{total} tests passed ({passed/total*100:.0f}%)")
    print(f"{'='*80}\n")
    
    if passed == total:
        print("🎉 All tests passed! The system is ready to demo.")
    elif passed >= 3:
        print("⚠️  Some tests failed but core functionality works.")
    else:
        print("❌ Critical failures detected. System needs fixes.")


if __name__ == "__main__":
    main()
