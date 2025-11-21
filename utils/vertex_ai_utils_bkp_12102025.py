import json
import re
import time
import random
import vertexai
from vertexai.generative_models import GenerativeModel
from vertexai.language_models import TextEmbeddingModel
import config
import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
# utils/vertex_ai_utils.py
from utils.prompts import SENTIMENT_PROMPTS

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
analyzer = SentimentIntensityAnalyzer()

POSITIVE_WORDS = [
        "good","great","excellent","amazing","supportive","helpful","positive","friendly",
        "encouraging","motivated","productive","valued","appreciated","collaborative","flexible",
        "fair","empowered","transparent","inclusive","growth","learned","improved","rewarding",
        "beneficial","fantastic","engaging","enjoyable","strong","efficient","clear","trustworthy",
        "constructive","valuable","adaptive","respected","innovative","commendable","uplifting"
    ]

NEGATIVE_WORDS = [
        "bad","poor","unfair","stressful","toxic","negative","inefficient","confusing",
        "frustrating","unclear","demotivating","overworked","disorganized","micromanaged",
        "biased","underpaid","unrecognized","slow","unresponsive","inflexible","unhelpful",
        "pressured","ignored","hostile","critical","excessive","burnout","lack","problem",
        "delay","complaint","rejected","failed","unavailable","incomplete","untrained","unhappy"
    ]


# from google.cloud import aiplatform

import math
from typing import List, Tuple, Dict

# Import Vertex libs only if available
try:
    from google.cloud import aiplatform
    _HAS_VERTEX = True
except Exception:
    _HAS_VERTEX = False

# Init Vertex AI
project=config.PROJECT_ID
location=config.LOCATION
vertexai.init(project=project, location=location)



# Load Gemini
gemini_model = GenerativeModel("gemini-2.5-flash-lite")

# Load Embedding model
embedding_model = TextEmbeddingModel.from_pretrained("text-embedding-004")


def _call_gemini_with_retry(prompt: str, retries: int = 3):
    """
    Internal helper to call Gemini API with exponential backoff for quota errors.
    """
    for attempt in range(retries):
        try:
            response = gemini_model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            # Check if the error is a quota-related (429) error
            if "429" in str(e) and attempt < retries - 1:
                sleep_time = (2 ** attempt) + random.random()
                print(f"⚠️ Quota hit (429). Retrying in {sleep_time:.1f}s...")
                time.sleep(sleep_time)
            else:
                # For non-retryable errors or final attempt, raise the exception
                raise e
    return "" # Should not be reached, but as a fallback


def summarize_text(text: str) -> str:
    """Summarize into 200–300 words (abstract style)."""
    prompt = f"""
    Summarize the following Human Resources and People Analytics content into 200–300 words, suitable as an abstract:
    {text[:4000]}
    """
    try:
        return _call_gemini_with_retry(prompt)
    except Exception as e:
        print(f"❌ Summarization failed after retries: {e}")
        return f"Error: Could not summarize text due to API issues. {e}"


def structured_extract(text: str) -> dict:
    """Extract title, authors, abstract, tags in JSON format"""
    prompt = f"""
    You are an Human Resources and People Analytics  research assistant.
    Return ONLY valid JSON with this structure:
    {{
      "title": "...",
      "authors": ["author1", "author2"],
      "abstract": "...",
      "tags": ["keyword1", "keyword2"]
    }}

    Journal text:
    {text[:4000]}
    """
    try:
        raw = _call_gemini_with_retry(prompt)
        
        # Try JSON parse
        try:
            print("DEBUG RAW GEMINI:", raw[:200])
            return json.loads(raw)
        except json.JSONDecodeError:
            pass # Fallback to regex if direct parsing fails

        # Try regex extraction from markdown code block
        match = re.search(r"```json\s*(\{.*?\})\s*```", raw, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
        
        # Try regex on raw string as last resort
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass

    except Exception as e:
        print(f"❌ Structured extract failed after retries: {e}")

    # Fallback if all parsing fails
    return {"title": "Untitled", "authors": [], "abstract": "", "tags": ["HR"]}


def generate_embedding(text: str) -> list:
    """Generate embedding vector using Vertex AI embedding model."""
    if not text.strip():
        return []
    try:
        response = embedding_model.get_embeddings([text])
        return response[0].values
    except Exception as e:
        print(f"❌ Embedding generation failed: {e}")
        return []

def generate_freeform(prompt: str) -> str:
    """
    Generate a free-form response from Vertex AI Gemini with retry logic.
    """
    try:
        return _call_gemini_with_retry(prompt)
    except Exception as e:
        print(f"❌ Gemini freeform failed after retries: {e}")
        # Return a user-friendly error message that can be displayed in the UI
        return f"❌ Gemini freeform failed: {e}. Please try again later. Refer to https://cloud.google.com/vertex-ai/generative-ai/docs/error-code-429 for more details."

    
def generate_freeform_streaming(prompt: str):
    """

    Stream tokens from Gemini 2.5 Flash Lite as they are generated.
    Note: Retry logic is more complex for streaming and not implemented here.
    """
    try:
        stream = gemini_model.generate_content(prompt, stream=True)
        for chunk in stream:
            if chunk.text:
                yield chunk.text
    except Exception as e:
        yield f"❌ Streaming failed: {e}"
        



def _heuristic_classify(text: str, domain: str = "general") -> Tuple[str, float, str, dict]:
    """
    Simple fallback: keyword-based sentiment with confidence heuristic.
    Returns (label, confidence, explanation, domain_fields).
    """
    # t = text.lower()


    # score = 0
    # for w in pos_words:
    #     if w in t:
    #         score += 1
    # for w in neg_words:
    #     if w in t:
    #         score -= 1
    # # out_of_scope detection
    # if any(k in t for k in ("cricket","movie","concert","vacation","party","football","hike")):
    #     return ("out_of_scope", 0.85, "Detected non-work/out-of-scope content", {})
    # if score > 0:
    #     conf = min(0.6 + 0.1*score, 0.95)
    #     return ("positive", conf, f"Contains positive tokens (score {score})", {})
    # elif score < 0:
    #     conf = min(0.6 + 0.1*(-score), 0.95)
    #     return ("negative", conf, f"Contains negative tokens (score {score})", {})
    # else:
    #     return ("neutral", 0.55, "Neutral or ambiguous text", {})
    t = text.lower()
    pos_hit = any(w in t for w in POSITIVE_WORDS)
    neg_hit = any(w in t for w in NEGATIVE_WORDS)
    scores = analyzer.polarity_scores(text)
    comp = scores["compound"]

    if pos_hit and not neg_hit:
        label, conf = "positive", max(comp, 0.8)
        reason = "Positive keywords and sentiment detected"
    elif neg_hit and not pos_hit:
        label, conf = "negative", max(abs(comp), 0.8)
        reason = "Negative keywords and sentiment detected"
    else:
        # fallback purely on VADER
        if comp >= 0.3:
            label, conf = "positive", comp
        elif comp <= -0.3:
            label, conf = "negative", abs(comp)
        else:
            label, conf = "neutral", 0.55
        reason = f"VADER compound={comp}"
    return label, conf, reason, {}    
    

def classify_texts_with_vertex(texts: List[str], domain: str = "general", batch_size:int=32) -> List[Tuple[str,float,str,dict]]:
    """
    Returns list of tuples (label, confidence, explanation, domain_fields)
    Uses Gemini 2.5 Flash Lite with SENTIMENT_PROMPTS if Vertex model is not configured.
    """
    out = []
    # 1️⃣ Try Vertex classification endpoint if enabled
    if _HAS_VERTEX and os.environ.get("USE_VERTEX","false").lower() == "true":
        model_name = os.environ.get("VERTEX_CLASSIFIER_NAME")
        if not model_name:
            # fallback to heuristics if no model configured
            for t in texts:
                out.append(_heuristic_classify(t, domain))
            return out

        client = aiplatform.gapic.PredictionServiceClient()
        endpoint = model_name
        for t in texts:
            try:
                response = client.predict(endpoint=endpoint, instances=[{"content": t}])
                pred = response.predictions[0]
                label = pred.get("label", "neutral")
                conf = float(pred.get("confidence", 0.75))
                reason = pred.get("explanation", "")
                domain_fields = pred.get("meta", {})
                out.append((label, conf, reason, domain_fields))
            except Exception as e:
                print("Vertex classify fallback:", e)
                out.append(_heuristic_classify(t, domain))
        return out

    # 2️⃣ If Vertex classification model not configured, use Gemini + domain prompt
    prompt_template = SENTIMENT_PROMPTS.get(domain, SENTIMENT_PROMPTS.get("exit_feedback"))
    for t in texts:
        try:
            filled_prompt = prompt_template.format(text=t[:2000])
            raw = gemini_model.generate_content(filled_prompt).text
            # Try to parse JSON
            try:
                #parsed = json.loads(raw)
                parsed = _parse_model_json(raw)
                if parsed:
                    label = parsed.get("label", "neutral")
                    conf = float(parsed.get("confidence", 0.7))
                    reason = parsed.get("reason", "")
                    domain_fields = {k:v for k,v in parsed.items() if k not in ("label","confidence","reason")}
                    out.append((label, conf, reason, domain_fields))
                else:
                    # fallback to heuristic if parse fails
                    out.append(_heuristic_classify(t, domain))
                label = parsed.get("label", "neutral")
                conf = float(parsed.get("confidence", 0.7))
                reason = parsed.get("reason", "")
                domain_fields = {k:v for k,v in parsed.items() if k not in ["label","confidence","reason"]}
                out.append((label, conf, reason, domain_fields))
            except Exception:
                # Fallback to heuristic if parse fails
                out.append(_heuristic_classify(t, domain))
        except Exception as e:
            print("Gemini classify fallback:", e)
            out.append(_heuristic_classify(t, domain))
    return out

def _parse_model_json(raw_text: str):
    """
    Robustly try to extract JSON from model raw output.
    Returns a dict on success or None on failure.
    """
    if not raw_text:
        return None
    # 1) Try direct parse
    try:
        #print("DEBUG RAW GEMINI:", raw_text[:200])
        return json.loads(raw_text)
    except Exception:
        pass
    # 2) Attempt to find a JSON object substring: {...}
    try:
        m = re.search(r"\{.*\}", raw_text, flags=re.DOTALL)
        if m:
            candidate = m.group(0)
            return json.loads(candidate)
    except Exception:
        pass
    # 3) Try a simple key/value extraction for label & confidence
    try:
        # attempt to find "label": "xxx"
        label_m = re.search(r'"?label"?\s*[:=]\s*["\']?([a-zA-Z0-9_ -]+)["\']?', raw_text, flags=re.IGNORECASE)
        conf_m = re.search(r'"?confidence"?\s*[:=]\s*([0-9]*\.?[0-9]+)', raw_text, flags=re.IGNORECASE)
        reason_m = re.search(r'"?reason"?\s*[:=]\s*["\']([^"\']{1,400})["\']', raw_text, flags=re.IGNORECASE)
        result = {}
        if label_m:
            result["label"] = label_m.group(1).strip()
        if conf_m:
            try:
                result["confidence"] = float(conf_m.group(1))
            except Exception:
                result["confidence"] = 0.0
        if reason_m:
            result["reason"] = reason_m.group(1).strip()
        if result:
            return result
    except Exception:
        pass
    return None
