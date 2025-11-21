import json
import re
import time
import random
import vertexai
from vertexai.generative_models import GenerativeModel
import traceback
from vertexai.language_models import TextEmbeddingModel
import config
import sys, os
from typing import List, Tuple, Dict, Any
import uuid


sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from utils.prompts import SENTIMENT_PROMPTS

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
analyzer = SentimentIntensityAnalyzer()

POSITIVE_WORDS = [
    "good", "great", "excellent", "amazing", "supportive", "helpful", "positive", "friendly",
    "encouraging", "motivated", "productive", "valued", "appreciated", "collaborative", "flexible",
    "fair", "empowered", "transparent", "inclusive", "growth", "learned", "improved", "rewarding",
    "beneficial", "fantastic", "engaging", "enjoyable", "strong", "efficient", "clear", "trustworthy",
    "constructive", "valuable", "adaptive", "respected", "innovative", "commendable", "uplifting"
]

NEGATIVE_WORDS = [
    "bad", "poor", "unfair", "stressful", "toxic", "negative", "inefficient", "confusing",
    "frustrating", "unclear", "demotivating", "overworked", "disorganized", "micromanaged",
    "biased", "underpaid", "unrecognized", "slow", "unresponsive", "inflexible", "unhelpful",
    "pressured", "ignored", "hostile", "critical", "excessive", "burnout", "lack", "problem",
    "delay", "complaint", "rejected", "failed", "unavailable", "incomplete", "untrained", "unhappy"
]

from typing import List, Tuple, Dict

# Import Vertex libs only if available
try:
    from google.cloud import aiplatform
    _HAS_VERTEX = True
except Exception:
    _HAS_VERTEX = False

# Init Vertex AI
project = config.PROJECT_ID
location = config.LOCATION
vertexai.init(project=project, location=location)

# Load Gemini
gemini_model = GenerativeModel("gemini-2.5-flash-lite")

# Load Embedding model
embedding_model = TextEmbeddingModel.from_pretrained("text-embedding-004")


def _call_gemini_with_retry(prompt: str, temperature: float = 0.1, retries: int = 3):
    """Internal helper to call Gemini API with exponential backoff for quota errors."""
    for attempt in range(retries):
        try:
            response = gemini_model.generate_content(
                prompt,
                generation_config={
                    "temperature": temperature,
                    "top_p": 0.8,
                    "top_k": 40,
                    "candidate_count": 1
                }
            )
            text = response.text.strip()
            
            # ✅ ADD: Check if response is empty
            if not text:
                print("⚠️ Gemini returned empty response")
                return "Unable to generate insight at this time. Please try again."
            
            return text
            
        except Exception as e:
            if "429" in str(e) and attempt < retries - 1:
                sleep_time = (2 ** attempt) + random.random()
                print(f"⚠️ Quota hit (429). Retrying in {sleep_time:.1f}s...")
                time.sleep(sleep_time)
            else:
                print(f"❌ Gemini API error: {e}")
                raise e
    
    # ✅ FIX: Don't return empty string, return error message
    return "Unable to generate insight after multiple retries. Service may be temporarily unavailable."

#  new

# vertex_ai_utils.py
# import time
# import random
# import json
# import re
# from typing import Optional, Any

# # --- Robust Gemini caller ---------------------------------------------------
# def _call_gemini_with_retry(
#     call_fn,                # callable that executes the actual API call: call_fn(prompt) -> raw_text
#     prompt: str,
#     retries: int = 6,
#     initial_delay: float = 1.0,
#     max_delay: float = 30.0,
#     treat_empty_as_retry: bool = True,
#     log_fn=print
# ) -> str:
#     """
#     Robust wrapper around a Gemini/Vertex call.
#     - call_fn is a callable that accepts the prompt and returns a raw text string (not parsed).
#     - Implements exponential backoff with jitter, special handling for 429/quota and empty responses.
#     Returns raw string on success. Raises exception on final failure.
#     """
#     for attempt in range(1, retries + 1):
#         try:
#             raw = call_fn(prompt)  # expected to return str
#             raw_text = (raw or "").strip()
#             if raw_text:
#                 return raw_text

#             # empty response handling
#             if not raw_text:
#                 if treat_empty_as_retry and attempt < retries:
#                     sleep_time = min(max_delay, initial_delay * (2 ** (attempt - 1)) + random.random())
#                     log_fn(f"⚠️ Empty response (attempt {attempt}/{retries}). Retrying in {sleep_time:.1f}s...")
#                     time.sleep(sleep_time)
#                     continue
#                 else:
#                     raise RuntimeError("Gemini returned empty response after retries.")

#         except Exception as e:
#             err_str = str(e)
#             # 429 / rate limit detection heuristics
#             is_rate_limit = ("429" in err_str) or ("rate limit" in err_str.lower()) or ("quota" in err_str.lower())

#             if is_rate_limit:
#                 if attempt < retries:
#                     # larger backoff on rate limit with jitter
#                     sleep_time = min(max_delay, initial_delay * (2 ** (attempt - 1)) * 1.5 + random.random() * 3)
#                     log_fn(f"⚠️ Rate limit detected (attempt {attempt}/{retries}). Backing off {sleep_time:.1f}s...")
#                     time.sleep(sleep_time)
#                     continue
#                 else:
#                     # final attempt exhausted
#                     raise

#             # other transient errors: allow retry
#             if attempt < retries:
#                 sleep_time = min(max_delay, initial_delay * (2 ** (attempt - 1)) + random.random() * 2)
#                 log_fn(f"⚠️ Gemini call failed ({e}). Retrying in {sleep_time:.1f}s (attempt {attempt}/{retries})...")
#                 time.sleep(sleep_time)
#                 continue

#             # final failure
#             raise

# # --- JSON extraction helper -------------------------------------------------
# def parse_json_from_raw(raw: str) -> Optional[Any]:
#     """
#     Attempts several strategies to extract/parse JSON from raw LLM text.
#     Returns parsed object on success, or None if no parseable JSON found.
#     Strategies:
#       1) Direct json.loads(raw)
#       2) Extract a ```json ... ``` code block and parse
#       3) Extract the first {...} substring (simple greedy) and parse
#     """
#     if not raw:
#         return None

#     s = raw.strip()

#     # 1) direct JSON
#     try:
#         return json.loads(s)
#     except Exception:
#         pass

#     # 2) ```json code block
#     m = re.search(r"```json\s*(\{.*?\})\s*```", s, re.DOTALL | re.IGNORECASE)
#     if m:
#         cand = m.group(1)
#         try:
#             return json.loads(cand)
#         except Exception:
#             pass

#     # 3) first top-level {...} block (simple greedy match)
#     #    This is not perfect for nested braces but works well for typical LLM JSON outputs.
#     m2 = re.search(r"(\{(?:[^{}]|\n)*\})", s, re.DOTALL)
#     if m2:
#         cand = m2.group(1)
#         try:
#             return json.loads(cand)
#         except Exception:
#             pass

#     # 4) try to find multiple lines forming a JSON-like block (fallback)
#     #    e.g., rid of surrounding markdown and parse inner braces.
#     # Remove surrounding markdown fences and try again
#     stripped = re.sub(r"^```.*?$", "", s, flags=re.MULTILINE).strip()
#     try:
#         return json.loads(stripped)
#     except Exception:
#         pass

#     return None


def summarize_text(text: str) -> str:
    """Summarize into 200–300 words (abstract style)."""
    prompt = f"""
    Summarize the following Human Resources and People Analytics content into 200–300 words, suitable as an abstract:
    {text[:4000]}
    """
    try:
        # Use higher temperature (0.4) for creative summarization
        return _call_gemini_with_retry(prompt, temperature=0.4)
    except Exception as e:
        print(f"❌ Summarization failed after retries: {e}")
        return f"Error: Could not summarize text due to API issues. {e}"


def structured_extract(text: str) -> dict:
    """Extract title, authors, abstract, tags in JSON format"""
    prompt = f"""
    You are an Human Resources and People Analytics research assistant.
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
        # Use lower temperature (0.1) for structured extraction
        raw = _call_gemini_with_retry(prompt, temperature=0.1)
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass

        match = re.search(r"```json\s*(\{.*?\})\s*```", raw, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
        
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass

    except Exception as e:
        print(f"❌ Structured extract failed after retries: {e}")

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


def generate_freeform(prompt: str, temperature: float = 0.4) -> str:
    """
    Generate a free-form response from Vertex AI Gemini with retry logic.
    Default to higher temperature (0.4) for creative responses.
    
    Args:
        prompt: The prompt to send to Gemini
        temperature: Controls randomness (0.0 = focused, 1.0 = creative)
    """
    try:
        return _call_gemini_with_retry(prompt, temperature=temperature)
    except Exception as e:
        print(f"❌ Gemini freeform failed after retries: {e}")
        return f"❌ Gemini freeform failed: {e}. Please try again later."

    
def generate_freeform_streaming(prompt: str, temperature: float = 0.4):
    """
    Stream tokens from Gemini 2.5 Flash Lite as they are generated.
    Default to higher temperature (0.4) for creative responses.
    
    Args:
        prompt: The prompt to send to Gemini
        temperature: Controls randomness (0.0 = focused, 1.0 = creative)
    """
    try:
        stream = gemini_model.generate_content(
            prompt,
            generation_config={
                "temperature": temperature,
                "top_p": 0.8,
                "top_k": 40,
                "candidate_count": 1
            },
            stream=True
        )
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
        if comp >= 0.3:
            label, conf = "positive", comp
        elif comp <= -0.3:
            label, conf = "negative", abs(comp)
        else:
            label, conf = "neutral", 0.55
        reason = f"VADER compound={comp}"
    return label, conf, reason, {}


def _parse_model_json(raw_text: str):
    """
    Robustly try to extract JSON from model raw output.
    Returns a dict on success or None on failure.
    """
    if not raw_text:
        print("DEBUG_PARSE: Empty raw_text received")
        return None
    
    # Strip whitespace
    raw_text = raw_text.strip()
    
    # 1) Try direct JSON parse
    try:
        result = json.loads(raw_text)
        print(f"DEBUG_PARSE: Direct JSON parse SUCCESS")
        return result
    except json.JSONDecodeError as e:
        print(f"DEBUG_PARSE: Direct parse failed: {e}")
    
    # 2) Try extracting from markdown code blocks (```json ... ```)
    try:
        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw_text, re.DOTALL | re.IGNORECASE)
        if match:
            candidate = match.group(1).strip()
            result = json.loads(candidate)
            print(f"DEBUG_PARSE: Markdown block parse SUCCESS")
            return result
    except (json.JSONDecodeError, AttributeError) as e:
        print(f"DEBUG_PARSE: Markdown block parse failed: {e}")
    
    # 3) Try finding JSON object anywhere in text
    try:
        match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', raw_text, re.DOTALL)
        if match:
            candidate = match.group(0).strip()
            result = json.loads(candidate)
            print(f"DEBUG_PARSE: Nested JSON extraction SUCCESS")
            return result
    except (json.JSONDecodeError, AttributeError) as e:
        print(f"DEBUG_PARSE: Nested JSON extraction failed: {e}")
    
    # 4) Try line-by-line key extraction (most robust fallback)
    try:
        result = {}
        
        # Extract label
        label_patterns = [
            r'"label"\s*:\s*"([^"]+)"',
            r"'label'\s*:\s*'([^']+)'",
            r'label\s*[:=]\s*"([^"]+)"',
            r'label\s*[:=]\s*([a-zA-Z_]+)',
        ]
        for pattern in label_patterns:
            match = re.search(pattern, raw_text, re.IGNORECASE)
            if match:
                result["label"] = match.group(1).strip().lower()
                break
        
        # Extract confidence
        conf_patterns = [
            r'"confidence"\s*:\s*([0-9]*\.?[0-9]+)',
            r"'confidence'\s*:\s*([0-9]*\.?[0-9]+)",
            r'confidence\s*[:=]\s*([0-9]*\.?[0-9]+)',
        ]
        for pattern in conf_patterns:
            match = re.search(pattern, raw_text, re.IGNORECASE)
            if match:
                try:
                    result["confidence"] = float(match.group(1))
                    break
                except ValueError:
                    pass
        
        # Extract reason/explanation
        reason_patterns = [
            r'"(?:reason|explanation)"\s*:\s*"([^"]+)"',
            r"'(?:reason|explanation)'\s*:\s*'([^']+)'",
            r'(?:reason|explanation)\s*[:=]\s*"([^"]+)"',
        ]
        for pattern in reason_patterns:
            match = re.search(pattern, raw_text, re.IGNORECASE)
            if match:
                result["reason"] = match.group(1).strip()
                break
        
        if result and "label" in result:
            print(f"DEBUG_PARSE: Key extraction SUCCESS: {result}")
            return result
        else:
            print(f"DEBUG_PARSE: Key extraction found partial data: {result}")
            
    except Exception as e:
        print(f"DEBUG_PARSE: Key extraction failed: {e}")
    
    print(f"DEBUG_PARSE: All parsing methods FAILED for text: {raw_text[:200]}")
    return None


def classify_texts_with_vertex(texts: List[str], domain: str = "general", batch_size: int = 32) -> List[Tuple[str, float, str, dict]]:
    """
    Returns list of tuples (label, confidence, explanation, domain_fields)
    Uses Gemini 2.5 Flash Lite with SENTIMENT_PROMPTS if Vertex model is not configured.
    """
    out = []
    
    # 1️⃣ Try Vertex classification endpoint if enabled
    if _HAS_VERTEX and os.environ.get("USE_VERTEX", "false").lower() == "true":
        model_name = os.environ.get("VERTEX_CLASSIFIER_NAME")
        if not model_name:
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
                print(f"Vertex classify fallback for text: {e}")
                out.append(_heuristic_classify(t, domain))
        return out

    # 2️⃣ Use Gemini + domain prompt
    prompt_template = SENTIMENT_PROMPTS.get(domain, SENTIMENT_PROMPTS.get("exit_feedback", SENTIMENT_PROMPTS.get("general", "")))
    
    if not prompt_template:
        print(f"⚠️ No prompt template found for domain '{domain}', using heuristic")
        for t in texts:
            out.append(_heuristic_classify(t, domain))
        return out
    
    for i, t in enumerate(texts):
        try:
            # Truncate long texts
            text_snippet = t[:2000] if len(t) > 2000 else t
            filled_prompt = prompt_template.format(text=text_snippet)
            
            print(f"DEBUG_CLASSIFY: Processing text {i+1}/{len(texts)}")
            
            # Call Gemini
            raw = gemini_model.generate_content(filled_prompt).text
            
            # Parse response
            parsed = _parse_model_json(raw)
            
            if parsed and "label" in parsed:
                label = parsed.get("label", "neutral").lower()
                # Normalize label
                if label not in ["positive", "negative", "neutral"]:
                    print(f"⚠️ Invalid label '{label}', defaulting to neutral")
                    label = "neutral"
                    
                conf = float(parsed.get("confidence", 0.7))
                # Clamp confidence to [0, 1]
                conf = max(0.0, min(1.0, conf))
                
                reason = parsed.get("reason", "AI classification")
                domain_fields = {k: v for k, v in parsed.items() if k not in ("label", "confidence", "reason")}
                
                out.append((label, conf, reason, domain_fields))
                print(f"✅ Successfully classified text {i+1}: {label} (conf={conf:.2f})")
            else:
                print(f"⚠️ Gemini parsing failed for text {i+1}, using heuristic fallback")
                out.append(_heuristic_classify(t, domain))
                
        except Exception as e:
            print(f"❌ Gemini classify exception for text {i+1}: {e}")
            traceback.print_exc()
            out.append(_heuristic_classify(t, domain))
    
    return out

def classify_texts_with_rate_limit_handling(
    texts: List[str], 
    domain: str = "general", 
    batch_size: int = 10,
    delay_between_batches: float = 2.0,
    max_retries_per_text: int = 5
) -> List[Tuple[str, float, str, dict]]:
    """
    Enhanced classifier with aggressive rate limit handling.
    
    Features:
    - Batch processing with delays
    - Exponential backoff on 429 errors
    - Automatic fallback to heuristic classification
    - Progress tracking
    
    Args:
        texts: List of texts to classify
        domain: Feedback domain
        batch_size: Number of texts per batch (reduce if hitting limits)
        delay_between_batches: Seconds to wait between batches
        max_retries_per_text: Max retry attempts per text before fallback
    """
    
    import sys
    import os
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    
    from utils import vertex_ai_utils
    from utils.prompts import SENTIMENT_PROMPTS
    
    results = []
    total_texts = len(texts)
    
    print(f"\n🔄 Starting batch classification of {total_texts} texts")
    print(f"   Batch size: {batch_size}")
    print(f"   Delay between batches: {delay_between_batches}s")
    
    # Process in batches
    for batch_idx in range(0, total_texts, batch_size):
        batch_texts = texts[batch_idx:batch_idx + batch_size]
        batch_num = (batch_idx // batch_size) + 1
        total_batches = (total_texts + batch_size - 1) // batch_size
        
        print(f"\n📦 Processing batch {batch_num}/{total_batches} ({len(batch_texts)} texts)...")
        
        for local_idx, text in enumerate(batch_texts):
            global_idx = batch_idx + local_idx + 1
            print(f"   [{global_idx}/{total_texts}] Classifying...", end=" ")
            
            success = False
            last_error = None
            
            # Retry loop for this specific text
            for attempt in range(max_retries_per_text):
                try:
                    # Call Gemini with the text
                    prompt_template = SENTIMENT_PROMPTS.get(domain, SENTIMENT_PROMPTS.get("general", ""))
                    if not prompt_template:
                        print("❌ No prompt template, using heuristic")
                        result = vertex_ai_utils._heuristic_classify(text, domain)
                        results.append(result)
                        success = True
                        break
                    
                    filled_prompt = prompt_template.format(text=text[:2000])
                    
                    # Generate with Gemini
                    raw = vertex_ai_utils.gemini_model.generate_content(
                        filled_prompt,
                        generation_config={"temperature": 0.1}
                    ).text
                    
                    # Parse response
                    parsed = vertex_ai_utils._parse_model_json(raw)
                    
                    if parsed and "label" in parsed:
                        label = parsed.get("label", "neutral").lower()
                        if label not in ["positive", "negative", "neutral"]:
                            label = "neutral"
                        
                        conf = float(parsed.get("confidence", 0.7))
                        conf = max(0.0, min(1.0, conf))
                        
                        reason = parsed.get("reason", "AI classification")
                        domain_fields = {k: v for k, v in parsed.items() if k not in ("label", "confidence", "reason")}
                        
                        results.append((label, conf, reason, domain_fields))
                        print(f"✅ {label}")
                        success = True
                        break
                    else:
                        print(f"⚠️ Parse failed (attempt {attempt+1})", end=" ")
                        last_error = "Parse failure"
                
                except Exception as e:
                    error_str = str(e)
                    
                    # Check if it's a 429 rate limit error
                    if "429" in error_str or "Resource exhausted" in error_str:
                        # Exponential backoff: 2^attempt + jitter
                        wait_time = (2 ** attempt) + random.uniform(0, 2)
                        print(f"⏳ 429 (retry {attempt+1}/{max_retries_per_text}, wait {wait_time:.1f}s)", end=" ")
                        time.sleep(wait_time)
                        last_error = "429 Rate Limit"
                    else:
                        print(f"❌ Error: {error_str[:50]}")
                        last_error = error_str
                        break  # Non-429 errors, don't retry
            
            # If all retries failed, use heuristic fallback
            if not success:
                print(f"🔄 Using heuristic fallback (reason: {last_error})")
                result = vertex_ai_utils._heuristic_classify(text, domain)
                results.append(result)
        
        # Delay between batches (except for last batch)
        if batch_idx + batch_size < total_texts:
            print(f"⏸️  Waiting {delay_between_batches}s before next batch...")
            time.sleep(delay_between_batches)
    
    print(f"\n✅ Completed classification of {len(results)}/{total_texts} texts")
    
    # Count how many used heuristic vs AI
    ai_classified = sum(1 for r in results if isinstance(r, tuple) and len(r) == 4)
    heuristic_classified = len(results) - ai_classified
    print(f"   AI classified: {ai_classified}")
    print(f"   Heuristic fallback: {heuristic_classified}")
    
    return results


# ============================================================================
# SOLUTION 3: Update sentiment_processing.py to use batching
# ============================================================================

# Replace this section in your sentiment_processing.py:

# BEFORE (line ~670):
# for row_idx, r in enumerate(rows, 1):
#     ...
#     label, conf, reason, domain_fields = vertex_ai_utils.classify_texts_with_vertex([redacted_text], domain=domain)[0]
#     ...

# AFTER:
# def process_feedback_batch(rows, domain, include_full_text):
#     """
#     Process a batch of feedback rows with rate limit handling.
#     Returns list of detail dicts.
#     """
#     details = []
    
#     # Extract texts for batch classification
#     texts_to_classify = []
#     row_metadata = []
    
#     for row_idx, r in enumerate(rows, 1):
#         candidate_id = r.get("candidate_id")
#         candidate_name = r.get("candidate_name")
#         text_id = r.get("row_index") or str(uuid.uuid4())
#         question_id = r.get("question_id") or ""
#         question_text = r.get("question_text", "")
#         response_text = r.get("response_text", "")
        
#         redacted_text, flags = _sanitize_text(response_text, include_full_text=include_full_text)
        
#         texts_to_classify.append(redacted_text)
#         row_metadata.append({
#             "candidate_id": candidate_id,
#             "candidate_name": candidate_name,
#             "text_id": text_id,
#             "question_id": question_id,
#             "question_text": question_text,
#             "redacted_text": redacted_text
#         })
    
#     # Batch classify with rate limit handling
#     print(f"\n🚀 Batch classifying {len(texts_to_classify)} feedback items...")
#     classifications = classify_texts_with_rate_limit_handling(
#         texts_to_classify, 
#         domain=domain,
#         batch_size=5,  # Small batches to avoid rate limits
#         delay_between_batches=3.0  # 3 second delay between batches
#     )
    
#     # Combine classifications with metadata
#     for metadata, (label, conf, reason, domain_fields) in zip(row_metadata, classifications):
#         details.append({
#             "candidate_id": metadata["candidate_id"],
#             "candidate_name": metadata["candidate_name"],
#             "text_id": str(metadata["text_id"]),
#             "question_id": metadata["question_id"],
#             "question_text": metadata["question_text"],
#             "text_snippet": metadata["redacted_text"][:400],
#             "label": label,
#             "confidence": float(conf)
#         })
    
#     return details

def _sanitize_text_local(text: str, include_full_text: bool = False):
    """
    Local version of sanitize_text for vertex_ai_utils.
    Redacts emails and optionally truncates.
    """
    try:
        # Simple email redaction
        red = re.sub(r'[\w\.-]+@[\w\.-]+', '[email_redacted]', text)
        
        if include_full_text:
            return text, {}
        else:
            return (red[:400], {})
    except Exception:
        if include_full_text:
            return text, {}
        return (text[:400], {})


def process_feedback_batch(rows, domain, include_full_text):
    """
    Process a batch of feedback rows with rate limit handling.
    Returns list of detail dicts.
    
    Args:
        rows: List of feedback row dicts from extract_candidate_feedback_rows()
        domain: Feedback domain (e.g., 'exit_feedback')
        include_full_text: Whether to include full text or truncate
    
    Returns:
        List of detail dicts with candidate_id, question_id, label, confidence, etc.
    """
    details = []
    
    # Extract texts for batch classification
    texts_to_classify = []
    row_metadata = []
    
    print(f"   Preparing {len(rows)} rows for batch classification...")
    
    for row_idx, r in enumerate(rows, 1):
        candidate_id = r.get("candidate_id", "unknown")
        candidate_name = r.get("candidate_name", "Unknown")
        text_id = r.get("row_index", str(uuid.uuid4()))
        question_id = r.get("question_id", "")
        question_text = r.get("question_text", "")
        response_text = r.get("response_text", "")
        
        # Sanitize text
        redacted_text, flags = _sanitize_text_local(response_text, include_full_text=include_full_text)
        
        texts_to_classify.append(redacted_text)
        row_metadata.append({
            "candidate_id": candidate_id,
            "candidate_name": candidate_name,
            "text_id": text_id,
            "question_id": question_id,
            "question_text": question_text,
            "redacted_text": redacted_text
        })
    
    # Batch classify with rate limit handling
    print(f"\n🚀 Batch classifying {len(texts_to_classify)} feedback items...")
    classifications = classify_texts_with_rate_limit_handling(
        texts_to_classify, 
        domain=domain,
        batch_size=5,  # Small batches to avoid rate limits
        delay_between_batches=3.0  # 3 second delay between batches
    )
    
    # Combine classifications with metadata
    for metadata, (label, conf, reason, domain_fields) in zip(row_metadata, classifications):
        details.append({
            "candidate_id": metadata["candidate_id"],
            "candidate_name": metadata["candidate_name"],
            "text_id": str(metadata["text_id"]),
            "question_id": metadata["question_id"],
            "question_text": metadata["question_text"],
            "text_snippet": metadata["redacted_text"][:400],
            "label": label,
            "confidence": float(conf)
        })
    
    print(f"✅ Batch classification complete: {len(details)} items processed")
    
    return details


# ==================== LinkedIn Scout Functions ====================

def analyze_linkedin_candidate(profile_data: Dict, job_description: str) -> Dict[str, Any]:
    """
    Analyze a LinkedIn profile against a job description using Gemini
    
    Args:
        profile_data: Dictionary with LinkedIn profile data (from scraperapi_linkedin_client)
        job_description: Full text of the job description
        
    Returns:
        Dictionary with:
            - match_score (0-100)
            - skills_score (0-100)
            - experience_score (0-100)
            - education_score (0-100)
            - key_strengths: str
            - gaps: str
            - recommendation: str
            - match_reasoning: str
            - job_hopping_risk: Optional[str]
            - job_hopping_detail: Optional[str]
    """
    
    # Build profile summary for analysis
    profile_summary = f"""
CANDIDATE PROFILE:
Name: {profile_data.get('name', 'Unknown')}
Headline: {profile_data.get('headline', 'N/A')}
Location: {profile_data.get('location', 'N/A')}

ABOUT:
{profile_data.get('about', 'Not provided')}

EXPERIENCE:
"""
    
    for idx, exp in enumerate(profile_data.get('experience', [])[:5], 1):
        profile_summary += f"\n{idx}. {exp.get('title', 'N/A')} at {exp.get('company', 'N/A')}"
        if exp.get('description'):
            profile_summary += f"\n   {exp['description'][:300]}"
    
    profile_summary += "\n\nEDUCATION:\n"
    for idx, edu in enumerate(profile_data.get('education', [])[:3], 1):
        profile_summary += f"{idx}. {edu.get('school', 'N/A')} - {edu.get('degree', 'N/A')}\n"
    
    profile_summary += f"\n\nSKILLS:\n{', '.join(profile_data.get('skills', [])[:20])}"
    
    # Create comprehensive analysis prompt
    analysis_prompt = f"""You are an expert HR recruiter analyzing candidate profiles against job requirements.

JOB DESCRIPTION:
{job_description}

{profile_summary}

Analyze this candidate's fit for the role and provide:

1. MATCH SCORES (0-100):
   - Overall Match Score
   - Skills Match Score
   - Experience Match Score  
   - Education Match Score

2. KEY STRENGTHS: List 3-5 specific strengths that make this candidate a good fit

3. SKILL/EXPERIENCE GAPS: List 2-4 areas where the candidate may not fully meet requirements

4. RECOMMENDATION: Brief hiring recommendation (Highly Recommended / Recommended / Consider / Not Recommended)

5. DETAILED ANALYSIS: 2-3 paragraph detailed assessment

Format your response as JSON:
{{
  "match_score": <number 0-100>,
  "skills_score": <number 0-100>,
  "experience_score": <number 0-100>,
  "education_score": <number 0-100>,
  "key_strengths": "<concise comma-separated list>",
  "gaps": "<concise comma-separated list>",
  "recommendation": "<Highly Recommended | Recommended | Consider | Not Recommended>",
  "match_reasoning": "<2-3 paragraph detailed assessment>",
  "job_hopping_risk": "<Low | Medium | High>",
  "job_hopping_detail": "<explanation of job stability assessment>"
}}"""

    try:
        response_text = _call_gemini_with_retry(analysis_prompt, temperature=0.2)
        
        # Parse JSON response
        # Remove markdown code blocks if present
        response_text = response_text.strip()
        if response_text.startswith('```json'):
            response_text = response_text[7:]
        if response_text.startswith('```'):
            response_text = response_text[3:]
        if response_text.endswith('```'):
            response_text = response_text[:-3]
        response_text = response_text.strip()
        
        analysis_result = json.loads(response_text)
        
        return analysis_result
        
    except json.JSONDecodeError as e:
        print(f"❌ Failed to parse Gemini JSON response: {e}")
        print(f"Raw response: {response_text[:500]}")
        
        # Return default structure on error
        return {
            "match_score": 50,
            "skills_score": 50,
            "experience_score": 50,
            "education_score": 50,
            "key_strengths": "Unable to analyze - parsing error",
            "gaps": "Analysis incomplete",
            "recommendation": "Manual Review Required",
            "match_reasoning": f"Error analyzing candidate. Raw response: {response_text[:200]}",
            "job_hopping_risk": None,
            "job_hopping_detail": None
        }
    except Exception as e:
        print(f"❌ Error in LinkedIn candidate analysis: {e}")
        return {
            "match_score": 0,
            "skills_score": 0,
            "experience_score": 0,
            "education_score": 0,
            "key_strengths": "",
            "gaps": "Analysis failed",
            "recommendation": "Error",
            "match_reasoning": f"Error: {str(e)}",
            "job_hopping_risk": None,
            "job_hopping_detail": None
        }


def generate_linkedin_summary_report(
    job_title: str,
    job_description: str,
    candidates_analysis: List[Dict[str, Any]]
) -> str:
    """
    Generate a comprehensive summary report for LinkedIn scouting results
    
    Args:
        job_title: Title of the position
        job_description: Full JD text
        candidates_analysis: List of analyzed candidates with their match scores
        
    Returns:
        Markdown-formatted comprehensive report
    """
    
    # Sort candidates by match score
    sorted_candidates = sorted(
        candidates_analysis,
        key=lambda x: x.get('match_score', 0),
        reverse=True
    )
    
    # Calculate statistics
    total_candidates = len(sorted_candidates)
    avg_match_score = sum(c.get('match_score', 0) for c in sorted_candidates) / total_candidates if total_candidates > 0 else 0
    highly_recommended = sum(1 for c in sorted_candidates if c.get('recommendation') == 'Highly Recommended')
    recommended = sum(1 for c in sorted_candidates if c.get('recommendation') == 'Recommended')
    
    # Build report
    report = f"""# LinkedIn Talent Scout Report
## Position: {job_title}

### Executive Summary
- **Total Candidates Analyzed**: {total_candidates}
- **Average Match Score**: {avg_match_score:.1f}/100
- **Highly Recommended**: {highly_recommended} candidates
- **Recommended**: {recommended} candidates

---

## Top Candidates

"""
    
    # Top 10 candidates detailed breakdown
    for idx, candidate in enumerate(sorted_candidates[:10], 1):
        full_name = candidate.get('full_name', 'Unknown')
        headline = candidate.get('headline', 'N/A')
        match_score = candidate.get('match_score', 0)
        recommendation = candidate.get('recommendation', 'N/A')
        
        report += f"""### {idx}. {full_name}
**Headline**: {headline}  
**Overall Match Score**: {match_score}/100  
**Recommendation**: {recommendation}

**Match Breakdown**:
- Skills: {candidate.get('skills_score', 0)}/100
- Experience: {candidate.get('experience_score', 0)}/100
- Education: {candidate.get('education_score', 0)}/100

**Key Strengths**: {candidate.get('key_strengths', 'N/A')}

**Potential Gaps**: {candidate.get('gaps', 'N/A')}

**Analysis**: {candidate.get('match_reasoning', 'No analysis available')}

**Job Stability**: {candidate.get('job_hopping_risk', 'N/A')} Risk
{candidate.get('job_hopping_detail', '')}

"""
        report += "---\n\n"
    
    # Add remaining candidates summary
    if len(sorted_candidates) > 10:
        report += f"\n## Additional Candidates ({len(sorted_candidates) - 10} more)\n\n"
        for idx, candidate in enumerate(sorted_candidates[10:], 11):
            full_name = candidate.get('full_name', 'Unknown')
            score = candidate.get('match_score', 0)
            rec = candidate.get('recommendation', 'N/A')
            report += f"{idx}. **{full_name}** - Match: {score}/100 - {rec}\n"
    
    # Add recommendations section
    report += f"""

---

## Hiring Recommendations

### Immediate Action
The following candidates should be prioritized for interviews:
"""
    
    priority_candidates = [c for c in sorted_candidates if c.get('match_score', 0) >= 75]
    for candidate in priority_candidates[:5]:
        report += f"- **{candidate.get('full_name')}** ({candidate.get('match_score')}/100)\n"
    
    report += f"""

### Next Steps
1. Schedule initial screening calls with top {min(5, highly_recommended + recommended)} candidates
2. Prepare technical assessment based on identified gaps
3. Coordinate with hiring manager for final interviews

---

*Report generated on {time.strftime('%Y-%m-%d %H:%M:%S UTC')}*
"""
    
    return report