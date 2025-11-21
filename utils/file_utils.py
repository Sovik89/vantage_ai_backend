# file_utils.py
# Patched: original utilities preserved; added Excel sheet readers and feedback row extractor.
import hashlib
from io import BytesIO
from docx import Document
import pypdf
import PyPDF2
import pandas as pd
import os
import traceback
import io
import re
from google.cloud import storage
import spacy
from typing import List, Tuple, Dict
from collections import defaultdict
from statistics import mean

nlp = None
def _ensure_spacy():
    global nlp
    if nlp is None:
        try:
            nlp = spacy.load("en_core_web_sm")
        except Exception:
            # fallback: load blank English pipeline if model not present
            nlp = spacy.blank("en")
    return nlp

# This file is now fully synchronous and works with in-memory BytesIO buffers.

def compute_file_hash(content: bytes) -> str:
    """Computes a SHA256 hash of the file's content."""
    return hashlib.sha256(content).hexdigest()

def get_text_from_file(content_buffer: BytesIO, file_ext: str) -> str:
    """Routes a file buffer to the correct text extraction function."""
    file_ext = file_ext.lower().replace('.', '')
    if file_ext == "pdf":
        return read_pdf_text(content_buffer)
    elif file_ext == "docx":
        return read_docx_text(content_buffer)
    elif file_ext == "txt":
        return read_txt_text(content_buffer)
    elif file_ext == "csv":
        return read_csv_text(content_buffer)
    else:
        # For unknown, try excel extraction as text
        if file_ext in ("xls", "xlsx"):
            try:
                # get first sheet text
                sheets = read_excel_sheets_from_bytes(content_buffer.getvalue() if isinstance(content_buffer, BytesIO) else content_buffer, "upload.xlsx")
                # join tiny preview
                texts = []
                for name, df in sheets.items():
                    texts.append(f"Sheet: {name}\n{df.head(5).to_markdown(index=False)}")
                return "\n\n".join(texts)
            except Exception:
                pass
        print(f"⚠️ Unsupported file type provided.")
        return ""

def read_pdf_text(content_buffer: BytesIO) -> str:
    """Extracts text from a PDF using a primary and fallback library."""
    text = ""
    try:
        content_buffer.seek(0)
        pdf_reader = pypdf.PdfReader(content_buffer)
        text = "".join(page.extract_text() or "" for page in pdf_reader.pages)
    except Exception as e_pypdf:
        print(f"Primary PDF reader (pypdf) failed: {e_pypdf}. Trying fallback.")
        try:
            content_buffer.seek(0)
            pdf_reader_fallback = PyPDF2.PdfReader(content_buffer)
            text = "".join(page.extract_text() or "" for page in pdf_reader_fallback.pages)
        except Exception as e_pypdf2:
            print(f"Fallback PDF reader (PyPDF2) also failed: {e_pypdf2}")
            return ""
    return text.strip()

def read_docx_text(content_buffer: BytesIO) -> str:
    """Extracts text from a DOCX file."""
    try:
        content_buffer.seek(0)
        doc = Document(content_buffer)
        text = "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
        return text.strip()
    except Exception as e:
        print(f"Could not extract text from DOCX: {e}")
        return ""

def read_txt_text(content_buffer: BytesIO) -> str:
    """Reads text from a TXT file."""
    try:
        content_buffer.seek(0)
        content = content_buffer.read()
        return content.decode("utf-8").strip()
    except Exception as e:
        print(f"Could not read TXT: {e}")
        return ""

def read_csv_text(content_buffer: BytesIO) -> str:
    """Reads the first 20 rows of a CSV."""
    try:
        content_buffer.seek(0)
        df = pd.read_csv(content_buffer)
        return df.head(20).to_markdown(index=False)
    except Exception as e:
        print(f"Could not read CSV: {e}")
        return ""

# Note: The export_to_docx function remains unchanged as it doesn't handle async file objects.
def export_to_docx(records, consolidated_text=None, user_prompt=None):
    """Exports summaries and a consolidated answer to a DOCX file in memory."""
    doc = Document()
    doc.add_heading("Vantage.Ai Insights", 0)
    
    if user_prompt:
        doc.add_paragraph(f"User Query: {user_prompt}")
    
    if consolidated_text:
        doc.add_heading("Consolidated Summary", level=1)
        doc.add_paragraph(consolidated_text)
    
    if records:
        doc.add_heading("Source Document Summaries", level=1)
        for r in records:
            title = r.get("title") or r.get("pdf_name") or "Untitled"
            doc.add_heading(title, level=2)
            if r.get("summary"):
                doc.add_paragraph(r["summary"])

    buf = BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf


def clean_text(text):
    if not text:
        return ""
    return (
        text.replace("–", "-")
            .replace("—", "-")
            .replace("’", "'")
            .replace("“", '"')
            .replace("”", '"')
            .replace("…", "...")
    )

def export_to_pdf(records, consolidated_text=None, user_prompt=None):
    from fpdf import FPDF
    from io import BytesIO

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, clean_text("HR Journal Insights"), ln=True, align="C")

    pdf.set_font("Arial", "", 12)
    if user_prompt:
        pdf.ln(10)
        pdf.multi_cell(0, 10, clean_text(f"User Query: {user_prompt}"))

    if consolidated_text:
        pdf.ln(10)
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, clean_text("Consolidated Summary"), ln=True)
        pdf.set_font("Arial", "", 12)
        pdf.multi_cell(0, 10, clean_text(consolidated_text))

    pdf.ln(10)
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, clean_text("Individual Paper Summaries"), ln=True)

    for r in records:
        title = r.get("title") or r.get("pdf_name") or "Untitled"
        summary = r.get("summary", "")
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, clean_text(title), ln=True)
        pdf.set_font("Arial", "", 12)
        if summary:
            pdf.multi_cell(0, 10, clean_text(summary))
        pdf.ln(5)

    buf = BytesIO()
    buf.write(pdf.output(dest='S').encode('latin-1'))
    buf.seek(0)
    return buf, None, True

def extract_text_from_bytes(file_bytes: bytes, filename: str, max_rows:int=10000) -> Tuple[List[str], List[int]]:
    """
    Returns (texts, row_indices) - detects a 'feedback' column or picks first string column.
    """
    buf = io.BytesIO(file_bytes)
    try:
        df = pd.read_excel(buf, engine="openpyxl")
    except Exception:
        df = pd.read_excel(buf)  # fallback
    return _extract_from_df(df, max_rows)

def extract_text_from_gcs(gcs_path: str, max_rows:int=10000) -> Tuple[List[str], List[int]]:
    # gcs_path like gs://bucket/path
    client = storage.Client()
    if not gcs_path.startswith("gs://"):
        raise ValueError("gcs_path must be gs://")
    _p = gcs_path[len("gs://"):]
    bucket_name, _, blob_path = _p.partition("/")
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_path)
    data = blob.download_as_bytes()
    return extract_text_from_bytes(data, blob_path, max_rows)

def _extract_from_df(df: pd.DataFrame, max_rows:int):
    # detect feedback-like column
    candidates = [c for c in df.columns if any(k in c.lower() for k in ("feedback","comment","response","text","answer"))]
    if candidates:
        col = candidates[0]
        series = df[col]
    else:
        # fallback: pick first object/string column
        obj_cols = [c for c in df.columns if df[c].dtype == 'object']
        if obj_cols:
            col = obj_cols[0]
            series = df[col]
        else:
            # if no text columns, stringify rows
            series = df.apply(lambda r: " | ".join([str(x) for x in r.values if pd.notna(x)]), axis=1)
    # clean and limit
    texts = []
    indices = []
    for i, v in enumerate(series.fillna("").astype(str).tolist(), start=1):
        t = v.strip()
        if not t:
            continue
        if len(texts) >= max_rows:
            break
        texts.append(t)
        indices.append(i)
    return texts, indices

def sanitize_text(text:str, redact_names:bool=True) -> Tuple[str, dict]:
    """
    Redact PERSON and EMAIL found in text.
    Returns (redacted_text, flags)
    """
    nlp = _ensure_spacy()
    doc = nlp(text)
    redacted = text
    flags = {"redacted_names": False, "redacted_emails": False}
    # replace entities in reverse order to keep indices valid
    for ent in reversed(list(doc.ents)):
        if ent.label_ in ("PERSON",):
            if redact_names:
                start, end = ent.start_char, ent.end_char
                redacted = redacted[:start] + "[REDACTED_NAME]" + redacted[end:]
                flags["redacted_names"] = True
    # redact emails with regex as extra layer
    email_re = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
    if email_re.search(redacted):
        redacted = email_re.sub("[REDACTED_EMAIL]", redacted)
        flags["redacted_emails"] = True
    return redacted, flags

# ----------------- New helper functions added for sentiment pipeline -----------------

def read_excel_sheets_from_bytes(file_bytes: bytes, filename: str = "upload.xlsx") -> Dict[str, pd.DataFrame]:
    """
    Read an excel file from bytes and return a dict mapping sheet_name -> DataFrame.
    Handles xls/xlsx and some malformed files robustly.
    """
    buf = BytesIO(file_bytes) if not isinstance(file_bytes, BytesIO) else file_bytes
    try:
        # engine openpyxl handles xlsx; xlrd removed for xls; pandas will choose fallback
        sheets = pd.read_excel(buf, sheet_name=None, engine="openpyxl")
        # ensure DataFrame objects (pandas returns dict if multiple sheets)
        return {str(k): v for k, v in sheets.items()}
    except Exception as e:
        # fallback: try without engine, or try to read first sheet only
        try:
            buf.seek(0)
            sheets = pd.read_excel(buf, sheet_name=None)
            return {str(k): v for k, v in sheets.items()}
        except Exception as e2:
            # if still failing, raise a helpful error
            raise RuntimeError(f"Failed to read excel bytes for {filename}: {e}; fallback error: {e2}")

def read_excel_sheets_from_path(path: str) -> Dict[str, pd.DataFrame]:
    """
    Convenience: read excel sheets from a file path.
    """
    try:
        sheets = pd.read_excel(path, sheet_name=None, engine="openpyxl")
        return {str(k): v for k, v in sheets.items()}
    except Exception:
        return pd.read_excel(path, sheet_name=None)

def _is_text_like(dtype) -> bool:
    """Return True if pandas dtype is string/object-ish."""
    try:
        return pd.api.types.is_string_dtype(dtype) or pd.api.types.is_object_dtype(dtype)
    except Exception:
        return False

def extract_feedback_rows_from_df(df: pd.DataFrame, max_rows: int = 10000) -> List[dict]:
    """
    Convert a questionnaire sheet DataFrame into a list of feedback row dicts:
    Each item: { row_id, question_id, question_text, response_text }
    Handles different sheet shapes:
      - Single free-text column (Feedback/Comment/Response)
      - Multiple question columns (Q1, Q2, Question 1, etc.) -> flattens per cell
      - If no text columns, concatenates row values into a string per respondent
    """
    rows_out = []
    if df is None or df.shape[0] == 0:
        return rows_out

    # Normalize column headers to strings
    cols = [str(c).strip() for c in df.columns]

    # 1) Candidate response columns (high priority)
    resp_candidates = [c for c in cols if any(k in c.lower() for k in ("feedback", "comment", "response", "answer", "remark", "text"))]
    # 2) Candidate question-style columns like Q1, Question 1 etc.
    q_candidates = [c for c in cols if re.match(r"^(q|question|ques|q\W*\d+)", c.lower())]
    # 3) If no candidates, pick all object/string columns
    if not resp_candidates and not q_candidates:
        obj_cols = [c for c in cols if _is_text_like(df[c].dtype)]
        if obj_cols:
            resp_candidates = obj_cols

    # If there are explicit response columns, prefer them (one column per feedback)
    if resp_candidates and not q_candidates:
        col = resp_candidates[0]
        for idx, val in enumerate(df[col].fillna("").astype(str).tolist(), start=1):
            val = val.strip()
            if not val:
                continue
            row_id = f"r{idx}"
            rows_out.append({
                "row_id": row_id,
                "question_id": col,
                "question_text": col,
                "response_text": val
            })
            if len(rows_out) >= max_rows:
                break
        return rows_out

    # If multiple question columns (q_candidates found), flatten them into per-question entries
    if q_candidates:
        for ridx, row in df.iterrows():
            for col in q_candidates:
                try:
                    cell = row.get(col)
                except Exception:
                    cell = row[col] if col in row else ""
                if pd.isna(cell):
                    continue
                text = str(cell).strip()
                if not text:
                    continue
                row_id = f"{ridx+1}_{col}"
                rows_out.append({
                    "row_id": row_id,
                    "question_id": col,
                    "question_text": col,
                    "response_text": text
                })
                if len(rows_out) >= max_rows:
                    break
            if len(rows_out) >= max_rows:
                break
        return rows_out

    # As a last resort, treat each row as a concatenated response (useful for tables)
    for ridx, row in df.iterrows():
        parts = []
        for col in cols:
            try:
                val = row.get(col)
            except Exception:
                val = row[col] if col in row else None
            if pd.isna(val):
                continue
            s = str(val).strip()
            if s:
                parts.append(f"{col}: {s}")
        if not parts:
            continue
        text = " | ".join(parts)
        row_id = f"r{ridx+1}"
        rows_out.append({
            "row_id": row_id,
            "question_id": "composite",
            "question_text": "composite",
            "response_text": text
        })
        if len(rows_out) >= max_rows:
            break
    return rows_out



def extract_candidate_feedback_rows(df: pd.DataFrame, max_rows: int = 10000) -> List[Dict]:
    """
    Extract feedback with CANDIDATE CONTEXT preservation.
    
    Expected sheet structure:
    | candidate_id | candidate_name | Q1_text | Q2_text | Q3_text | ... |
    OR
    | Candidate ID | Candidate Name | Question 1 | Question 2 | ... |
    
    Returns: List of dicts with:
    {
        "candidate_id": str,
        "candidate_name": str,
        "question_id": str,
        "question_text": str (column name),
        "response_text": str,
        "row_index": int
    }
    """
    rows_out = []
    if df is None or df.shape[0] == 0:
        return rows_out
    
    # Normalize column names
    df.columns = [str(c).strip() for c in df.columns]
    cols = df.columns.tolist()
    
    # 1. DETECT CANDIDATE ID COLUMN
    candidate_id_col = None
    for col in cols:
        col_lower = col.lower()
        if any(pattern in col_lower for pattern in ['candidate_id', 'candidateid', 'employee_id', 'employeeid', 'emp_id', 'empid', 'id']):
            candidate_id_col = col
            break
    
    # 2. DETECT CANDIDATE NAME COLUMN
    candidate_name_col = None
    for col in cols:
        col_lower = col.lower()
        if any(pattern in col_lower for pattern in ['candidate_name', 'candidatename', 'name', 'employee_name', 'employeename', 'emp_name', 'empname']):
            candidate_name_col = col
            break
    
    # 3. DETECT QUESTION COLUMNS (all columns that aren't ID/Name and are text-like)
    excluded_cols = {candidate_id_col, candidate_name_col}
    excluded_cols = {c for c in excluded_cols if c is not None}
    
    question_cols = []
    for c in cols:
        if c not in excluded_cols:
            # Check if it's a text column
            if df[c].dtype == 'object' or pd.api.types.is_string_dtype(df[c]):
                question_cols.append(c)
    
    print(f"DEBUG: Detected candidate_id_col={candidate_id_col}")
    print(f"DEBUG: Detected candidate_name_col={candidate_name_col}")
    print(f"DEBUG: Detected {len(question_cols)} question columns: {question_cols[:5]}...")
    
    if not candidate_id_col and not candidate_name_col:
        print("WARNING: No candidate identifier columns found. Using row index as candidate_id.")
    
    # 4. EXTRACT EACH CANDIDATE'S RESPONSES
    for row_idx, row in df.iterrows():
        # Get candidate identifiers
        if candidate_id_col:
            candidate_id = str(row.get(candidate_id_col, f"candidate_{row_idx+1}"))
        else:
            candidate_id = f"candidate_{row_idx+1}"
        
        if candidate_name_col:
            candidate_name = str(row.get(candidate_name_col, "Unknown"))
        else:
            candidate_name = f"Candidate {row_idx+1}"
        
        # Extract each question response for this candidate
        for q_col in question_cols:
            try:
                response = row.get(q_col)
                if pd.isna(response):
                    continue
                
                response_text = str(response).strip()
                if not response_text or len(response_text) < 10:  # Skip very short responses
                    continue
                
                rows_out.append({
                    "candidate_id": candidate_id,
                    "candidate_name": candidate_name,
                    "question_id": q_col,
                    "question_text": q_col,
                    "response_text": response_text,
                    "row_index": int(row_idx)
                })
                
                if len(rows_out) >= max_rows:
                    return rows_out
                    
            except Exception as e:
                print(f"WARNING: Failed to extract Q={q_col} for candidate {candidate_id}: {e}")
                continue
    
    print(f"DEBUG: Extracted {len(rows_out)} total feedback items from {len(df)} candidates")
    return rows_out

# End of file_utils.py
