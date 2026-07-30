# crossword-sat

SAT-based crossword generator using Z3, with an optional LLM warm-start via the OpenAI API.

Encoding follows: https://bohlender.pro/blog/generating-crosswords-with-sat-smt/

---

## Files

| File | Purpose |
|---|---|
| `crossword.py` | Main solver — generates crosswords and can extend existing grids |
| `crossword_tikz.py` | Renders a grid or solved crossword as a compilable LaTeX/TikZ file |
| `test_crossword.py` | pytest suite for the core encoding and pipeline |
| `test_suggest_grid.py` | Manual smoke-test for the LLM grid-suggestion feature |
| `clues/` | Example clue files (one `WORD clue text` per line) |

---

## Encoding rules

Each constraint block in the SAT encoding corresponds to a rule from the blog:

| Rule | Description |
|---|---|
| (1) | Word placement forces matching grid characters |
| (2) | Placed words must be bounded by empty cells |
| (3) | Each word is placed at most once; exactly once if selected |
| (4) | Every horizontal/vertical character sequence must be a word placement |
| (5) | All placed words must form a single connected component |

Quality is the **number of words placed**. `--min-quality N` requires at least N words in the solution.

---

## crossword.py — usage

```
python crossword.py (--words WORDS | --clues FILE)
                   [--size SIZE] [--min-quality N]
                   [--tex FILE] [--grid FILE]
                   [--llm] [--max-repairs N]
                   [--no-optimize] [--invert-weights]
```

### Word source (required, mutually exclusive)

| Flag | Description |
|---|---|
| `--words CAT,DOG,OAT` | Comma-separated word list |
| `--clues FILE` | Clues file — first token of each non-empty line is used as the word |

### Grid options

| Flag | Default | Description |
|---|---|---|
| `--size N` | 12 | Side length of the square grid |
| `--min-quality N` | 0 | Minimum number of words that must be placed |
| `--tex FILE` | — | Also write a LaTeX/TikZ file after solving |
| `--grid FILE` | — | Extend an existing `#`/letter grid — locked letters are treated as soft constraints |

### LLM warm-start

| Flag | Default | Description |
|---|---|---|
| `--llm` | off | Ask GPT-4o for an initial grid layout, then hand it to the SAT solver |
| `--max-repairs N` | 1 | Maximum validation-error repair loops sent back to the LLM |

Requires `OPENAI_API_KEY` in the environment.

### Solver options

| Flag | Default | Description |
|---|---|---|
| `--no-optimize` | off | Use a plain `Solver` instead of `Optimize` (faster; ignores soft-constraint weights) |
| `--invert-weights` | off | Invert soft-constraint weights — prefer keeping shorter existing words (default: prefer longer) |

### Examples

```bash
# Generate from a word list
python crossword.py --words CAT,DOG,COT,OAT --size 5 --min-quality 3

# Generate from a clues file and write a PDF-ready TikZ file
python crossword.py --clues clues/gpt5_clues1.txt --size 13 --min-quality 15 --tex puzzle.tex

# LLM warm-start with up to 3 repair rounds, then extend with the SAT solver
python crossword.py --clues clues/times_clues1.txt --size 13 --min-quality 18 \
                    --llm --max-repairs 3

# Extend an existing grid file
python crossword.py --clues clues/times_clues1.txt --size 13 --grid puzzle.txt
```

---

## crossword_tikz.py — usage

Renders a grid or a freshly solved crossword as a standalone LaTeX/TikZ document.

```
python crossword_tikz.py (--grid FILE | --words WORDS | --clues FILE)
                         [--size SIZE] [--min-quality N]
                         [--cell-size CM] [--output FILE]
```

| Flag | Default | Description |
|---|---|---|
| `--grid FILE` | — | Render a plain-text `#`/letter grid directly (no solving) |
| `--words` / `--clues` | — | Solve first, then render |
| `--size N` | 12 | Grid side length (solve mode only) |
| `--min-quality N` | 0 | Minimum words placed (solve mode only) |
| `--cell-size CM` | 1.0 | Cell size in centimetres |
| `--output FILE`, `-o` | `crossword.tex` | Output file path |

```bash
# Render an existing grid file
python crossword_tikz.py --grid puzzle.txt -o puzzle.tex

# Solve and render in one step
python crossword_tikz.py --clues clues/gpt5_clues1.txt --size 13 --min-quality 10 -o out.tex

# Compile to PDF
pdflatex out.tex
```

---

## Tests

```bash
# Core pytest suite (no API key required)
python -m pytest test_crossword.py -v

# LLM smoke-test (requires OPENAI_API_KEY)
OPENAI_API_KEY=sk-... python test_suggest_grid.py
```

---

## Dependencies

```
z3-solver
openai        # only needed for --llm
pytest        # only needed for tests
```

Install into a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install openai pytest
```
