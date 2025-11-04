(The file `/Users/rodri/Documents/EnterAI-challenge/README.md` exists, but is empty)
Project: EnterAI-challenge

Quick run instructions

1. Install runtime deps (recommended in a venv):

	pip install pdfplumber rapidfuzz

2. Run the example dataset:

	python run_examples.py --dataset examples/dataset.json

Notes:
- The extractor will call an LLM only if a label is unseen (no examples stored yet). After the registry has at least one example for a label, heuristics (anchors/regex/positional) are used.
- If you want to enable the OpenAI-based LLM seeding step, set OPENAI_API_KEY in your environment.
