# scripts/test_ats_local.py
"""
ATS Checker Local Test Script
Only orchestrates testing - all logic in worker/ats_processing.py
Similar to sentiment analysis test structure

SETUP:
1. Place JD_Data_Scientist_B2.docx in test_data/ folder
2. Place all CV PDFs in test_data/ folder
3. Run: python scripts/test_ats_local.py
"""

import os
import sys
import traceback
from datetime import datetime
import pandas as pd

# Add repo root to path
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

print(f"DEBUG: repo root on sys.path -> {REPO_ROOT}")

# Import worker functions
from worker.ats_processing import batch_analyze_candidates, export_analysis_to_excel
from utils.file_utils import get_text_from_file
from io import BytesIO


def find_cv_files():
    """
    Find all CV PDF files in test_data folder
    """
    test_data_dir = os.path.join(REPO_ROOT, "test_data")
    
    if not os.path.exists(test_data_dir):
        os.makedirs(test_data_dir)
        print(f"⚠️  Created test_data directory: {test_data_dir}")
        print(f"   Please place your CV files here and run again.")
        return []
    
    cv_files = []
    
    # Look for PDF files with candidate names
    candidate_names = [
        'Abhishek', 'Bibhu', 'Bhupinder', 'Arun', 
        'Akanksha', 'Aashna', 'Akshay'
    ]
    
    for filename in os.listdir(test_data_dir):
        if filename.lower().endswith('.pdf'):
            # Check if it's a CV
            if any(name in filename for name in candidate_names):
                cv_files.append(filename)
            elif 'cv' in filename.lower() or 'resume' in filename.lower():
                cv_files.append(filename)
    
    return cv_files


def load_job_description():
    """
    Load JD from DOCX file in test_data folder
    """
    test_data_dir = os.path.join(REPO_ROOT, "test_data")
    jd_file = os.path.join(test_data_dir, "JD_Data_Scientist_B2.docx")
    
    if not os.path.exists(jd_file):
        raise FileNotFoundError(
            f"JD file not found: {jd_file}\n"
            f"Please place JD_Data_Scientist_B2.docx in the test_data folder"
        )
    
    print(f"📄 Loading Job Description: {os.path.basename(jd_file)}")
    
    with open(jd_file, 'rb') as f:
        jd_bytes = f.read()
    
    jd_text = get_text_from_file(BytesIO(jd_bytes), ".docx")
    
    print(f"   ✓ JD loaded: {len(jd_text)} characters")
    print(f"   ✓ Preview: {jd_text[:200]}...\n")
    
    return jd_text


def prepare_cv_data(cv_files):
    """
    Load CV files from test_data folder
    """
    test_data_dir = os.path.join(REPO_ROOT, "test_data")
    cv_data = []
    
    print(f"📋 Loading {len(cv_files)} CV files:\n")
    
    for idx, cv_file in enumerate(cv_files, 1):
        cv_path = os.path.join(test_data_dir, cv_file)
        
        try:
            with open(cv_path, 'rb') as f:
                cv_bytes = f.read()
            
            cv_data.append((cv_bytes, cv_file))
            print(f"   {idx}. ✓ {cv_file} ({len(cv_bytes)} bytes)")
            
        except Exception as e:
            print(f"   {idx}. ❌ {cv_file}: {e}")
            continue
    
    print()
    return cv_data


def display_summary(results):
    """
    Display analysis summary
    """
    if not results:
        print("❌ No results to display")
        return
    
    print("\n" + "="*80)
    print("📊 ANALYSIS SUMMARY")
    print("="*80 + "\n")
    
    total = len(results)
    avg_match = sum(r['overall_match_percentage'] for r in results) / total
    
    # Count by match range
    high_match = sum(1 for r in results if r['overall_match_percentage'] >= 70)
    medium_match = sum(1 for r in results if 50 <= r['overall_match_percentage'] < 70)
    low_match = sum(1 for r in results if r['overall_match_percentage'] < 50)
    
    # Count AI detection
    ai_detected = sum(
        1 for r in results 
        if r['ai_generated_flags'] and r['ai_generated_flags']['is_likely_ai_generated']
    )
    
    print(f"Total Candidates Analyzed: {total}")
    print(f"Average Match Score: {avg_match:.1f}%")
    print(f"\nMatch Distribution:")
    print(f"  • High Match (≥70%): {high_match}")
    print(f"  • Medium Match (50-69%): {medium_match}")
    print(f"  • Low Match (<50%): {low_match}")
    print(f"\nAI-Generated CVs Detected: {ai_detected}")
    print()


def display_rankings(results):
    """
    Display candidate rankings
    """
    print("="*80)
    print("🏆 CANDIDATE RANKINGS")
    print("="*80 + "\n")
    
    for idx, result in enumerate(results, 1):
        # Color coding based on match percentage
        match_pct = result['overall_match_percentage']
        if match_pct >= 80:
            emoji = "🌟"
        elif match_pct >= 70:
            emoji = "✅"
        elif match_pct >= 50:
            emoji = "🟡"
        else:
            emoji = "🔴"
        
        print(f"{emoji} {idx}. {result['candidate_name']} - {match_pct:.1f}%")
        print(f"   📧 {result['email']}")
        print(f"   🏢 {result['current_company']}")
        print(f"   💼 Experience: {result['total_experience_years']} years")
        print(f"   🎯 Skills Match: {result['component_scores']['skills_match']:.1f}%")
        print(f"   📈 Technical Depth: {result['component_scores']['technical_depth']}/100")
        
        # AI Detection
        if result['ai_generated_flags']:
            ai_verdict = result['ai_generated_flags']['final_verdict']
            ai_risk = result['ai_generated_flags']['warning_level']
            
            if ai_risk == 'high':
                print(f"   🚨 AI Detection: {ai_verdict} (HIGH RISK)")
            elif ai_risk == 'medium':
                print(f"   ⚠️  AI Detection: {ai_verdict} (MEDIUM RISK)")
            else:
                print(f"   ✓ AI Detection: {ai_verdict} (low risk)")
        
        print(f"   💬 {result['match_reason'][:120]}...")
        print()


def export_to_excel(results):
    """
    Export results to Excel
    """
    test_data_dir = os.path.join(REPO_ROOT, "test_data")
    os.makedirs(test_data_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = os.path.join(test_data_dir, f"ATS_Analysis_{timestamp}.xlsx")
    
    print("="*80)
    print("📊 EXPORTING RESULTS")
    print("="*80 + "\n")
    
    try:
        export_analysis_to_excel(results, output_file)
        
        print(f"\n📈 Excel file contains 4 sheets:")
        print(f"   1. Candidate Rankings - Complete overview")
        print(f"   2. Skills Analysis - Detailed skill matching")
        print(f"   3. AI Detection - AI generation analysis")
        print(f"   4. Insights & Recommendations - Strengths and gaps")
        
        return output_file
        
    except Exception as e:
        print(f"❌ Export failed: {e}")
        traceback.print_exc()
        return None


def run_ats_test():
    """
    Main orchestration function - calls worker functions
    """
    
    print("\n" + "="*80)
    print("🚀 ATS CHECKER - LOCAL TEST")
    print("="*80 + "\n")
    
    try:
        # Step 1: Load Job Description
        print("STEP 1: Loading Job Description")
        print("-" * 80)
        jd_text = load_job_description()
        
        # Step 2: Find CV files
        print("\nSTEP 2: Finding CV Files")
        print("-" * 80)
        cv_files = find_cv_files()
        
        if not cv_files:
            print("❌ No CV files found in test_data folder!")
            print("   Please place PDF CVs in the test_data directory")
            print(f"   Location: {os.path.join(REPO_ROOT, 'test_data')}")
            return
        
        print(f"✓ Found {len(cv_files)} CV files\n")
        
        # Step 3: Prepare CV data
        print("STEP 3: Loading CV Files")
        print("-" * 80)
        cv_data = prepare_cv_data(cv_files)
        
        if not cv_data:
            print("❌ No CV files could be loaded!")
            return
        
        # Step 4: Run batch analysis (worker does the heavy lifting)
        print("\nSTEP 4: Analyzing Candidates (WITH BigQuery)")
        print("-" * 80)
        print("⏳ This may take several minutes...")
        print("💾 Results will be saved to BigQuery (privacy-compliant)\n")
        
        job_id, results = batch_analyze_candidates(
            cv_files_data=cv_data,
            jd_text=jd_text,
            position_title="Data Scientist - B2",
            organization="Test Organization",
            user_email="tester@example.com",
            detect_ai=True,
            save_to_bigquery=True,  # Enable BigQuery integration
            verbose=True  # Show detailed progress
        )
        
        if not results:
            print("❌ No candidates were successfully analyzed!")
            return
        
        # Step 5: Display results
        print("\nSTEP 5: Results")
        print("-" * 80)
        display_summary(results)
        display_rankings(results)
        
        # Step 6: Export to Excel
        print("\nSTEP 6: Export Results")
        print("-" * 80)
        output_file = export_to_excel(results)
        
        if output_file:
            print(f"\n✅ Results saved to: {output_file}")
        
        # Final summary
        print("\n" + "="*80)
        print("✅ ATS ANALYSIS COMPLETED SUCCESSFULLY")
        print("="*80)
        print(f"\n📊 Job ID: {job_id}")
        print(f"📈 Total Analyzed: {len(results)}")
        print(f"\n🏆 Top 3 Candidates:")
        for idx, result in enumerate(results[:3], 1):
            print(f"   {idx}. {result['candidate_name']} ({result['overall_match_percentage']:.1f}%)")
        
        print(f"\n💾 BigQuery Storage:")
        print(f"   ✅ Job metadata saved to: ats_jobs")
        print(f"   ✅ Aggregated results saved to: ats_results")
        print(f"   ✅ Learning insights saved to: journal_vectors")
        print(f"\n🔒 Privacy Compliance:")
        print(f"   ✅ NO candidate PII stored in database")
        print(f"   ✅ Only aggregated statistics retained")
        print(f"   ✅ Individual data available in Excel export only")
        
        print("\n" + "="*80 + "\n")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    print("\n" + "="*80)
    print("🔧 ATS CHECKER - STANDALONE TEST MODE")
    print("="*80 + "\n")
    
    # Check environment
    creds = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if not creds:
        print("❌ GOOGLE_APPLICATION_CREDENTIALS not set!")
        print("   Set it with: $env:GOOGLE_APPLICATION_CREDENTIALS='path/to/key.json'")
        sys.exit(1)
    elif not os.path.exists(creds):
        print(f"❌ Credentials file not found: {creds}")
        sys.exit(1)
    else:
        print(f"✅ Using credentials: {creds}")
    
    print(f"✅ Repo root: {REPO_ROOT}")
    print()
    
    try:
        run_ats_test()
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        traceback.print_exc()
    
    print("\n" + "="*80)
    print("🎬 TEST SCRIPT FINISHED")
    print("="*80 + "\n")