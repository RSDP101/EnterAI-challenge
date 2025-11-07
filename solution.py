# bbox_extractor.py
import os, json, math
from typing import Dict, List, Optional
from pdf_parser import parse_pdf, llm_extract
from extract_text_with_custom_splits import extract_text_with_custom_splits
MEMORY_PATH = "bbox_memory.json"


# ============ Utility helpers ============
def load_memory() -> Dict:
    """Load bounding-box memory from disk."""
    if os.path.exists(MEMORY_PATH):
        try:
            return json.load(open(MEMORY_PATH, "r", encoding="utf-8"))
        except Exception:
            return {}
    return {}

def save_memory(mem: Dict):
    json.dump(mem, open(MEMORY_PATH, "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)


def update_memory(label: str, llm_result: Dict[str, Optional[Dict]]):
    """Update per-field bounding-box history after each LLM extraction."""
    mem = load_memory()
    label_mem = mem.setdefault(label, {"seen": 0, "fields": {}})
    label_mem["seen"] += 1

    for field, data in llm_result.items():
        if not data or not isinstance(data, dict) or not data.get("bbox"):
            continue
        label_mem["fields"].setdefault(field, {"boxes": []})
        label_mem["fields"][field]["boxes"].append(data["bbox"])

    save_memory(mem)


def average_box(boxes: List[List[float]]) -> List[float]:
    """Compute average of a list of boxes."""
    xs0, ys0, xs1, ys1 = zip(*boxes)
    return [sum(xs0)/len(xs0), sum(ys0)/len(ys0),
            sum(xs1)/len(xs1), sum(ys1)/len(ys1)]

def box_center(b: List[float]) -> List[float]:
    x0, y0, x1, y1 = b
    return [(x0+x1)/2, (y0+y1)/2]

def box_distance(b1: List[float], b2: List[float]) -> float:
    c1, c2 = box_center(b1), box_center(b2)
    return math.dist(c1, c2)


# ============ Geometric extraction ============
def extract_by_geometry(label: str, schema: Dict[str, str], lines: List[Dict]) -> Dict[str, Dict]:
    mem = load_memory().get(label, {})
    result = {}

    for field in schema:
        fmem = mem.get("fields", {}).get(field)
        if not fmem or not fmem.get("boxes"):
            result[field] = None
            continue

        avg_box = average_box(fmem["boxes"])
        nearest = min(lines, key=lambda l: box_distance(l["bbox"], avg_box))
        result[field] = {
            "value": nearest["text"],
            "page": nearest["page"],
            "bbox": nearest["bbox"]
        }

    return result


# ============ Controller logic ============
def extract(label: str, schema: Dict[str, str], pdf_bytes):
    """
    Strategy:
    - For first 3 samples of a label: use LLM, store bounding boxes.
    - After 3 samples: use geometric proximity extraction (no LLM).
    """

    # lines = parse_pdf(pdf_bytes)
    lines_list = extract_text_with_custom_splits(pdf_bytes)
    lines = []
    for text, bbox in lines_list:
        if not text.strip():
            continue
        lines.append({
            "page": 1,              # assuming 1-page PDFs (update if multi-page)
            "text": text.strip(),
            "bbox": [float(b) for b in bbox],
        })

    print("\n=== EXTRACTED OCR LINES ===")
    for l in lines:
        print(f"{l['text']!r}  →  {l['bbox']}")
    print("============================\n")

    mem = load_memory()
    label_mem = mem.get(label, {"seen": 0})
    seen = label_mem.get("seen", 0)

    # Case 1: Use LLM for first 3 documents
    if seen < 3:
        print(f"[INFO] Using LLM extraction (sample {seen+1}/3) for label '{label}'.")
        try:
            llm_result = llm_extract(label, schema, lines)
            update_memory(label, llm_result)
            return llm_result
        except Exception as e:
            print(f"[ERROR] LLM extraction failed ({e}), falling back to geometric.")
            return extract_by_geometry(label, schema, lines)

    # Case 2: Geometric extraction after 3 samples
    print(f"[INFO] Using geometric extraction for label '{label}' (seen={seen}).")
    geo_result = extract_by_geometry(label, schema, lines)

    # ✅ Count how many fields are None
    total_fields = len(schema)
    null_fields = sum(1 for v in geo_result.values() if v is None)
    null_ratio = null_fields / total_fields if total_fields else 0

    print(f"[DEBUG] Geometric extraction null ratio: {null_ratio:.2%}")

    # ✅ If more than 50% of fields are missing → call LLM as fallback
    if null_ratio > 0.5:
        print(f"[INFO] More than 50% fields missing ({null_ratio:.1%}). Retrying with LLM...")
        try:
            llm_result = llm_extract(label, schema, lines)
            update_memory(label, llm_result)
            return llm_result
        except Exception as e:
            print(f"[ERROR] LLM fallback failed ({e}). Returning geometric result instead.")
            return geo_result

    # Otherwise keep geometric result
    return geo_result


# ============ CLI: Batch dataset runner ============
if __name__ == "__main__":
    from tqdm import tqdm  # optional progress bar
    if os.path.exists("bbox_memory.json"):
        os.remove("bbox_memory.json")
        print("[INFO] Cleared bbox_memory.json (fresh learning run).")

    DATASET_PATH = "examples/dataset.json"
    OUTPUT_PATH = "output.json"

    if not os.path.exists(DATASET_PATH):
        raise FileNotFoundError(f"{DATASET_PATH} not found")

    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    results = []

    print(f"[INFO] Running extraction for {len(dataset)} documents...\n")

    for item in tqdm(dataset, desc="Processing PDFs"):
        label = item["label"]
        schema = item["extraction_schema"]
        pdf_path = item["pdf_path"]

        if not os.path.exists(pdf_path):
            print(f"⚠️ Skipping missing file: {pdf_path}")
            continue

        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()

        try:
            extraction_result = extract(label, schema, pdf_bytes)
        except Exception as e:
            print(f"[ERROR] Extraction failed for {pdf_path}: {e}")
            extraction_result = {k: None for k in schema.keys()}

        # === Clean extracted_fields (strip bbox/page) ===
        cleaned = {}
        for field, data in extraction_result.items():
            if isinstance(data, dict) and "value" in data:
                cleaned[field] = data["value"]
            else:
                cleaned[field] = data

        results.append({
            "label": label,
            "extraction_schema": schema,
            "pdf_path": pdf_path,
            "extracted_fields": cleaned
        })

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Extraction complete! Clean results saved to {OUTPUT_PATH}")
