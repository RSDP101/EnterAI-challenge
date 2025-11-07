import fitz  # PyMuPDF
# pdf_parser.py
from dataclasses import dataclass
from typing import List, Tuple
import json
from openai import OpenAI
import os
from typing import Dict, List, Optional

# optional LLM
USE_LLM = bool(os.getenv("OPENAI_API_KEY"))
if USE_LLM:
    client = OpenAI()

def llm_extract(label: str, schema: Dict[str, str], lines: list[Dict]) -> Dict[str, Optional[Dict]]:
    context = json.dumps(lines[:100], ensure_ascii=False)

    system_prompt = """
    You are a data extraction assistant.
    You receive a list of OCR text lines with coordinates from a PDF.
    For each field in the given schema, find the text that best matches it
    and return a JSON object containing the field value and its bounding box.

    The output must be strictly JSON of the form:
    {
      "<field_name>": {
        "value": "<value>",
        "page": <page_number>,
        "bbox": [x0, y0, x1, y1]
      },
      ...
    }
    Return null for fields you cannot find.
    """

    prompt = {"label": label, "schema": schema, "lines": lines[:100]}
    rsp = client.chat.completions.create(
        model="gpt-5-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)}
        ]
    )

    content = rsp.choices[0].message.content.strip()
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        print("⚠️ Invalid JSON:\n", content)
        return {k: None for k in schema.keys()}

def parse_pdf(pdf_bytes: bytes):
    from io import BytesIO
    doc = fitz.open(stream=BytesIO(pdf_bytes), filetype="pdf")
    lines = []
    for page_num, page in enumerate(doc):
        for block in page.get_text("blocks"):  # (x0, y0, x1, y1, text, block_no, ...)
            x0, y0, x1, y1, text, *_ = block
            if text.strip():
                lines.append({
                    "page": page_num + 1,
                    "text": text.strip(),
                    "bbox": [x0, y0, x1, y1]
                })
    return lines

if __name__ == "__main__":
    import json
    label = "carteira_oab"  # e.g. "Invoice", "Contract", "Customer_Info"
    schema ={
        "nome": "Nome do profissional, normalmente no canto superior esquerdo da imagem",
        "inscricao": "Número de inscrição do profissional",
        "seccional": "Seccional do profissional",
        "subsecao": "Subseção à qual o profissional faz parte",
        "categoria": "Categoria, pode ser ADVOGADO, ADVOGADA, SUPLEMENTAR, ESTAGIARIO, ESTAGIARIA",
        "endereco_profissional": "Endereço do profissional",
        "situacao": "Situação do profissional, normalmente no canto inferior direito."
      }
    pdf_path = "./examples/oab_2.pdf"  # <-- change this path

    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()

    lines = parse_pdf(pdf_bytes)
    print(f"Extracted {len(lines)} text blocks from PDF.")

    # === OPTIONAL: PRINT FIRST FEW LINES ===
    for l in lines[:5]:
        print(l)

    # === RUN LLM EXTRACTION ===
    if USE_LLM:
        result = llm_extract(label, schema, lines)
        print("\n=== LLM Output ===")
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print("⚠️ OPENAI_API_KEY not set, skipping LLM extraction.")