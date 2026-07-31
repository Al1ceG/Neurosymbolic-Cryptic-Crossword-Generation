# Neurosymbolic-Cryptic-Crossword-Generation

This repo contains code to **generate** cryptic crossword clues and grids using LLMs.

## SET UP


### 1) Python setup

Create and activate a virtualenv (example):

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
```

Install runtime dependencies and models:

```bash
pip install openai omegaconf numpy python-Levenshtein torch transformers nltk spacy fasttext sentence-transformers z3-solver
python -m spacy download en_core_web_sm
```

Tested with the following versions:
~~~
Python 3.14.5
fasttext               0.9.3
nltk                   3.9.4
numpy                  2.4.6
omegaconf              2.3.0
openai                 2.37.0
python-Levenshtein     0.27.3
spacy                  3.8.13
torch                  2.12.0
transformers           5.8.1
~~~


Note: other parts of the project may require additional packages (e.g. evaluator plotting, semantic distance, etc.).

### 2) Download necessary files

1. Clone repository from Deits into the `dissertation/` directory:
git clone https://github.com/rdeits/CrypticCrosswords.jl.git

2. Now move the files provided in the deits_indicators directory of my repo into the corpora/indicators directory of the cloned repo

3. Download the cc.en.100.bin embeddings from HuggingFace and put in the `dissertation/` directory: 
https://huggingface.co/adorkin/fasttext-english-100-bin/blob/main/cc.en.100.bin



## CORRECTNESS

```bash
python -m scripts.correctness --model MODEL [--validator]
```

### Available Models

| Option | Model |
|--------|-------|
| `gpt52` | GPT-5.2 |
| `gpt55` | GPT-5.5 |
| `gpt4` | GPT-4o |
| `llama3` | Llama 3.3 70B Instruct |

### Examples

Generate clues without validation:

```bash
python -m scripts.correctness --model gpt55
```

Generate clues with validation:

```bash
python -m scripts.correctness --model gpt55 --validator
```

### Configuration

The following parameters can be adjusted near the top of `correctness.py`:

- `num_clues_of_each_type` – Number of clues generated for each clue type.
- `max_rewrites` – Maximum number of rewrite attempts when using validation.
- `clue_types` – List of cryptic clue types to generate.

### Output

Each run creates a directory under `logfiles/` named according to the selected model and whether validation was enabled (e.g. `gpt55_with_validator` or `gpt55_no_validator`).

Without validation, the output contains:

- `clues.txt` – Generated clues.
- `generation_stats.txt` – Total runtime and number of unique clues.
- Per-clue-type log files.

With validation, the output additionally includes:

- Successful and failed clue files.
- Detailed generation log files.


## QUALITY

The `quality.py` script evaluates the quality of the generated crossword clues by computing:

- Perplexity using DistilGPT-2, GPT-2, GPT-2 XL, and Llama 3.
- Semantic distance between each clue and its answer.
- Average clue length (characters and words).
- Web hits count and percentage.

Statistics are reported for each clue type and for the dataset as a whole.

### Usage

Run the script with:

```bash
python quality_stats.py --model <model_name>
```

where `<model_name>` is one of:

- `gpt52`
- `gpt55`
- `gpt4`
- `llama3`

To evaluate clues generated using the validator pipeline, add the `--validator` flag:

```bash
python quality_stats.py --model gpt55 --validator
```

To evaluate only correctly generated clues, add the `--correct_only` flag (you will need to make a clues_correct.txt file yourself, and put it in the same directory as the generated clues.txt file):

```bash
python quality_stats.py --model gpt55 --correct_only
```

The `--validator` and `--correct_only` flags can be used together.

### Output

The script prints the evaluation statistics to the terminal and saves them to the corresponding experiment directory as either `quality_stats` or `quality_stats_correct_only`.


## GRID GENERATION

The `grids.py` script runs the crossword grid generation experiments for all supported generation methods on a collection of clue sets. It evaluates each generated grid and records summary statistics.

### Clue Sets

The script expects clue sets to be located in:

```text
clue_sets/
```

The provided examples include both valid and intentionally invalid answers to evaluate generator robustness.

By default, the script runs experiments on:

- `gpt5_no_validator_1.txt`
- `gpt5_no_validator_2.txt`
- `gpt5_with_validator_1.txt`
- `gpt5_with_validator_2.txt`
- `the_times_1.txt`
- `the_times_2.txt`

### Usage

Run all grid generation methods:

```bash
python -m scripts.grids
```

or

```bash
python -m scripts.grids --method all
```

Run a specific method:

```bash
python -m scripts.grids --method llm
python -m scripts.grids --method genxword
python -m scripts.grids --method smt
python -m scripts.grids --method smt-llm-1-opt
python -m scripts.grids --method smt-llm-3-opt
python -m scripts.grids --method smt-llm-1-noopt
python -m scripts.grids --method smt-llm-3-noopt
```

### Output

Results are written to:

```text
logfiles/grid_generation_results/
```

One results file is created for each clue set. Each log contains:

- Runtime statistics.
- Grid density.
- Number of clues placed.
- Number of incorrect words in the generated grid.
- Whether a complete 13×13 grid was successfully generated.
- Average statistics across repeated runs where applicable.