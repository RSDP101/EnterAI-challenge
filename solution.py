import json
import sys
import os
import fitz
from openai import OpenAI
from extract_text_with_custom_splits import extract_text_with_custom_splits
from math import isfinite
from typing import Dict, Any
import re

# -------------------------------
# 1️⃣ Local Geometric Extractor
# -------------------------------
def find_associated_value(keyword: str, pdf_path: str, direction: str = "right",
                          tol_x_ratio=0.25, tol_y_ratio=0.25):
    """
    Find the text value that appears to the RIGHT or BELOW a given keyword
    in a 1-page PDF, using the segmented output from extract_text_with_custom_splits().
    """
    results = extract_text_with_custom_splits(pdf_path)
    if not results:
        print("⚠️ No text extracted.")
        return None

    keyword_lower = keyword.lower().strip()
    keyword_box = None
    for text, bbox in results:
        if keyword_lower in text.lower():
            keyword_box = bbox
            break

    if not keyword_box:
        return None

    x0, y0, x1, y1 = keyword_box
    kw_height = y1 - y0
    kw_width = x1 - x0
    tol_x = tol_x_ratio * kw_width
    tol_y = tol_y_ratio * kw_height
    min_gap = 0.0

    candidates = []
    for text, bbox in results:
        if bbox == keyword_box:
            continue
        if keyword_lower in text.lower():
            continue
        bx0, by0, bx1, by1 = bbox
        dx_left = bx0 - x1
        dy_top = by0 - y1
        dx_align = abs(bx0 - x0)
        dy_align = abs(by0 - y0)

        if direction == "right":
            if dx_left < min_gap or dy_align > tol_y:
                continue
            candidates.append((dx_left, text.strip(), bbox))
        elif direction == "below":
            if dy_top <= min_gap or dx_align > tol_x:
                continue
            candidates.append((dy_top, text.strip(), bbox))

    if not candidates:
        return None

    candidates.sort(key=lambda c: c[0])
    _, best_text, _ = candidates[0]
    return best_text


# -------------------------------
# 2️⃣ OCR Chunk Extractor (imported)
# -------------------------------
def extract_text(pdf_path):
    """Return all text from PDF for LLM fallback."""
    doc = fitz.open(pdf_path)
    return "\n".join(page.get_text("text") for page in doc)


# -------------------------------
# 3️⃣ LLM Fallback
# -------------------------------
def llm_fallback_extract(label: str, schema: Dict[str, str], pdf_text: str) -> Dict[str, str]:
    """
    Use GPT-5-mini to extract missing fields given OCR text and schema.
    """
    client = OpenAI()

    system_prompt = f"""
    You are a data extraction assistant. 
    The document label is '{label}'.
    The following is the OCRed text of the PDF. 
    For each field, extract the best possible value based on the description.
    Return a JSON strictly matching the provided schema keys.
    """

    user_prompt = f"""
    SCHEMA (key: description):
    {json.dumps(schema, ensure_ascii=False, indent=2)}

    TEXT:
    {pdf_text[:6000]}  # limit for efficiency
    """

    try:
        response = client.chat.completions.create(
            model="gpt-5-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content
        return json.loads(content)
    except Exception as e:
        print("⚠️ LLM fallback failed:", e)
        return {key: None for key in schema}


# -------------------------------
# 4️⃣ Main Solution Function
# -------------------------------
def extract_structured_data(pdf_path: str, label: str, schema: Dict[str, str]) -> Dict[str, Any]:
    """
    Extract structured information from the PDF according to schema.
    Uses geometric search first, then LLM fallback.
    """
    result = {}
    print(f"🔍 Processing '{label}' on {pdf_path}")

    # Try to find values locally
    for field_name in schema.keys():
        print(f"→ Searching for '{field_name}' ...")
        value = find_associated_value(field_name, pdf_path, direction="right")
        if not value:
            value = find_associated_value(field_name, pdf_path, direction="below")
        result[field_name] = value if value else None

    # Determine which were missing
    missing_fields = {k: v for k, v in result.items() if v is None}
    print(f"\n❌ Missing fields: {list(missing_fields.keys())}")

    # If missing, call LLM fallback
    if missing_fields:
        pdf_text = extract_text(pdf_path)
        llm_results = llm_fallback_extract(label, missing_fields, pdf_text)
        result.update({k: v for k, v in llm_results.items() if v})

    print("\n✅ Final extracted schema:")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return result


# -------------------------------
# 5️⃣ CLI Usage
# -------------------------------
if __name__ == "__main__":

    pdf_path = "./examples/oab_1.pdf"
    label = "carteira_oab"
    schema_path = ""

    with open(schema_path, "r", encoding="utf-8") as f:
        schema = json.load(f)

    output = extract_structured_data(pdf_path, label, schema)

    # save to output.json
    with open("output.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print("\n📝 Saved final output to output.json")
