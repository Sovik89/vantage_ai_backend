import hashlib
from io import BytesIO
from docx import Document
import PyPDF2
#import streamlit as st
import pandas as pd
import os
from datetime import datetime
import traceback
from fpdf import FPDF

#-------------------Common util functions---------------------------------#

def compute_pdf_hash(uploaded_file) -> str:
    """Computes a SHA256 hash of the uploaded file's content for deduplication."""
    uploaded_file.seek(0)
    data = uploaded_file.read()
    uploaded_file.seek(0)
    return hashlib.sha256(data).hexdigest()

def get_text_from_file(uploaded_file, file_ext: str) -> str:
    """Routes an uploaded file to the correct text extraction function based on its extension."""
    if file_ext == ".pdf":
        return read_pdf_text(uploaded_file)
    elif file_ext == ".docx":
        return read_docx_text(uploaded_file)
    elif file_ext == ".txt":
        return read_txt_text(uploaded_file)
    elif file_ext == ".csv":
        return read_csv_text(uploaded_file)
    else:
        st.warning(f"⚠️ Unsupported file type: {uploaded_file.name}")
        return ""

#---------------------------------------Import functions---------------------------------------#

def read_pdf_text(uploaded_file) -> str:
    """Extracts all text from an uploaded PDF file."""
    try:
        # ✅ CRITICAL FIX: Ensure the file stream is at the beginning before reading.
        uploaded_file.seek(0)
        reader = PyPDF2.PdfReader(uploaded_file)
        text = "".join(page.extract_text() or "" for page in reader.pages)
        return text.strip()
    except Exception as e:
        st.warning(f"Could not extract text from PDF: {e}")
        return ""


def read_docx_text(uploaded_file) -> str:
    """Extracts all text from an uploaded DOCX file."""
    try:
        uploaded_file.seek(0)
        doc = Document(uploaded_file)
        text = "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
        return text.strip()
    except Exception as e:
        st.warning(f"Could not extract text from DOCX: {e}")
        return ""

def read_txt_text(uploaded_file) -> str:
    """Reads text from an uploaded TXT file."""
    try:
        uploaded_file.seek(0)
        return uploaded_file.read().decode("utf-8").strip()
    except Exception as e:
        st.warning(f"Could not read TXT: {e}")
        return ""

def read_csv_text(uploaded_file) -> str:
    """Reads the first 20 rows of a CSV to provide context."""
    try:
        uploaded_file.seek(0)
        df = pd.read_csv(uploaded_file)
        # Take first few rows for context, convert to markdown string
        return df.head(20).to_markdown(index=False)
    except Exception as e:
        st.warning(f"Could not read CSV: {e}")
        return ""
    
#----------------------------Export functions------------------------------#

def export_to_docx(records, consolidated_text=None, user_prompt=None):
    """
    Exports summaries and a consolidated answer to a DOCX file in memory.
    Returns a BytesIO buffer.
    """
    doc= Document()
    doc.add_heading("HR Journal Insights", 0)
    
    if user_prompt:
        doc.add_paragraph(f"User Query: {user_prompt}")
    
    if consolidated_text:
        doc.add_heading("Consolidated Summary", level=1)
        doc.add_paragraph(consolidated_text)
    
    doc.add_heading("Individual Paper Summaries", level=1)
    
    for r in records:
        title = r.get("title") or r.get("pdf_name") or "Untitled"
        doc.add_heading(title, level=2)
        if r.get("summary"):
            doc.add_paragraph(r["summary"])

    buf = BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf, None, True



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
