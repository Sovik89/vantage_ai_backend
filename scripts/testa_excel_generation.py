"""
Standalone test to verify Excel generation with pandas and openpyxl
"""
import pandas as pd
import os
from datetime import datetime

# Test data
test_data = {
    "filename": "test.xlsx",
    "total_overall": 30,
    "pos_overall": 20,
    "neg_overall": 5,
    "neu_overall": 5,
    "sentiment_index_overall": 0.5,
    "avg_conf_overall": 0.85,
    "domain": "training_feedback",
    "detected_domains_list": ["training_feedback", "onboarding_feedback"],
    "ai_summary": "Generally positive feedback about training with some concerns about technical setup."
}

overall_details = [
    {"text_id": "1", "question_id": "Q1", "text_snippet": "Great training!", "label": "positive", "confidence": 0.95},
    {"text_id": "2", "question_id": "Q2", "text_snippet": "Laptop issues", "label": "negative", "confidence": 0.80},
    {"text_id": "3", "question_id": "Q3", "text_snippet": "It was okay", "label": "neutral", "confidence": 0.65},
]

questionnaire_summaries = [
    {
        "questionnaire_id": "Q001",
        "questionnaire_name": "Sheet1",
        "total_texts": 30,
        "positive_count": 20,
        "negative_count": 5,
        "neutral_count": 5,
        "average_confidence": 0.85,
        "sentiment_index": 0.5
    }
]

print("Creating test Excel file...")

# Sheet 1: Executive Summary
exec_summary_data = {
    "Metric": [
        "File Name",
        "Processing Date",
        "Total Responses",
        "Positive Count",
        "Negative Count",
        "Neutral Count",
        "Positive %",
        "Negative %",
        "Neutral %",
        "Sentiment Index",
        "Average Confidence",
        "Detected Domains",
        "AI Generated Summary"
    ],
    "Value": [
        test_data["filename"],
        datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        test_data["total_overall"],
        test_data["pos_overall"],
        test_data["neg_overall"],
        test_data["neu_overall"],
        f"{(test_data['pos_overall']/test_data['total_overall']*100):.1f}%",
        f"{(test_data['neg_overall']/test_data['total_overall']*100):.1f}%",
        f"{(test_data['neu_overall']/test_data['total_overall']*100):.1f}%",
        f"{test_data['sentiment_index_overall']:.3f}",
        f"{test_data['avg_conf_overall']:.3f}",
        ", ".join(test_data["detected_domains_list"]),
        test_data["ai_summary"]
    ]
}
df_exec = pd.DataFrame(exec_summary_data)
print(f"✓ Executive Summary: {len(df_exec)} rows")

# Sheet 2: Detailed Feedback
feedback_data = []
for detail in overall_details:
    feedback_data.append({
        "Text ID": detail["text_id"],
        "Question ID": detail["question_id"],
        "Feedback Text": detail["text_snippet"],
        "Sentiment": detail["label"],
        "Confidence": f"{detail['confidence']:.3f}",
        "Confidence Level": "High" if detail['confidence'] > 0.85 else ("Low" if detail['confidence'] < 0.6 else "Medium")
    })
df_feedback = pd.DataFrame(feedback_data)
print(f"✓ Detailed Feedback: {len(df_feedback)} rows")

# Sheet 3: Questionnaire Summary
questionnaire_data = []
for s in questionnaire_summaries:
    questionnaire_data.append({
        "Questionnaire ID": s["questionnaire_id"],
        "Questionnaire Name": s["questionnaire_name"],
        "Total Responses": s["total_texts"],
        "Positive": s["positive_count"],
        "Negative": s["negative_count"],
        "Neutral": s["neutral_count"],
        "Positive %": f"{(s['positive_count']/s['total_texts']*100):.1f}%",
        "Avg Confidence": f"{s['average_confidence']:.3f}",
        "Sentiment Index": f"{s['sentiment_index']:.3f}"
    })
df_questionnaire = pd.DataFrame(questionnaire_data)
print(f"✓ Questionnaire Summary: {len(df_questionnaire)} rows")

# Sheet 4: Confidence Analysis
from statistics import mean
confidence_analysis = []
for label in ["positive", "negative", "neutral"]:
    label_items = [d for d in overall_details if d["label"] == label]
    if label_items:
        confidences = [d["confidence"] for d in label_items]
        confidence_analysis.append({
            "Sentiment": label.capitalize(),
            "Count": len(label_items),
            "Avg Confidence": f"{mean(confidences):.3f}",
            "Min Confidence": f"{min(confidences):.3f}",
            "Max Confidence": f"{max(confidences):.3f}",
            "High (>0.85)": sum(1 for c in confidences if c > 0.85),
            "Medium (0.6-0.85)": sum(1 for c in confidences if 0.6 <= c <= 0.85),
            "Low (<0.6)": sum(1 for c in confidences if c < 0.6)
        })
df_confidence = pd.DataFrame(confidence_analysis)
print(f"✓ Confidence Analysis: {len(df_confidence)} rows")

# Sheet 5: Key Insights
insights_data = {
    "Category": [
        "Overall Assessment",
        "Strengths",
        "Data Quality"
    ],
    "Insight": [
        f"Sentiment Index of {test_data['sentiment_index_overall']:.3f} indicates positive sentiment.",
        f"{test_data['pos_overall']} positive responses ({(test_data['pos_overall']/test_data['total_overall']*100):.1f}%).",
        f"Average confidence of {test_data['avg_conf_overall']:.3f} indicates strong certainty."
    ]
}
df_insights = pd.DataFrame(insights_data)
print(f"✓ Key Insights: {len(df_insights)} rows")

# Write to Excel
output_file = "test_sentiment_report.xlsx"
print(f"\nWriting to {output_file}...")

try:
    with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
        df_exec.to_excel(writer, sheet_name="Executive Summary", index=False)
        df_feedback.to_excel(writer, sheet_name="Detailed Feedback", index=False)
        df_questionnaire.to_excel(writer, sheet_name="Questionnaire Summary", index=False)
        df_confidence.to_excel(writer, sheet_name="Confidence Analysis", index=False)
        df_insights.to_excel(writer, sheet_name="Key Insights", index=False)
        
        # Auto-adjust column widths
        for sheet_name in writer.sheets:
            worksheet = writer.sheets[sheet_name]
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if cell.value:
                            max_length = max(max_length, len(str(cell.value)))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 100)
                worksheet.column_dimensions[column_letter].width = adjusted_width
    
    print(f"✅ SUCCESS! Excel file created: {os.path.abspath(output_file)}")
    print(f"\n📊 File contains 5 sheets:")
    print(f"   1. Executive Summary")
    print(f"   2. Detailed Feedback")
    print(f"   3. Questionnaire Summary")
    print(f"   4. Confidence Analysis")
    print(f"   5. Key Insights")
    print(f"\nOpen the file to verify all sheets are present.")
    
except Exception as e:
    print(f"❌ ERROR: {e}")
    import traceback
    traceback.print_exc()