#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
extract_from_keyword.py
-----------------------

Extract a specific information value near a keyword in an OCRed PDF.
Uses PyMuPDF for geometric search (bounding boxes).
Optionally falls back to LLM for disambiguation if heuristic fails.

Dependencies:
    pip install pymupdf openai

Usage:
    python extract_from_keyword.py path/to/file.pdf "CPF" right
"""

import fitz  # PyMuPDF
import sys
import re
import os

# Optional LLM (requires OPENAI_API_KEY)
USE_LLM = bool(os.getenv("OPENAI_API_KEY"))
if USE_LLM:
    from openai import OpenAI
    client = OpenAI()
    MODEL = "gpt-5-mini"


def get_nearby_text(blocks, keyword_bbox, direction="right", max_dist=80):
    """Find text blocks near keyword_bbox based on geometric heuristics."""
    kx0, ky0, kx1, ky1 = keyword_bbox
    kcx = (kx0 + kx1) / 2
    kcy = (ky0 + ky1) / 2
    candidates = []

    for (x0, y0, x1, y1, text, *_ ) in blocks:
        cx = (x0 + x1) / 2
        cy = (y0 + y1) / 2
        if direction == "right" and x0 > kcx and abs(cy - kcy) < max_dist:
            candidates.append((x0, text))
        elif direction == "below" and y0 > ky1 and abs(cx - kcx) < max_dist:
            candidates.append((y0, text))

    candidates.sort()
    return candidates[0][1].strip() if candidates else None


def extract_value_by_keyword(pdf_path, keyword, direction="right"):
    """
    Extract the text value associated with a given keyword in a 1-page OCRed PDF.

    Args:
        pdf_path: str, path to PDF (with embedded OCR text)
        keyword: str, keyword to locate (e.g. "CPF")
        direction: "right" or "below" (depending on document layout)
    Returns:
        Extracted string or None.
    """
    doc = fitz.open(pdf_path)
    page = doc[0]
    blocks = page.get_text("blocks")

    # Search for keyword (case-insensitive)
    rects = []
    for kw_variant in [keyword, keyword.upper(), keyword.lower(), keyword.capitalize()]:
        rects = page.search_for(kw_variant)
        if rects:
            break

    if not rects:
        print(f"⚠️ Keyword '{keyword}' not found.")
        return None

    keyword_bbox = rects[0]
    value = get_nearby_text(blocks, keyword_bbox, direction=direction)
    return value


def extract_keyword_context(pdf_path, keyword, window_chars=300):
    """Return a local text window around the keyword for LLM or fallback."""
    doc = fitz.open(pdf_path)
    text = doc[0].get_text("text")
    norm_text = text.lower()
    keyword_lower = keyword.lower()
    match = re.search(re.escape(keyword_lower), norm_text)
    if not match:
        return text
    start, end = match.start(), match.end()
    context_start = max(0, start - window_chars)
    context_end = min(len(text), end + window_chars)
    return text[context_start:context_end].strip()


def llm_fallback(keyword, context):
    """Ask LLM to extract value from local text context."""
    if not USE_LLM:
        return None
    prompt = f"""
    Extract the value or information related to the keyword '{keyword}' in this text.
    Return only the value (no explanation).

    Context:
    {context}
    """
    try:
        resp = client.chat.completions.create(
            model=MODEL,
            temperature=0,
            messages=[
                {"role": "system", "content": "You are a precise text extraction assistant."},
                {"role": "user", "content": prompt.strip()},
            ],
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        print("LLM fallback failed:", e)
        return None


def extract_information(pdf_path, keyword, direction="right"):
    """
    Main function: try heuristic first, fallback to LLM using local context if needed.
    """
    value = extract_value_by_keyword(pdf_path, keyword, direction)
    if value:
        print(f"✅ Heuristic extraction succeeded: {keyword} → {value}")
        return value

    # fallback if heuristic fails
    print(f"🔁 Heuristic failed; trying LLM fallback for '{keyword}'...")
    context = extract_keyword_context(pdf_path, keyword)
    value = llm_fallback(keyword, context)
    if value:
        print(f"✅ LLM extraction succeeded: {keyword} → {value}")
        return value
    print(f"❌ Could not extract value for '{keyword}'.")
    return None


# =========================
# Test / CLI entry point
# =========================
if __name__ == "__main__":

    pdf_path = "./examples/tela_sistema_1.pdf"  # adjust path
    keyword = "Data"
    direction = "below"

    value = extract_information(pdf_path, keyword, direction)
    print("\n=== FINAL RESULT ===")
    print(f"{keyword}: {value}")
