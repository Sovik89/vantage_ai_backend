# scripts/test_gemini_raw.py
import sys, os, json
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from utils import vertex_ai_utils

samples = [
  "I loved the training; the trainer was excellent and very helpful.",
  "No laptop on day one and no access to systems; onboarding failed.",
  "The cricket match was amazing last weekend."
]

print("DEBUG: utils.vertex_ai_utils loaded from:", vertex_ai_utils.__file__)
for i, s in enumerate(samples,1):
    print("\n--- SAMPLE",i,"---")
    try:
        # call the small internal function that uses Gemini and prints raw
        res = vertex_ai_utils.classify_texts_with_vertex([s], domain="training_feedback")
        print("RESULT:", res)
    except Exception as e:
        print("EXCEPTION:", e)
