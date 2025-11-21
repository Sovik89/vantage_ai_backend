from utils.vertex_ai_utils import summarize_text, generate_freeform
from utils.vector_utils import search_similar_papers
from utils.prompts import HR_TEXT_CLASSIFIER_PROMPT, HR_QUERY_CLASSIFIER_PROMPT, HR_PA_CONTENT_CLASSIFIER_PROMPT
from io import BytesIO  
import re

# This file contains the logic for classifying user queries and documents to ensure relevance.

def classify_topic(query: str) -> bool:
    """
    Checks if a user's question is related to HR or People Analytics using a prompt from prompts.py.
    This is used as an initial gatekeeper for user input.
    """
    check_prompt = HR_QUERY_CLASSIFIER_PROMPT.format(query=query)
    try:
        # Call the LLM for classification
        res = summarize_text(check_prompt).strip().upper()
        return res.startswith("YES")
    except Exception as e:
        print(f"Error in classify_topic: {e}")
        return False

# def is_hr_text(text: str) -> bool:
#     """
#     A strict document classifier that enforces the GIGO (Garbage In, Garbage Out) principle.
#     It uses a highly detailed and specific prompt from prompts.py to validate uploaded documents.
#     """
#     # Use a substantial snippet of the text to give the classifier enough context
#     snippet = text[:3000]

#     # Format the detailed prompt with the text snippet
#     check_prompt = HR_TEXT_CLASSIFIER_PROMPT.format(snippet=snippet)

#     try:
#         # Call the LLM for classification
#         res = summarize_text(check_prompt).strip().upper()
#         # The prompt is designed to return a definitive "YES" for relevant documents
#         return res == "YES"
#     except Exception as e:
#         print(f"Error in is_hr_text: {e}")
#         return False

def is_hr_text(text: str) -> bool:
    """
    A strict document classifier that enforces the GIGO (Garbage In, Garbage Out) principle.
    It uses a highly detailed and specific prompt from prompts.py to validate uploaded documents.
    """
    snippet = text[:3000]
    check_prompt = HR_TEXT_CLASSIFIER_PROMPT.format(snippet=snippet)

    try:
        res = summarize_text(check_prompt).strip().upper()
        # ✅ **FIX:** The prompt now returns "ACCEPT", so we check for that keyword.
        return res == "ACCEPT"
    except Exception as e:
        print(f"Error in is_hr_text: {e}")
        return False

def is_hr_pa_content(text: str) -> bool:
    """
    Enhanced validation for both HR and People Analytics content
    """
    try:
        response = generate_freeform(
            HR_PA_CONTENT_CLASSIFIER_PROMPT.format(snippet=text[:10000])
        ).strip().upper()
        
        is_valid = response == "ACCEPT"
        
        print(f"📊 Content Validation:")
        print(f"   Response: {response}")
        print(f"   Valid HR/PA content: {'✅' if is_valid else '❌'}")
        
        return is_valid
        
    except Exception as e:
        print(f"⚠️ Validation error: {e}")
        return True  # Fail open for production stability

def detect_metric_and_filter(candidates):
    """
    Filters a list of candidate documents from a vector search based on their distance scores.
    This helps in selecting the most relevant documents to use as context.
    """
    if not candidates:
        return []

    # We are using 'COSINE' distance where a lower score (closer to 0) means more similar.
    # A threshold of 0.1 is a reasonable starting point for relevance.
    similarity_threshold = 0.1

    # Filter candidates whose distance is below the threshold and sort them by relevance (lowest distance first)
    relevant_matches = [
        c for c in candidates if c.get("distance", 1.0) <= similarity_threshold
    ]

    return sorted(relevant_matches, key=lambda x: x.get("distance", 1.0))

