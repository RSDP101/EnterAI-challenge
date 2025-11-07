## Quick run instructions

1. Install runtime deps (recommended in a venv):

	pip install -r requirements.txt

2. Add yours samples and a dataset.json file containing their label schemas. You can follow the format specified in examples/dataset.json for running in series.

3. python3 solution.py 

You'll see a file output.json containing the filled up schemas.

## Explanation:

The algorithm attempts to learn the "average" position of the boxes for each particular keyword in our scheme, by calling LLM. In general terms, we segment the text into semantically-meaningful boxes, and expect the algorithm to learn a correspondence between keywords and box-positions, which would enable it to uncover a pattern for keyword's answers without calling an LLM.

The whole learning algorithm is explained below for a fixed label:

1. [LLM EXTRACTION] For the first 3 steps, the LLM is called directly by passing the segmented boxes obtained. Then, the centers of the returned boxes for each keyword are stored in memory. With time, the model learns the average representation of the mean center of a particular keyword. 

2. [GEOMETRIC EXTRACTION] In the future steps, it will assume the mean-center is a "good" estimate of the correct box position, and then will pick the box that is closest to this mean-estimate. If less than 50% of the fields are found 

