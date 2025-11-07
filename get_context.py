import fitz  # PyMuPDF
import re

def extract_keyword_context(pdf_path: str, keyword: str, window_chars: int = 300) -> str:
    """
    Find a keyword in a 1-page OCRed PDF and return text context around it,
    printing each text block (not line/word) with its bounding box.
    """
    doc = fitz.open(pdf_path)
    page = doc[0]  # assume 1-page PDF
    blocks = page.get_text("dict")["blocks"]
    print (type(blocks))
    print("\n=== TEXT BLOCKS WITH BOUNDING BOXES ===\n")
    all_texts = []
    for b in blocks:
        if b.get("type", 0) != 0:
            continue  # skip images, drawings, etc.
        # Merge all lines/spans in the block into one string
        block_lines = []
        for l in b["lines"]:
            spans = l.get("spans", [])
            line_text = "".join(span.get("text", "") for span in spans).strip()
            if line_text:
                block_lines.append(line_text)
        if not block_lines:
            continue

        text_block = " ".join(block_lines).strip()
        bbox = b["bbox"]
        print(f"{text_block!r}  →  {bbox}")
        all_texts.append(text_block)

    # Join text for context search
    full_text = "\n".join(all_texts)
    norm_text = full_text.lower()
    keyword_lower = keyword.lower()

    match = re.search(re.escape(keyword_lower), norm_text)
    if not match:
        print("\n⚠️ Keyword not found — returning full text.")
        return full_text

    start, end = match.start(), match.end()
    context_start = max(0, start - window_chars)
    context_end = min(len(full_text), end + window_chars)
    context = full_text[context_start:context_end]
    return context.strip()


if __name__ == "__main__":
    pdf_path = "./examples/tela_sistema_1.pdf"  # adjust path
    keyword = "Data"
    window = 20

    context = extract_keyword_context(pdf_path, keyword, window)
    print("\n=== CONTEXT EXTRACTED ===\n")
    print(context)
