# utils/bias_utils.py
import re

PROTECTED_TERMS = {
    "gender": ["woman","man","female","male","girl","boy","she","he"],
    "ethnicity": ["caste","hindu","muslim","indian","asian","pakistani","bangladeshi","african","black"],
    "age": ["young","old","age","years old"],
    "disability": ["disability","disabled","wheelchair","autism"],
    "religion": ["christian","muslim","hindu","jewish","sikh","buddhist",'jain'],
}

def detect_bias_flags(text: str, domain: str = "general"):
    """
    Returns (flags_list, short_explanation)
    """
    t = text.lower()
    flags = []
    explanation = []
    # protected attribute scanning
    for k, keywords in PROTECTED_TERMS.items():
        for kw in keywords:
            if kw in t:
                flags.append("protected_attribute_mentioned")
                explanation.append(f"Possible mention of {k} ({kw})")
                break
    # performance bias heuristic for interview feedback
    if domain == "interview_feedback":
        if any(w in t for w in ("failed","didn't clear","not selected","rejected")):
            flags.append("performance_bias_possible")
            explanation.append("Mentions of failure/outcome may conflate selection with competence.")
    # sarcasm / low confidence heuristics
    if "!" in text or "??" in text or any(emo in text for emo in [":)",":("]):
        flags.append("tone_marker")
    # return unique list
    return list(set(flags)), "; ".join(explanation)
