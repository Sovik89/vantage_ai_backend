import json
import re
import time
import random
import math
import sys, os

from typing import List, Tuple, Dict

import vertexai
from vertexai.generative_models import GenerativeModel
from vertexai.language_models import TextEmbeddingModel
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from google.cloud import bigquery

import config
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from utils.prompts import SENTIMENT_PROMPTS

# -------------------------------------------------------------------
# Initialization
# -------------------------------------------------------------------
project = config.PROJECT_ID
location = config.LOCATION
vertexai.init(project=project, location=location)
DATASET_ID = f"{config.PROJECT_ID}.{config.BQ_DATASET}"
VECTOR_TABLE_ID = f"{DATASET_ID}.journal_vectors"
client = bigquery.Client(project=config.PROJECT_ID)


gemini_model = GenerativeModel("gemini-2.5-flash-lite")
# ✅ FIXED: Changed from text-embedding-004 to text-embedding-005 for consistency
embedding_model = TextEmbeddingModel.from_pretrained("text-embedding-005")
analyzer = SentimentIntensityAnalyzer()

DATASET_ID = f"{config.PROJECT_ID}.{config.BQ_DATASET}"

# -------------------------------------------------------------------
# Extended HR keyword lexicons
# -------------------------------------------------------------------
POSITIVE_WORDS = [
    "good","great","excellent","amazing","supportive","helpful","positive","friendly",
    "encouraging","motivated","productive","valued","appreciated","collaborative","flexible",
    "fair","empowered","transparent","inclusive","growth","learned","improved","rewarding",
    "beneficial","fantastic","engaging","enjoyable","strong","efficient","clear","trustworthy",
    "constructive","valuable","adaptive","respected","innovative","commendable","uplifting",
    "acknowledged","balanced","resilient","comfortable","safe","encouraged","successful"
]

NEGATIVE_WORDS = [
    "bad","poor","unfair","stressful","toxic","negative","inefficient","confusing",
    "frustrating","unclear","demotivating","overworked","disorganized","micromanaged",
    "biased","underpaid","unrecognized","slow","unresponsive","inflexible","unhelpful",
    "pressured","ignored","hostile","critical","excessive","burnout","lack","problem",
    "delay","complaint","rejected","failed","unavailable","incomplete","untrained","unhappy",
    "overloaded","inequitable","unhealthy","unproductive","ineffective","apathetic"
]

try:
    from google.cloud import aiplatform
    _HAS_VERTEX = True
except Exception:
    _HAS_VERTEX = False


# -------------------------------------------------------------------
# Gemini helpers
# -------------------------------------------------------------------
def _call_gemini_with_retry(prompt: str, retries: int = 3):
    for attempt in range(retries):
        try:
            response = gemini_model.generate_content(
                prompt,
                generation_config={"temperature": 0.1}
            )
            return response.text.strip()
        except Exception as e:
            if "429" in str(e) and attempt < retries - 1:
                sleep_time = (2 ** attempt) + random.random()
                print(f"⚠️ Quota hit (429). Retrying in {sleep_time:.1f}s...")
                time.sleep(sleep_time)
            else:
                raise e
    return ""


# -------------------------------------------------------------------
# Core utilities
# -------------------------------------------------------------------
def summarize_text(text: str) -> str:
    prompt = f"""
    Summarize the following Human Resources and People Analytics content into 200–300 words, suitable as an abstract:
    {text[:4000]}
    """
    try:
        return _call_gemini_with_retry(prompt)
    except Exception as e:
        print(f"❌ Summarization failed: {e}")
        return f"Error: {e}"


def structured_extract(text: str) -> dict:
    prompt = f"""
    You are an HR and People Analytics assistant.
    Return ONLY valid JSON with:
    {{ "title": "...", "authors": ["..."], "abstract": "...", "tags": ["..."] }}
    Text: {text[:4000]}
    """
    try:
        raw = _call_gemini_with_retry(prompt)
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            return json.loads(match.group(0))
    except Exception as e:
        print("❌ structured_extract error:", e)
    return {"title": "Untitled", "authors": [], "abstract": "", "tags": []}


def generate_embedding(text: str) -> list:
    """
    Generate a single embedding vector for the given text.
    Returns an empty list if embedding generation fails.
    """
    if not text.strip():
        return []
    try:
        response = embedding_model.get_embeddings([text])
        embedding = response[0].values
        print(f"✓ Generated embedding with {len(embedding)} dimensions")
        return embedding
    except Exception as e:
        print(f"❌ Embedding generation failed: {e}")
        return []
    
def generate_embeddings(texts: list, retries: int = 3):
    """
    Batch generate embeddings for multiple texts (up to 250 at once).
    Returns list of vectors aligned with input order.
    """
    if not texts:
        return []

    for attempt in range(retries):
        try:
            responses = embedding_model.get_embeddings(texts)
            embeddings = [resp.values for resp in responses]
            print(f"✓ Generated {len(embeddings)} embeddings, each with {len(embeddings[0])} dimensions")
            return embeddings
        except Exception as e:
            if "429" in str(e) and attempt < retries - 1:
                sleep_time = (2 ** attempt) + random.random()
                print(f"⚠️ Quota hit (429). Retrying batch in {sleep_time:.1f}s...")
                time.sleep(sleep_time)
            else:
                raise



def generate_freeform(prompt: str) -> str:
    try:
        return _call_gemini_with_retry(prompt)
    except Exception as e:
        print(f"❌ Gemini freeform failed: {e}")
        return f"❌ Gemini freeform failed: {e}"


# -------------------------------------------------------------------
# Fallback sentiment classifier (hybrid VADER + keywords)
# -------------------------------------------------------------------
def _heuristic_classify(text: str, domain: str = "general") -> Tuple[str, float, str, dict]:
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


# -------------------------------------------------------------------
# Robust JSON parser for model output
# -------------------------------------------------------------------
def _parse_model_json(raw_text: str):
    if not raw_text:
        return None
    try:
        return json.loads(raw_text)
    except Exception:
        pass
    try:
        m = re.search(r"\{.*\}", raw_text, flags=re.DOTALL)
        if m:
            return json.loads(m.group(0))
    except Exception:
        pass
    try:
        label_m = re.search(r'"?label"?\s*[:=]\s*["\']?([a-zA-Z0-9_ -]+)["\']?', raw_text, re.IGNORECASE)
        conf_m = re.search(r'"?confidence"?\s*[:=]\s*([0-9]*\.?[0-9]+)', raw_text, re.IGNORECASE)
        reason_m = re.search(r'"?reason"?\s*[:=]\s*["\']([^"\']{1,400})["\']', raw_text, re.IGNORECASE)
        result = {}
        if label_m:
            result["label"] = label_m.group(1).strip()
        if conf_m:
            result["confidence"] = float(conf_m.group(1))
        if reason_m:
            result["reason"] = reason_m.group(1).strip()
        return result if result else None
    except Exception:
        return None


def classify_sentiment_batch(texts: List[str], domain: str = "general") -> List[Tuple[str, float, str, dict]]:
    """
    Batch classify sentiments with Gemini.
    Returns: [(label, confidence, reason, domain_fields), ...]
    """
    out = []
    domain_prompt_template = SENTIMENT_PROMPTS.get(domain, SENTIMENT_PROMPTS["general"])

    for t in texts:
        if not t.strip():
            out.append(("neutral", 0.5, "Empty text", {}))
            continue
        try:
            prompt = domain_prompt_template.format(text=t)
            response = gemini_model.generate_content(
                prompt,
                generation_config={"temperature": 0.1}
            )
            raw = response.text
            print("DEBUG_RAW_GEMINI:", raw[:500].replace("\n", "\\n"))

            parsed = _parse_model_json(raw)
            if not parsed:
                # aggressive regex fallback
                label_m = re.search(r'"?label"?\s*[:=]\s*["\']?([a-zA-Z0-9_\- ]+)["\']?', raw, re.IGNORECASE)
                conf_m = re.search(r'"?confidence"?\s*[:=]\s*([0-9]*\.?[0-9]+)', raw, re.IGNORECASE)
                reason_m = re.search(r'"?reason"?\s*[:=]\s*["\']([^"\']{1,400})["\']', raw, re.IGNORECASE)
                parsed = {}
                if label_m:
                    parsed["label"] = label_m.group(1).strip()
                if conf_m:
                    try:
                        parsed["confidence"] = float(conf_m.group(1))
                    except Exception:
                        parsed["confidence"] = 0.75
                if reason_m:
                    parsed["reason"] = reason_m.group(1).strip()

            if parsed:
                label = parsed.get("label", "neutral")
                conf = float(parsed.get("confidence", 0.7))
                reason = parsed.get("reason", "")
                domain_fields = {k: v for k, v in parsed.items() if k not in ("label", "confidence", "reason")}
                out.append((label, conf, reason, domain_fields))
            else:
                out.append(_heuristic_classify(t, domain))
        except Exception as e:
            print("Gemini classify fallback:", e)
            out.append(_heuristic_classify(t, domain))
    return out

def search_similar_papers(query: str, top_k: int = 5):
    """
    Search across ALL records in vector DB based on semantic similarity.
    """
    query_embedding = generate_embedding(query)
    if not query_embedding:
        print("❌ Failed to generate query embedding")
        return []

    # ✅ ADDED: Verify embedding dimensions
    print(f"Query embedding dimensions: {len(query_embedding)}")

    sql = f"""
    SELECT pdf_name, title, summary, source_type, file_hash,
           ML.DISTANCE(embedding, @query_embedding, 'COSINE') AS distance
    FROM `{VECTOR_TABLE_ID}`
    WHERE ARRAY_LENGTH(embedding) = @embedding_dim
    ORDER BY distance
    LIMIT {top_k}
    """

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ArrayQueryParameter("query_embedding", "FLOAT64", query_embedding),
            bigquery.ScalarQueryParameter("embedding_dim", "INT64", len(query_embedding))
        ]
    )

    try:
        rows = client.query(sql, job_config=job_config).result()
        results = [dict(row) for row in rows]
        print(f"✓ Found {len(results)} similar papers")
        return results
    except Exception as e:
        print(f"❌ Vector search failed: {e}")
        import traceback
        traceback.print_exc()
        return []

def search_similar_titles(query: str, top_k: int = 5) -> List[Dict]:
    """
    Search across titles in vector DB based on semantic similarity.
    
    Args:
        query (str): The search query text
        top_k (int): Number of most similar results to return
        
    Returns:
        list: List of dictionaries containing matched records sorted by similarity
    """
    query_embedding = generate_embedding(query)
    if not query_embedding:
        print("⚠️ Failed to generate embedding for query")
        return []

    # ✅ ADDED: Verify embedding dimensions
    print(f"Title search - Query embedding dimensions: {len(query_embedding)}")

    # Modified SQL to search specifically in titles with better distance calculation
    sql = f"""
    WITH RankedResults AS (
        SELECT 
            pdf_name,
            title,
            summary,
            source_type,
            file_hash,
            ML.DISTANCE(embedding, @query_embedding, 'COSINE') AS distance,
            ROUND(100 * (1 - ML.DISTANCE(embedding, @query_embedding, 'COSINE')), 2) AS similarity_score
        FROM `{VECTOR_TABLE_ID}`
        WHERE title IS NOT NULL 
          AND TRIM(title) != ''
          AND source_type != 'gemini_fallback'
          AND ARRAY_LENGTH(embedding) = @embedding_dim
    )
    SELECT *
    FROM RankedResults
    WHERE similarity_score >= 70  # Only return highly similar results
    ORDER BY similarity_score DESC
    LIMIT {top_k}
    """

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ArrayQueryParameter("query_embedding", "FLOAT64", query_embedding),
            bigquery.ScalarQueryParameter("embedding_dim", "INT64", len(query_embedding))
        ]
    )

    try:
        results = []
        query_job = client.query(sql, job_config=job_config)
        
        for row in query_job:
            result = {
                "pdf_name": row.pdf_name,
                "title": row.title,
                "summary": row.summary,
                "source_type": row.source_type,
                "file_hash": row.file_hash,
                "distance": row.distance,
                "similarity_score": row.similarity_score,
                "match_percentage": f"{row.similarity_score}%"
            }
            results.append(result)
            
        if results:
            print(f"✓ Found {len(results)} similar titles")
            print(f"  Top match: {results[0]['title']} ({results[0]['match_percentage']})")
        else:
            print("✗ No similar titles found above threshold")
            
        return results

    except Exception as e:
        print(f"❌ Error in title similarity search: {e}")
        import traceback
        traceback.print_exc()
        return []

def insert_vector_record(record: dict):
    """
    Insert embedding + metadata into BigQuery using a single dictionary record.
    This is consistent with our hash-based schema.
    """
    # Ensure the file_hash is present
    if 'file_hash' not in record:
        print("❌ Error: file_hash is missing from the vector record.")
        return

    # ✅ ADDED: Verify embedding dimensions before insertion
    embedding = record.get("embedding")
    if embedding:
        print(f"Inserting vector with {len(embedding)} dimensions")
    
    # Ensure all expected keys are in the record to avoid schema errors
    row = {
        "pdf_name": record.get("pdf_name"),
        "file_hash": record.get("file_hash"),
        "title": record.get("title"),
        "summary": record.get("summary"),
        "embedding": embedding,
        "source_type": record.get("source_type"),
        "created_at": record.get("created_at")
    }

    errors = client.insert_rows_json(VECTOR_TABLE_ID, [row])
    if errors:
        print("❌ Error inserting vector record:", errors)
    else:
        pdf_name = record.get("pdf_name", "N/A")
        print(f"✅ Inserted vector record for {pdf_name}")