"""
Sample Exit Feedback Excel Generator
Creates realistic test data for candidate-aware sentiment analysis
"""

import pandas as pd
import random
from datetime import datetime, timedelta

# Sample data pools for realistic exit feedback
CANDIDATE_NAMES = [
    "Sarah Johnson", "Michael Chen", "Priya Sharma", "James Williams", "Maria Garcia",
    "Ahmed Hassan", "Emily Brown", "Raj Patel", "Jessica Lee", "David Kumar",
    "Sophia Martinez", "Ryan O'Brien", "Aisha Khan", "Thomas Anderson", "Nina Desai",
    "Christopher Taylor", "Lakshmi Reddy", "Daniel Murphy", "Fatima Ali", "Andrew Kim",
    "Meera Iyer", "John Smith", "Ananya Gupta", "Robert Davis", "Kavya Nair",
    "William Jones", "Zara Ahmed", "Joseph Miller", "Roshni Verma", "Charles Wilson"
]

# Exit feedback questions
QUESTIONS = {
    "Q1_Reason_Leaving": "What is your primary reason for leaving the organization?",
    "Q2_Manager_Experience": "How would you rate your relationship with your immediate manager?",
    "Q3_Work_Environment": "How satisfied were you with the work environment and culture?",
    "Q4_Career_Growth": "Did you feel there were adequate opportunities for career growth?",
    "Q5_Recommendations": "What suggestions do you have for improving employee retention?"
}

# Response templates by sentiment
RESPONSES = {
    "Q1_Reason_Leaving": {
        "positive": [
            "I received an exciting opportunity for career advancement that aligned perfectly with my long-term goals.",
            "Found a role that offers better work-life balance and is closer to my family.",
            "Got an opportunity to work on cutting-edge technology that I'm passionate about.",
        ],
        "neutral": [
            "Relocating to another city due to personal reasons.",
            "Pursuing higher education to enhance my skills.",
            "Family commitments require my attention at this time.",
        ],
        "negative": [
            "Limited career growth opportunities and stagnant salary progression over the past two years.",
            "Excessive workload and unrealistic deadlines were causing burnout.",
            "Poor management practices and lack of support from leadership.",
            "Toxic work culture with favoritism and lack of transparency.",
            "No recognition for hard work and contributions to the team.",
        ]
    },
    "Q2_Manager_Experience": {
        "positive": [
            "My manager was extremely supportive, provided regular feedback, and helped me develop my skills.",
            "Great manager who always listened to concerns and advocated for the team.",
            "Excellent mentor who invested time in my professional growth.",
        ],
        "neutral": [
            "Manager was professional but had limited time for one-on-ones due to workload.",
            "Decent working relationship, though communication could have been more frequent.",
            "Manager was fair but not particularly involved in career development.",
        ],
        "negative": [
            "Manager was micromanaging every task and didn't trust the team's capabilities.",
            "Lack of feedback and guidance made it difficult to understand expectations.",
            "Manager showed favoritism and didn't treat all team members equally.",
            "Poor communication and unrealistic expectations created unnecessary stress.",
            "Manager was unavailable most of the time and didn't provide necessary support.",
        ]
    },
    "Q3_Work_Environment": {
        "positive": [
            "The workplace culture was inclusive, collaborative, and people were genuinely helpful.",
            "Great team dynamics with strong support from colleagues and leadership.",
            "Modern facilities, good work-life balance policies, and respect for diversity.",
        ],
        "neutral": [
            "Work environment was okay, nothing exceptional but professional.",
            "Office was decent though infrastructure could be improved.",
            "Team was professional but not particularly collaborative.",
        ],
        "negative": [
            "High-pressure environment with constant stress and unrealistic expectations.",
            "Office politics and gossip made the workplace uncomfortable.",
            "Poor infrastructure, outdated tools, and lack of proper resources.",
            "No work-life balance, expected to work long hours and weekends regularly.",
            "Lack of transparency and communication from senior leadership created uncertainty.",
        ]
    },
    "Q4_Career_Growth": {
        "positive": [
            "Yes, there were clear career paths and I was given challenging projects to grow.",
            "Regular training opportunities and mentorship programs helped my development.",
            "Multiple promotions based on merit and clear growth trajectory.",
        ],
        "neutral": [
            "Some opportunities existed but they were not clearly communicated.",
            "Growth was possible but required significantly more effort than expected.",
            "Opportunities were limited to specific departments.",
        ],
        "negative": [
            "No clear career progression path and promotions were rare.",
            "Stuck in the same role for years despite exceeding performance expectations.",
            "Training and development opportunities were almost non-existent.",
            "Favoritism determined promotions rather than merit or performance.",
            "Senior positions were filled externally rather than promoting from within.",
        ]
    },
    "Q5_Recommendations": {
        "positive": [
            "Continue the great work with employee engagement programs and maintain the open-door policy.",
            "Keep investing in employee development and the positive work culture.",
            "The organization is doing well, just need to stay competitive with market salaries.",
        ],
        "neutral": [
            "Improve communication between management and employees.",
            "Consider more flexible work arrangements.",
            "Update infrastructure and provide better tools.",
        ],
        "negative": [
            "Address the toxic work culture and hold managers accountable for their behavior.",
            "Provide clear career paths and invest in employee development programs.",
            "Improve compensation to match industry standards and recognize good work.",
            "Reduce workload expectations and respect work-life balance.",
            "Increase transparency in decision-making and stop favoritism in promotions.",
        ]
    }
}

def generate_candidate_feedback(num_candidates=28, sentiment_distribution=None):
    """
    Generate realistic exit feedback data
    
    Args:
        num_candidates: Number of candidates (default 28 for realistic scenario)
        sentiment_distribution: Dict with 'positive', 'neutral', 'negative' percentages
                               Default: {'positive': 25, 'neutral': 20, 'negative': 55}
    """
    
    if sentiment_distribution is None:
        # Realistic exit feedback distribution (typically more negative)
        sentiment_distribution = {
            'positive': 0.25,  # 25% leaving for positive reasons
            'neutral': 0.20,   # 20% neutral/personal reasons
            'negative': 0.55   # 55% leaving due to issues
        }
    
    data = []
    
    for i in range(num_candidates):
        candidate_id = f"EMP{str(i+1001).zfill(4)}"
        candidate_name = CANDIDATE_NAMES[i] if i < len(CANDIDATE_NAMES) else f"Employee {i+1}"
        
        # Assign overall sentiment to this candidate
        rand = random.random()
        if rand < sentiment_distribution['positive']:
            primary_sentiment = 'positive'
        elif rand < sentiment_distribution['positive'] + sentiment_distribution['neutral']:
            primary_sentiment = 'neutral'
        else:
            primary_sentiment = 'negative'
        
        # Generate responses with some variation around primary sentiment
        row = {
            "Candidate ID": candidate_id,
            "Candidate Name": candidate_name,
        }
        
        for q_id, q_text in QUESTIONS.items():
            # 70% match primary sentiment, 30% variation
            if random.random() < 0.7:
                sentiment = primary_sentiment
            else:
                # Add some variation
                other_sentiments = [s for s in ['positive', 'neutral', 'negative'] if s != primary_sentiment]
                sentiment = random.choice(other_sentiments)
            
            # Pick a response
            response = random.choice(RESPONSES[q_id][sentiment])
            row[q_id] = response
        
        data.append(row)
    
    return pd.DataFrame(data)


def generate_multiple_feedback_types():
    """Generate multiple sheets for different feedback types"""
    
    # 1. Exit Feedback (realistic scenario: 28 candidates, 5 questions each)
    df_exit = generate_candidate_feedback(
        num_candidates=28,
        sentiment_distribution={'positive': 0.25, 'neutral': 0.20, 'negative': 0.55}
    )
    
    # 2. Onboarding Feedback (more positive: 20 candidates)
    onboarding_names = CANDIDATE_NAMES[:20]
    onboarding_questions = {
        "Q1_First_Day": "How was your first day experience?",
        "Q2_Orientation": "Was the orientation program helpful?",
        "Q3_IT_Setup": "Were you provided with necessary equipment and access on time?",
        "Q4_Team_Welcome": "How welcoming was your team?",
        "Q5_Overall": "Overall, how would you rate your onboarding experience?"
    }
    
    onboarding_data = []
    for i in range(20):
        # Onboarding typically more positive
        sentiment = random.choices(
            ['positive', 'neutral', 'negative'],
            weights=[0.60, 0.25, 0.15]
        )[0]
        
        responses = {
            "positive": [
                "Excellent experience, everything was well organized.",
                "Very smooth process, felt welcomed from day one.",
                "Great support from HR and team members.",
            ],
            "neutral": [
                "Good overall but some delays in system access.",
                "Process was okay, could be more streamlined.",
                "Adequate but not exceptional.",
            ],
            "negative": [
                "Poor planning, no laptop on first day.",
                "Confusing process with lack of clear guidance.",
                "No proper orientation, felt lost initially.",
            ]
        }
        
        row = {
            "Candidate ID": f"NEW{str(i+1).zfill(3)}",
            "Candidate Name": onboarding_names[i],
        }
        
        for q_id in onboarding_questions.keys():
            row[q_id] = random.choice(responses[sentiment])
        
        onboarding_data.append(row)
    
    df_onboarding = pd.DataFrame(onboarding_data)
    
    # 3. Training Feedback (very positive: 15 candidates)
    training_names = CANDIDATE_NAMES[:15]
    training_questions = {
        "Q1_Content": "Was the training content relevant and useful?",
        "Q2_Trainer": "How effective was the trainer?",
        "Q3_Duration": "Was the training duration appropriate?",
        "Q4_Materials": "Were the training materials helpful?",
    }
    
    training_data = []
    for i in range(15):
        sentiment = random.choices(
            ['positive', 'neutral', 'negative'],
            weights=[0.70, 0.20, 0.10]
        )[0]
        
        responses = {
            "positive": [
                "Excellent training, very engaging and practical.",
                "Trainer was knowledgeable and made it interesting.",
                "Great content with hands-on exercises.",
            ],
            "neutral": [
                "Good but could have more interactive sessions.",
                "Content was okay, delivery could be improved.",
            ],
            "negative": [
                "Too theoretical, lacked practical examples.",
                "Trainer was not well prepared.",
            ]
        }
        
        row = {
            "Candidate ID": f"TRN{str(i+1).zfill(3)}",
            "Candidate Name": training_names[i],
        }
        
        for q_id in training_questions.keys():
            row[q_id] = random.choice(responses[sentiment])
        
        training_data.append(row)
    
    df_training = pd.DataFrame(training_data)
    
    return df_exit, df_onboarding, df_training


def save_sample_files():
    """Save sample Excel files for testing"""
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 1. Single sheet: Exit Feedback only
    print("📄 Generating Exit Feedback (single sheet)...")
    df_exit = generate_candidate_feedback(num_candidates=28)
    exit_filename = f"exit_feedback_sample_{timestamp}.xlsx"
    df_exit.to_excel(exit_filename, index=False, sheet_name="Exit Feedback")
    print(f"✅ Saved: {exit_filename}")
    print(f"   - 28 candidates")
    print(f"   - 5 questions per candidate")
    print(f"   - Total: {len(df_exit) * 5} responses")
    
    # 2. Multi-sheet: All feedback types
    print("\n📚 Generating Multi-Sheet Feedback...")
    df_exit, df_onboarding, df_training = generate_multiple_feedback_types()
    
    multi_filename = f"all_feedback_types_{timestamp}.xlsx"
    with pd.ExcelWriter(multi_filename, engine='openpyxl') as writer:
        df_exit.to_excel(writer, sheet_name='Exit Feedback', index=False)
        df_onboarding.to_excel(writer, sheet_name='Onboarding Feedback', index=False)
        df_training.to_excel(writer, sheet_name='Training Feedback', index=False)
    
    print(f"✅ Saved: {multi_filename}")
    print(f"   - Sheet 1: Exit Feedback (28 candidates, 5 questions)")
    print(f"   - Sheet 2: Onboarding Feedback (20 candidates, 5 questions)")
    print(f"   - Sheet 3: Training Feedback (15 candidates, 4 questions)")
    
    # 3. High-risk scenario (mostly negative)
    print("\n⚠️ Generating High-Risk Scenario...")
    df_risk = generate_candidate_feedback(
        num_candidates=25,
        sentiment_distribution={'positive': 0.10, 'neutral': 0.15, 'negative': 0.75}
    )
    risk_filename = f"exit_feedback_high_risk_{timestamp}.xlsx"
    df_risk.to_excel(risk_filename, index=False, sheet_name="Exit Feedback")
    print(f"✅ Saved: {risk_filename}")
    print(f"   - 25 candidates")
    print(f"   - 75% negative sentiment (high risk)")
    
    print("\n" + "="*60)
    print("🎉 All sample files generated successfully!")
    print("="*60)
    print("\n📋 File Descriptions:")
    print(f"\n1. {exit_filename}")
    print("   → Realistic exit feedback distribution")
    print("   → Use this to test your sentiment_processing.py")
    
    print(f"\n2. {multi_filename}")
    print("   → Multiple feedback types in one file")
    print("   → Tests multi-sheet processing")
    
    print(f"\n3. {risk_filename}")
    print("   → High-risk scenario with mostly negative feedback")
    print("   → Tests risk detection and alerts")
    
    print("\n💡 Quick Start:")
    print(f"   python your_test_script.py --file {exit_filename}")
    
    return exit_filename, multi_filename, risk_filename


# Generate the files
if __name__ == "__main__":
    print("\n" + "="*60)
    print("🚀 Sample Exit Feedback Generator")
    print("="*60 + "\n")
    
    save_sample_files()
    
    print("\n✨ You can now test these files with your sentiment processing system!")
    print("   The files include:")
    print("   - Candidate ID and Name columns")
    print("   - Multiple question columns")
    print("   - Realistic positive/neutral/negative responses")
    print("   - Proper Excel formatting")