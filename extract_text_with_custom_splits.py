import fitz
import math
from io import BytesIO

def extract_text_with_custom_splits(pdf_bytes: bytes, x_gap_thresh=30, space_thresh=3):
    """
    Extract text chunks with bounding boxes, splitting when horizontal gaps or spaces are too large.
    
    Args:
        pdf_path: path to the 1-page OCRed PDF
        x_gap_thresh: pixel distance threshold to separate words horizontally
        space_thresh: number of consecutive spaces to trigger a split
    """
    doc = fitz.open(stream=BytesIO(pdf_bytes), filetype="pdf")
    page = doc[0]
    blocks = page.get_text("dict")["blocks"]

    results = []
    for b in blocks:
        if b.get("type", 0) != 0:
            continue  # skip images
        for line in b["lines"]:
            spans = line.get("spans", [])
            if not spans:
                continue

            current_chunk = ""
            current_xs, current_ys, current_xe, current_ye = [], [], [], []
            last_x1 = None

            for span in spans:
                text = span.get("text", "")
                x0, y0, x1, y1 = span["bbox"]

                # detect horizontal distance gap
                if last_x1 is not None:
                    x_gap = x0 - last_x1
                    space_gap = text.count(" ")
                    if x_gap > x_gap_thresh or space_gap > space_thresh:
                        # finalize previous chunk
                        if current_chunk.strip():
                            bbox = (min(current_xs), min(current_ys),
                                    max(current_xe), max(current_ye))
                            results.append((current_chunk.strip(), bbox))
                        current_chunk = ""
                        current_xs, current_ys, current_xe, current_ye = [], [], [], []

                # append current span
                current_chunk += text
                current_xs.append(x0); current_ys.append(y0)
                current_xe.append(x1); current_ye.append(y1)
                last_x1 = x1

            # finalize last chunk of line
            if current_chunk.strip():
                bbox = (min(current_xs), min(current_ys),
                        max(current_xe), max(current_ye))
                results.append((current_chunk.strip(), bbox))

    print("\n=== TEXT CHUNKS WITH CUSTOM SPLITS ===\n")
    for text, bbox in results:
        print(f"{text!r}  →  {bbox}")

    return results


# if __name__ == "__main__":
#     pdf_path = "./examples/oab_1.pdf"  # change path
#     with open(pdf_path, "rb") as f:
#         pdf_bytes = f.read()

#     results = extract_text_with_custom_splits(pdf_bytes)
#     print (results)