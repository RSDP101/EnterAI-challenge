import math
from extract_text_with_custom_splits import extract_text_with_custom_splits
import re
def find_associated_value(keyword: str, pdf_path: str, direction: str = "right",tol_x_ratio=0.25, tol_y_ratio=0.25):
    """
    Find the text value that appears to the RIGHT or BELOW a given keyword
    in a 1-page PDF, using the segmented output from extract_text_with_custom_splits().

    Args:
        keyword (str): The label or keyword to search for (e.g. "Subseção", "Telefone Profissional").
        pdf_path (str): Path to the PDF file.
        direction (str): "right" or "below" — which direction to search in.
        x_tolerance (float): How far horizontally (in pixels) to allow when matching boxes.
        y_tolerance (float): How far vertically (in pixels) to allow when matching boxes.

    Returns:
        str | None: The text found in the box associated with the keyword in the given direction,
                    or None if not found.
    """
    # Step 1: extract all chunks (text, bbox)
    results = extract_text_with_custom_splits(pdf_path)
    if not results:
        print("⚠️ No text extracted.")
        return None

    # Step 2: locate keyword box
    keyword_lower = keyword.lower().strip()
    keyword_box = None
    for text, bbox in results:
        if keyword_lower in text.lower():
            keyword_box = bbox
            break

    if not keyword_box:
        print(f"⚠️ Keyword '{keyword}' not found in document.")
        return None

    x0, y0, x1, y1 = keyword_box
    kw_center = ((x0 + x1) / 2, (y0 + y1) / 2)
    print ("kw center: ", kw_center)
    min_gap=0.0
    # Step 3: search for nearby boxes in the given direction
    candidates = []
    for text, bbox in results:
        if keyword_lower in text.lower():
            keyword_box = bbox
            break

    if not keyword_box:
        print(f"⚠️ Keyword '{keyword}' not found.")
        return None

    x0, y0, x1, y1 = keyword_box
    kw_height = y1 - y0
    kw_width = x1 - x0
    tol_x = tol_x_ratio * kw_width
    tol_y = tol_y_ratio * kw_height
    candidates = []
    print (f"[INFO] tolerances tol_x: {tol_x}, tol_y: {tol_y}")
    for text, bbox in results:
        
        if bbox == keyword_box:
            continue
        # Skip identical or near-identical text matches
        if keyword_lower in text.lower():
            continue
        
        bx0, by0, bx1, by1 = bbox
        dx_left = bx0 - x1     # how far to the right
        dy_top  = by0 - y1     # how far below
        dx_align = abs(bx0 - x0)
        dy_align = abs(by0 - y0)

        if direction == "right":
            # Block must be to the right and vertically aligned
            if dx_left < min_gap:
                continue
            if dy_align > tol_y:
                continue
            candidates.append((dx_left, text.strip(), (bx0, by0, bx1, by1)))

        elif direction == "below":
            # Block must be below and horizontally aligned
            if dy_top <= min_gap:
                continue
            if dx_align > tol_x:
                continue
            candidates.append((dy_top, text.strip(), (bx0, by0, bx1, by1)))

        else:
            raise ValueError("direction must be either 'right' or 'below'")

    if not candidates:
        print(f"⚠️ No well-aligned block found {direction}.")
        return None, None

    # Pick the nearest aligned candidate
    candidates.sort(key=lambda c: c[0])
    print (candidates)
    best_gap, best_text, best_box = candidates[0]
    print(f"✅ '{best_text}' found {round(best_gap, 2)} px to the {direction} of '{keyword}'.")
    print(f"   keyword box={keyword_box}, value box={best_box}")
    return best_text

# -------------------------------
# 🧪 Example usage
# -------------------------------
if __name__ == "__main__":
    pdf_path = "./examples/oab_1.pdf"

    # Example 1: find value BELOW "Telefone Profissional"
    value2 = find_associated_value("Subseção", pdf_path, direction="below")
    print(f"\nResult → Endereço Profissional: {value2}")
