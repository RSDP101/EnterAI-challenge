1. Install runtime deps (recommended in a venv):

	pip install -r requirements.txt

2. Run the example dataset:

	python bbox_extractor.py 

Notes:
- pdf_parser.py implements the logic for sending an LLM call with the parsed text and the bounding box.
- business_logic.py implements the main logic explained below:

LOGIC:
- LOGIC 1: For the first 5 calls, pass the text and the bounding boxes of blocks of text to the LLM, and let it decide what is the best way.
- For the future calls: Obtain the center of the bounding box of the chosen response from the LLM. Then, return 
