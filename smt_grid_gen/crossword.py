"""
crossword.py — SAT-based crossword generator using Z3.

Encoding follows: https://bohlender.pro/blog/generating-crosswords-with-sat-smt/
Each constraint block is annotated with the corresponding rule from the blog:
  Rule (1): word placement forces matching grid characters
  Rule (2): placed words must be bounded by empty cells
  Rule (3): each word is placed at most once; exactly once if selected
  Rule (4): every horizontal/vertical character sequence must be a word placement
  Rule (5): all placed words must form a single connected component

Usage:
  python crossword.py --words CAT,DOG,COT,OAT --size 5 --min-quality 0
"""

import argparse
import itertools
import os
import sys
import time
from itertools import product


# Each call to create_variables needs a unique EnumSort name; Z3 raises an error
# if the same name is declared twice in the same context.
_sort_counter = itertools.count()

from z3 import (
    And, AtMost, Bool, Const, EnumSort, Implies, Not, Optimize, Or, PbGe, Solver, is_true,
    sat,
)

def find_words_with_most_common_letters(words: list[str], n: int) -> list[str]:
    """
    Find the n words with the most common letters.

    Parameters
    ----------
    words : list[str]
        List of words to analyze.
    n : int
        Number of words to return.

    Returns
    -------
    list[str]
        The n words with the most common letters, sorted by frequency.
    """
    from collections import Counter

    letter_counts = Counter(letter for word in words for letter in word)
    word_scores = {word: sum(letter_counts[letter] for letter in set(word)) for word in words}
    sorted_words = sorted(words, key=lambda w: word_scores[w]/len(w), reverse=True)
    return sorted_words[:n]


def validate_placements(
    placements: list[tuple],
    words: list[str],
    size: int,
) -> list[str]:
    """
    Validate a list of (word, x, y, orientation) placement tuples.

    Checks:
    - every word comes from the supplied word list
    - orientation is 'horizontal' or 'vertical'
    - starting cell is inside the grid
    - the full word fits within the grid boundary
    - no word appears more than once
    - no two words place different letters at the same cell

    Returns a (possibly empty) list of error message strings.
    """
    upper_words = {w.upper() for w in words}
    errors: list[str] = []

    for word, x, y, orientation in placements:
        if word not in upper_words:
            errors.append(f"UNKNOWN WORD: {word!r}")

        if orientation not in ("horizontal", "vertical"):
            errors.append(f"BAD ORIENTATION for {word!r}: {orientation!r}")

        if not (0 <= x < size and 0 <= y < size):
            errors.append(f"OUT OF BOUNDS start for {word!r}: ({x}, {y})")

        if orientation == "horizontal" and x + len(word) > size:
            errors.append(
                f"{word!r} overflows horizontally: "
                f"x={x}, len={len(word)}, size={size}"
            )
        if orientation == "vertical" and y + len(word) > size:
            errors.append(
                f"{word!r} overflows vertically: "
                f"y={y}, len={len(word)}, size={size}"
            )

    seen: set[str] = set()
    for word, *_ in placements:
        if word in seen:
            errors.append(f"DUPLICATE PLACEMENT: {word!r}")
        seen.add(word)

    cell_chars: dict[tuple, str] = {}
    for word, x, y, orientation in placements:
        for k, ch in enumerate(word):
            pos = (x + k, y) if orientation == "horizontal" else (x, y + k)
            if pos in cell_chars and cell_chars[pos] != ch:
                errors.append(
                    f"CHARACTER CONFLICT at {pos}: "
                    f"{cell_chars[pos]!r} vs {ch!r} (word={word!r})"
                )
            cell_chars[pos] = ch

    return errors


def remove_invalid_placements(
    placements: list[tuple],
    words: list[str],
    size: int,
) -> list[tuple]:
    """
    Return a copy of placements with every invalid entry removed.

    Removals are applied in this order:
    1. Placements whose word is not in the supplied word list.
    2. Placements with an unrecognised orientation.
    3. Placements whose starting cell or span falls outside the grid.
    4. Duplicate placements of the same word (first occurrence kept).
    5. Placements that create a character conflict with an already-accepted
       placement (the later conflicting placement is dropped).
    """
    upper_words = {w.upper() for w in words}
    kept: list[tuple] = []
    seen_words: set[str] = set()
    cell_chars: dict[tuple, str] = {}

    for entry in placements:
        word, x, y, orientation = entry

        # 1. Unknown word
        if word not in upper_words:
            continue

        # 2. Bad orientation
        if orientation not in ("horizontal", "vertical"):
            continue

        # 3. Out of bounds / overflow
        if not (0 <= x < size and 0 <= y < size):
            continue
        if orientation == "horizontal" and x + len(word) > size:
            continue
        if orientation == "vertical" and y + len(word) > size:
            continue

        # 4. Duplicate word
        if word in seen_words:
            continue

        # 5. Character conflict with a previously accepted placement
        cells = {}
        conflict = False
        for k, ch in enumerate(word):
            pos = (x + k, y) if orientation == "horizontal" else (x, y + k)
            if pos in cell_chars and cell_chars[pos] != ch:
                conflict = True
                break
            cells[pos] = ch

        if conflict:
            continue

        # Placement is valid — accept it
        cell_chars.update(cells)
        seen_words.add(word)
        kept.append(entry)

    return kept



## Call an LLM to suggest a grid which place n words from a list of words, with a minimum quality of m.
# The grid is of size s x s.
def suggest_grid(words: list[str], s: int, m: int, max_repairs: int = 1) -> list[tuple]:
    """
    Suggest a grid which place n words from a list of words, with a minimum quality of m. 
    The grid is of size s x s.

    Parameters
    ----------
    words : list[str]
        List of words to place in the grid.
    s : int
        Size of the grid (s x s).
    m : int
        Minimum quality (number of words placed).
    max_repairs : int
        Maximum number of repair attempts to make if the initial grid is invalid.

    Returns
    -------
    list[tuple]
        List of (word, x, y, orientation) tuples where orientation is 'horizontal' or 'vertical'.
    """
    from openai import OpenAI

    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

    sorted_words = find_words_with_most_common_letters(words, m)

    # system_prompt = (
    #     "You are a crossword construction assistant. "
    #     "Given a word list and a grid size, return a crossword layout as a plain-text grid. "
    #     "Rules: words may intersect only where they share the same letter; "
    #     "no two words may be parallel and adjacent; every word must fit within the grid. "
    #     "Represent empty cells with '#' and filled cells with their uppercase letter. "
    #     "Return ONLY the grid — no explanations, no markdown fences, no extra whitespace. "
    #     "Every row must be exactly s characters wide. You do not have to place all of the words."
    #     "If you cannot place a word you should skip it."
    #     f"Example for a 4×4 grid: \n"
    #     "CAT#\n"
    #     "#T##\n"
    #     "PET#\n"
    #     "####"
    # )

    system_prompt = (
        "You are a crossword construction assistant. "
        "Given a word list and a grid size, return a crossword layout as a plain-text grid. "
        "Rules: words may intersect only where they share the same letter; "
        "no two words may be parallel and adjacent; every word must fit within the grid. "
        "Represent empty cells with '#' and filled cells with their uppercase letter. "
        "Return ONLY the grid — no explanations, no markdown fences, no extra whitespace. "
        "Every row must be exactly s characters wide. You do not have to place all of the words."
        "If you cannot place a word you should skip it."
        f"Example for a 4×4 grid: \n"
        "CAT#\n"
        "#T##\n"
        "PET#\n"
        "####"
    )



    user_prompt = (
        f"Grid size: {s}×{s}\n"
        f"Place at least {m} of these words: {', '.join(w.upper() for w in sorted_words)}\n"
        "Return only the grid."
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user",   "content": user_prompt},
    ]

    for attempt in range(1 + max_repairs):
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            temperature=0.2,
        )

        raw = response.choices[0].message.content.strip()

        # Strip markdown fences if the model added them despite instructions
        if raw.startswith("```"):
            raw = "\n".join(
                line for line in raw.splitlines()
                if not line.startswith("```")
            ).strip()

        print(f"{'Initial' if attempt == 0 else f'Repair {attempt}'} grid:\n{raw}\n")

        # Strip markdown fences if the model added them despite instructions
        if raw.startswith("```"):
            raw = "\n".join(
                line for line in raw.splitlines()
                if not line.startswith("```")
            ).strip()

        grid, nrows, ncols, placements = parse_grid(raw)
        errors = validate_placements(placements, words, s)

        if not errors:
            print(f"Grid is valid after {'initial attempt' if attempt == 0 else f'{attempt} repair(s)'}.")
            break

        print(f"Validation errors ({len(errors)}):")
        for e in errors:
            print(f"  {e}")

        if attempt == max_repairs:
            print("Max repairs reached — returning best available placements.")
            break

        # Append the assistant's reply and a repair request to the conversation
        error_list = "\n".join(f"- {e}" for e in errors)
        messages.append({"role": "assistant", "content": raw})
        messages.append({
            "role": "user",
            "content": (
                f"The grid has the following errors, please fix them and return the corrected grid:\n"
                f"{error_list}\n\n"
                "Return only the corrected grid, no explanations."
            ),
        })

    # placements = remove_invalid_placements(placements, words, s)
    return placements


# ---------------------------------------------------------------------------
# Grid parsing  (for --grid mode)
# ---------------------------------------------------------------------------

def parse_grid(text: str) -> tuple[list[list], int, int, list[tuple]]:
    """
    Parse a plain-text crossword grid.

    Each character should be either a letter (white cell — stored as uppercase)
    or '#' (black/empty cell — stored as None).  Lines of different lengths are
    right-padded with '#' to the width of the longest line.

    Returns (grid, nrows, ncols, placements) where placements is the list of
    (word, x, y, orientation) tuples extracted from the grid.
    """
    lines = [line.rstrip("\n") for line in text.splitlines() if line.strip()]
    if not lines:
        raise ValueError("Grid text is empty")
    ncols = max(len(line) for line in lines)
    nrows = len(lines)
    grid = []
    for line in lines:
        row = []
        for i in range(ncols):
            ch = line[i] if i < len(line) else "#"
            row.append(None if ch == "#" else ch.upper())
        grid.append(row)
    return grid, nrows, ncols, extract_words(grid, nrows, ncols)


def extract_words(grid: list[list], nrows: int, ncols: int) -> list[tuple]:
    """
    Extract every contiguous letter sequence of length ≥ 2 from a parsed grid.

    Scans all rows (horizontal) then all columns (vertical).  Each run of
    non-None cells whose length is at least 2 is returned as a placement tuple.

    Parameters
    ----------
    grid : list[list]
        The grid returned by parse_grid (None = black cell, str = letter).
    nrows, ncols : int
        Grid dimensions returned by parse_grid.

    Returns
    -------
    list of (word, x, y, orientation) where
        word        – the letter sequence as an uppercase string
        x           – starting column
        y           – starting row
        orientation – 'horizontal' or 'vertical'
    """
    placements = []

    # Horizontal passes
    for row in range(nrows):
        col = 0
        while col < ncols:
            if grid[row][col] is not None:
                start = col
                while col < ncols and grid[row][col] is not None:
                    col += 1
                word = "".join(grid[row][c] for c in range(start, col))
                if len(word) >= 2:
                    placements.append((word, start, row, "horizontal"))
            else:
                col += 1

    # Vertical passes
    for col in range(ncols):
        row = 0
        while row < nrows:
            if grid[row][col] is not None:
                start = row
                while row < nrows and grid[row][col] is not None:
                    row += 1
                word = "".join(grid[r][col] for r in range(start, row))
                if len(word) >= 2:
                    placements.append((word, col, start, "vertical"))
            else:
                row += 1

    return placements


def placements_to_grid(
    placements: list[tuple], nrows: int, ncols: int
) -> list[list]:
    """
    Convert a list of (word, x, y, orientation) placements to a character grid.

    The inverse of extract_words: builds the same list-of-lists format that
    parse_grid produces (None for empty cells, uppercase letter for filled cells).

    Parameters
    ----------
    placements : list of (word, x, y, orientation)
        Word placements as returned by interpret, suggest_grid, etc.
    nrows, ncols : int
        Grid dimensions.  Every placed letter must fit within these bounds.

    Returns
    -------
    grid : list[list]
        grid[row][col] is a single uppercase letter str, or None if empty.

    Raises
    ------
    ValueError
        If two placements assign different letters to the same cell.
    """
    grid = [[None] * ncols for _ in range(nrows)]

    for word, x, y, orientation in placements:
        for k, ch in enumerate(word):
            row = y + k if orientation == "vertical"   else y
            col = x + k if orientation == "horizontal" else x
            existing = grid[row][col]
            if existing is not None and existing != ch:
                raise ValueError(
                    f"Character conflict at ({col}, {row}): "
                    f"existing {existing!r} vs {ch!r} from {word!r}"
                )
            grid[row][col] = ch

    return grid
# ---------------------------------------------------------------------------

def max_distance(size: int) -> int:
    """Upper bound on the number of steps needed for any non-empty cell to
    reach the connected-component start cell via adjacent non-empty neighbours.

    A longest simple path on an n×n grid visits at most n² cells, but a
    tighter practical bound is 2*n - 1 (the longest Manhattan path across the
    grid). The blog uses a heuristic in this spirit; we use 2*size - 1.
    """
    return 2 * size - 1


# ---------------------------------------------------------------------------
# Variable creation
# ---------------------------------------------------------------------------

def create_variables(words: list[str], size: int):
    """
    Create all Z3 variables and constants needed for the encoding.

    Returns
    -------
    placement_vars : dict[str, list[list[list[BoolRef]]]]
        placement_vars[word][y][x][o] is True  ⟺  `word` is placed at
        column x, row y, with orientation o (0 = horizontal, 1 = vertical).
        Blog: "a variable w_{x,y,o} for each position (x,y) and orientation o"
    word_selection : dict[str, BoolRef]
        word_selection[word] is True  ⟺  `word` is included in the crossword.
        Blog: "a variable w_selected for each word w"
    chars_enc : dict[str, ExprRef]
        Maps each character to its Z3 finite-domain constant.
    char_empty : ExprRef
        The distinguished 'empty' constant (represents an unoccupied cell).
    grid : list[list[ExprRef]]
        grid[y][x] is a finite-domain Z3 variable holding the character at
        column x, row y.
        Blog: "an array of char_sort variables for the grid"
    """
    # -- Placement variables: w_{x,y,o} -----------------------------------------------
    # Blog: "a variable w_{x,y,o} for each position (x,y) within the grid and
    #        orientation o ∈ {horizontal, vertical}"
    placement_vars = {
        word: [
            [
                [Bool(f"{word}_{x},{y}_{'h' if o == 0 else 'v'}") for o in range(2)]
                for x in range(size)
            ]
            for y in range(size)
        ]
        for word in words
    }

    # -- Word-selection variables: w_selected ------------------------------------------
    # Blog: "a variable w_selected for each word w"
    word_selection = {word: Bool(f"{word}_selected") for word in words}

    # -- Character finite-domain constants ---------------------------------------------
    # Blog: "create a constant c for each distinct character … plus a special
    #        'empty' character"
    chars = sorted(set("".join(words)))
    char_sort, char_constants = EnumSort(f"Chars_{next(_sort_counter)}", chars + ["empty"])
    char_empty = char_constants[-1]
    chars_enc = {c: sym for c, sym in zip(chars, char_constants)}

    # -- Grid variables: grid[y][x] of type char_sort ----------------------------------
    # Blog: "represent the characters in the grid as an array of char_sort variables"
    grid = [
        [Const(f"grid_{x}_{y}", char_sort) for x in range(size)]
        for y in range(size)
    ]

    return placement_vars, word_selection, chars_enc, char_empty, grid


# ---------------------------------------------------------------------------
# Constraint encoding
# ---------------------------------------------------------------------------

def encode_problem(words: list[str], additional_words: list[str], size: int, min_quality: int):
    """
    Encode the crossword-generation problem as a Z3 formula.

    Returns
    -------
    constraints : list[BoolRef]
        All constraints; pass directly to a Z3 Solver.
    placement_vars : dict
        The placement variable dict (needed later to interpret a model).
    """
    placement_vars, word_selection, chars_enc, char_empty, grid = create_variables(
        words + additional_words, size
    )

    # possible_placements[y][x][o] — all placement vars whose word *starts* at
    # (x, y) with orientation o.  Populated during Rule (1)/(2) below and
    # consumed in Rule (4).
    possible_placements = [
        [[[] for _o in range(2)] for _x in range(size)] for _y in range(size)
    ]

    constraints = []

    # -----------------------------------------------------------------------
    # Rules (1) and (2): word placement ↔ grid characters + boundary cells
    # -----------------------------------------------------------------------
    # Blog Rule (1): "w_{x,y,o} → grid_{x,y} = c_0 ∧ … ∧ grid_{x+k,y} = c_k"
    # Blog Rule (2): "w_{x,y,o} → cell before word = empty ∧ cell after word = empty"
    for word in words+additional_words:
        word_placement_vars = []   # all placement vars for this word (used in Rule 3)

        for y, x in product(range(size), range(size)):

            # ---- Horizontal placement ----
            if x + len(word) <= size:
                pvar = placement_vars[word][y][x][0]
                word_placement_vars.append(pvar)
                possible_placements[y][x][0].append(pvar)

                # Rule (1): placement forces matching characters
                cell_chars = grid[y][x : x + len(word)]
                match_expr = And([chars_enc[c] == sym for c, sym in zip(word, cell_chars)])
                constraints.append(Implies(pvar, match_expr))

                # Rule (2): cells immediately before and after must be empty
                boundary = []
                if x - 1 >= 0:
                    boundary.append(grid[y][x - 1] == char_empty)
                if x + len(word) < size:
                    boundary.append(grid[y][x + len(word)] == char_empty)
                if boundary:
                    constraints.append(Implies(pvar, And(boundary)))

            # ---- Vertical placement ----
            if y + len(word) <= size:
                pvar = placement_vars[word][y][x][1]
                word_placement_vars.append(pvar)
                possible_placements[y][x][1].append(pvar)

                # Rule (1): placement forces matching characters (vertical)
                cell_chars = [grid[y + k][x] for k in range(len(word))]
                match_expr = And([chars_enc[c] == sym for c, sym in zip(word, cell_chars)])
                constraints.append(Implies(pvar, match_expr))

                # Rule (2): cells immediately above and below must be empty
                boundary = []
                if y - 1 >= 0:
                    boundary.append(grid[y - 1][x] == char_empty)
                if y + len(word) < size:
                    boundary.append(grid[y + len(word)][x] == char_empty)
                if boundary:
                    constraints.append(Implies(pvar, And(boundary)))

        # -------------------------------------------------------------------
        # Rule (3): at most one placement per word; at least one if selected
        # -------------------------------------------------------------------
        # Blog Rule (3): "each word may only be placed once"
        #   AtMost(*vars, 1)      → at most one placement variable is True
        #   word_selected → Or(vars) → if word is selected, some placement is True
        constraints.append(AtMost(*word_placement_vars, 1))
        constraints.append(Implies(word_selection[word], Or(word_placement_vars)))

    # -----------------------------------------------------------------------
    # Rule (4): every non-trivial character sequence must be a word placement
    # -----------------------------------------------------------------------
    # Blog Rule (4): "every horizontal and vertical contiguous sequence of
    #   characters in the grid must correspond to a word placement"
    # Strategy: the start of a sequence (first non-empty cell preceded by empty
    # or grid edge, followed by another non-empty cell) must be exactly one of
    # the placement variables that start at that position in that orientation.
    for y, x in product(range(size), range(size)):

        # ---- Horizontal sequence start at (x, y) ----
        if x + 1 < size:
            prev_empty = (grid[y][x - 1] == char_empty) if x - 1 >= 0 else True
            seq_start = And(prev_empty, grid[y][x] != char_empty, grid[y][x + 1] != char_empty)
            constraints.append(seq_start == Or(possible_placements[y][x][0]))

        # ---- Vertical sequence start at (x, y) ----
        if y + 1 < size:
            prev_empty = (grid[y - 1][x] == char_empty) if y - 1 >= 0 else True
            seq_start = And(prev_empty, grid[y][x] != char_empty, grid[y + 1][x] != char_empty)
            constraints.append(seq_start == Or(possible_placements[y][x][1]))

    # -----------------------------------------------------------------------
    # Rule (5): all placed characters form a single connected component
    # -----------------------------------------------------------------------
    # Blog Rule (5): "the placed words must form a single connected component"
    #
    # Approach: pick the uppermost-leftmost non-empty cell as the CC "start".
    # Unroll a BFS reachability relation up to max_distance(size) steps.
    # Every non-empty cell must reach the start within that many steps.
    #
    # Variables:
    #   ccStartRow[y]    — True iff row y is the first non-empty row
    #   ccStart[y][x]    — True iff (x,y) is the CC start cell
    #   inCc[y][x][i]    — True iff (x,y) can reach the CC start in ≤ i steps

    md = max_distance(size)

    cc_start_row = [Bool(f"ccStartRow_{y}") for y in range(size)]
    cc_start = [[Bool(f"ccStart_{x},{y}") for x in range(size)] for y in range(size)]
    in_cc = [
        [[Bool(f"reach{i}_{x},{y}") for i in range(md + 1)] for x in range(size)]
        for y in range(size)
    ]

    for y in range(size):
        # ccStartRow[y]: row y is the first non-empty row
        #   Blog: "ccStart_y must be True for the first row that is not empty"
        not_in_prev_rows = And([Not(cc_start_row[i]) for i in range(y)])
        any_in_cur_row = Or([grid[y][x] != char_empty for x in range(size)])
        constraints.append((And(any_in_cur_row, not_in_prev_rows)) == cc_start_row[y])

        for x in range(size):
            # ccStart[y][x]: (x,y) is the uppermost-leftmost non-empty cell
            #   Blog: "ccStart_{x,y} must be True for the leftmost non-empty
            #          cell in the CC start row"
            not_in_prev_pos = And([Not(cc_start[y][i]) for i in range(x)])
            in_cur_pos = grid[y][x] != char_empty
            constraints.append(
                (And(cc_start_row[y], in_cur_pos, not_in_prev_pos)) == cc_start[y][x]
            )

            # Reachability step 0: only the start cell reaches itself in 0 steps
            #   Blog: "reach_{0,x,y} = ccStart_{x,y}"
            constraints.append(cc_start[y][x] == in_cc[y][x][0])

            # Reachability step i: (x,y) reaches start in i steps iff
            #   it reaches start in i-1 steps, OR an adjacent non-empty cell does
            #   Blog: "reach_{i,x,y} → grid_{x,y} ≠ empty ∧
            #          (reach_{i-1,x,y} ∨ ⋁_{(nx,ny)} reach_{i-1,nx,ny})"
            for i in range(1, md + 1):
                reasons = [in_cc[y][x][i - 1]]
                if x - 1 >= 0:
                    reasons.append(in_cc[y][x - 1][i - 1])
                if x + 1 < size:
                    reasons.append(in_cc[y][x + 1][i - 1])
                if y - 1 >= 0:
                    reasons.append(in_cc[y - 1][x][i - 1])
                if y + 1 < size:
                    reasons.append(in_cc[y + 1][x][i - 1])
                constraints.append(
                    Implies(in_cc[y][x][i], And(grid[y][x] != char_empty, Or(reasons)))
                )

            # # Every non-empty cell must reach the CC start within max_distance steps
            # #   Blog: "all non-empty grid entries must reach the CC start"
            constraints.append(
                Implies(grid[y][x] != char_empty, in_cc[y][x][md])
            )

    # -----------------------------------------------------------------------
    # Quality criterion
    # -----------------------------------------------------------------------
    # quality = number of selected words ≥ min_quality
    # PbGe encodes a pseudo-Boolean ≥ constraint natively in Z3.
    if min_quality > 0:
        constraints.append(
            PbGe([(word_selection[word], 1) for word in words], min_quality)
        )

    return constraints, placement_vars, chars_enc, grid


# ---------------------------------------------------------------------------
# Grid enforcement  (fill mode: pin existing cells after encode_problem)
# ---------------------------------------------------------------------------

def enforce_grid(chars_enc: dict,
                z3_grid: list[list],
                placements: list[tuple],
                nrows: int,
                ncols: int) -> list:
    """
    Build one Z3 constraint per placement that pins every cell of that word.

    For each (word, x, y, orientation) placement a single And(...) constraint
    is produced covering all cells of the word:

        And(z3_grid[y][x] == chars_enc[word[0]],
            z3_grid[y][x+1] == chars_enc[word[1]], ...)

    Cells that appear in no placement (isolated single letters) each get their
    own individual constraint so nothing is left unconstrained.

    Returns a list of constraints — one per placement plus one per isolated cell.
    """
    constraints = []

    # Track which cells are covered by a placement
    covered: set[tuple] = set()
    extra_words = [];

    for word, x, y, orientation in placements:
        cell_constraints = []
        for k, ch in enumerate(word):
            row = y + k if orientation == "vertical" else y
            col = x + k if orientation == "horizontal" else x
            if row >= nrows or col >= ncols:
                continue
            if ch in chars_enc:
                cell_constraints.append(z3_grid[row][col] == chars_enc[ch])
                covered.add((row, col))
        if cell_constraints:
            constraints.append(And(cell_constraints) if len(cell_constraints) > 1
                                else cell_constraints[0])
            extra_words.append(word)
            # print(f"Enforcing placement: {word} at ({x}, {y}) {orientation} with constraints: {cell_constraints}")

    return constraints, extra_words


# ---------------------------------------------------------------------------
# Solve
# ---------------------------------------------------------------------------

def solve(constraints: list, extra_constraints: list | None = None, words: list[str] | None = None, optimize: bool = True, invert_weights: bool = True):
    """
    Feed constraints to Z3 and return a satisfying model, or None if UNSAT.

    extra_constraints are tracked individually with assert_and_track so that
    unsat_core() returns a meaningful subset when the problem is infeasible.
    If the full problem is UNSAT, conflicting extra_constraints are removed one
    by one until the base problem becomes satisfiable (or nothing remains).
    """
    from z3 import Bool as Z3Bool

    solver = Optimize() if optimize else Solver()
    solver.add(constraints)

    if extra_constraints is None:
        result = solver.check()
        return solver.model() if result == sat else None
    
    # maximum length of words to use as weights for soft constraints
    max_word_length = max(len(w) for w in words) if words else 1
    costs = []
    if invert_weights:
        costs = [max_word_length + 1 - len(w) for w in words] if words else [1] * len(extra_constraints)
    else:
        costs = [len(w) for w in words] if words else [1] * len(extra_constraints)

    if(optimize):
        for i in range(len(extra_constraints)):
            solver.add_soft(extra_constraints[i], costs[i])
        result = solver.check()
        if result == sat:
            # print("objectives =", solver.objectives())
            return solver.model()
        return None

    else:
        push_count=0;
        pop_count=0;
        for i in range(len(extra_constraints)):
            solver.push()
            push_count += 1
            solver.add(extra_constraints[i])
        while push_count > pop_count:
            result = solver.check()
            if result == sat:
                return solver.model() 
            else:
                solver.pop()
                pop_count += 1
        return None





# ---------------------------------------------------------------------------
# Interpret model
# ---------------------------------------------------------------------------

def interpret(model, placement_vars: dict, size: int) -> list[tuple]:
    """
    Extract the word placements from a satisfying Z3 model.

    Returns a list of (word, x, y, orientation) tuples where orientation is
    'horizontal' or 'vertical'.
    """
    placements = []
    for word, rows in placement_vars.items():
        for y in range(size):
            for x in range(size):
                for o, label in enumerate(["horizontal", "vertical"]):
                    var = rows[y][x][o]
                    if is_true(model[var]):
                        placements.append((word, x, y, label))
    return placements


# ---------------------------------------------------------------------------
# Pretty-print
# ---------------------------------------------------------------------------

def print_placement(placements: list[tuple], size: int):
    """
    Render the crossword as an ASCII grid.  '#' marks empty cells.
    """
    result = ""
    grid = [["#" for _ in range(size)] for _ in range(size)]
    for word, x, y, orientation in placements:
        for k, ch in enumerate(word):
            if orientation == "horizontal":
                grid[y][x + k] = ch
            else:
                grid[y + k][x] = ch

    # col_nums = "".join(str(i % 10) for i in range(size))
    # result += f"   {col_nums}\n"
    # result += f"  +{'-' * size}+\n"
    for r, row in enumerate(grid):
        result += f"{''.join(row)}\n"
    # result += f"  +{'-' * size}+\n"
    return result


# ---------------------------------------------------------------------------
# Top-level entry point
# ---------------------------------------------------------------------------

def generate_crossword(words: list[str], size: int, min_quality: int,
                       tex_path: str | None = None,
                       placements: list[tuple] | None = None,
                       optimize: bool = True,
                       invert_weights: bool = False) -> None:
    """
    Full pipeline: encode → solve → interpret → print.
    If tex_path is given, also write a LaTeX/TikZ file to that path.
    """

    additional_words = []
    # get grid to extend
    if placements is not None:
        # print(f"Extending grid …")
        additional_words = [w for w, _, _, _ in placements]
        
    
    # Deduplicate while preserving a deterministic order
    words = list(dict.fromkeys(w.upper() for w in words))

    assert size > 0, f"Grid size ({size}) must be positive"
    longest = max(words, key=len)
    assert size >= len(longest), (
        f'"{longest}" ({len(longest)} chars) does not fit in a grid of size {size}'
    )
    assert min_quality >= 0, "min_quality must be non-negative"

    print(f"Encoding problem: {len(words)} words, {size}×{size} grid, "
          f"min-quality={min_quality} …")

    t0 = time.perf_counter()
    constraints, placement_vars, chars_enc, z3_grid = encode_problem(words, additional_words, size, min_quality)
    if(placements is not None):
        if(not optimize):
            placements = remove_invalid_placements(placements, words, size)
            
        extra_constraints, extra_words = enforce_grid(chars_enc, z3_grid, placements, size, size)

    encode_secs = time.perf_counter() - t0
    print(f"Encoded {len(constraints)} constraints in {encode_secs:.2f}s")

    # print(f"Constraints: {(constraints)}")

    print("Solving …")
    t0 = time.perf_counter()
    model = solve(constraints,
                  extra_constraints if placements is not None else None,
                  words=extra_words if placements is not None else None,
                  optimize=optimize,
                  invert_weights=invert_weights)
    solve_secs = time.perf_counter() - t0
    print(f"Solver finished in {solve_secs:.2f}s")

    if model is None:
        print("Constraints unsatisfiable — try a smaller grid, fewer words, "
              "or a lower min-quality.")
        return

    placements = interpret(model, placement_vars, size)
    quality = len(placements)
    print(f"Solution found! {quality} words placed\n")
    print(placements)
    print(print_placement(placements, size))

    if tex_path is not None:
        import crossword_tikz
        grid = crossword_tikz.build_grid(placements, size)
        cell_numbers = crossword_tikz.compute_cell_numbers(placements)
        tikz = crossword_tikz.render_tikz(grid, size, cell_numbers)
        latex = crossword_tikz.render_latex(tikz)
        with open(tex_path, "w") as f:
            f.write(latex)
        print(f"TikZ written to {tex_path}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a crossword via SAT (Z3). "
                    "Encoding: https://bohlender.pro/blog/generating-crosswords-with-sat-smt/"
    )
    word_source = parser.add_mutually_exclusive_group(required=True)
    word_source.add_argument(
        "--words",
        help="Comma-separated list of words, e.g. CAT,DOG,COT,OAT",
    )
    word_source.add_argument(
        "--clues",
        metavar="FILE",
        help="Path to a clues file; the first word of each non-empty line is used",
    )
    parser.add_argument(
        "--size",
        type=int,
        default=13,
        help="Side length of the square grid (default: 12)",
    )
    parser.add_argument(
        "--min-quality",
        type=int,
        default=0,
        dest="min_quality",
        help="Minimum quality (number of words placed, default: 0)",
    )
    parser.add_argument(
        "--tex",
        metavar="FILE",
        default=None,
        help="Also write a LaTeX/TikZ file to this path, e.g. crossword.tex",
    )
    parser.add_argument(
        "--grid",
        metavar="FILE",
        default=None,
        help="Extend the grid attached",
    )
    parser.add_argument(
        "--llm",
        action="store_true",
        help="Use an LLM to suggest a grid layout",
    )
    parser.add_argument(
        "--max-repairs",
        type=int,
        default=0,
        dest="max_repairs",
        help="Maximum LLM repair attempts when --llm is used (default: 0)",
    )
    parser.add_argument(
        "--no-optimize",
        action="store_true",
        dest="no_optimize",
        help="Use a plain Solver instead of Optimize (faster, ignores soft constraints)",
    )
    parser.add_argument(
        "--invert-weights",
        action="store_true",
        dest="invert_weights",
        help="Invert soft-constraint weights: prefer shorter existing words (default: prefer longer)",
    )
    
    start = time.perf_counter()
    args = parser.parse_args()

    if args.size > 13 and not args.no_optimize:
        print("Cannot use optimize solver for grid sizes > 13, switching to plain solver.")
        args.no_optimize = True

    if args.words is not None:
        words = [w.strip() for w in args.words.split(",") if w.strip()]
    else:
        try:
            with open(args.clues) as f:
                words = [line.split()[0] for line in f if line.strip()]
        except OSError as e:
            print(f"Error reading clues file: {e}", file=sys.stderr)
            sys.exit(1)

    if not words:
        print("Error: no words found — check --words or --clues", file=sys.stderr)
        sys.exit(1)

    if args.grid is not None and args.llm:
        print("Error: --grid and --llm are mutually exclusive", file=sys.stderr)
        sys.exit(1)

    placements = []
    if args.llm:
        print(f"Suggesting a grid layout for {len(words)} words …")
        placements = suggest_grid(words, args.size, args.min_quality,
                                  max_repairs=args.max_repairs)
        placements = [p for p in placements if p[0] in words]
        print(f"Suggested placements: {placements}")

    if args.grid:
        try:
            with open(args.grid) as f:
                _, _, _, placements = parse_grid(f.read())
            placements = [p for p in placements if p[0] in words]
        except OSError as e:
            print(f"Error reading grid file: {e}", file=sys.stderr)
            sys.exit(1)

    generate_crossword(words, args.size, args.min_quality,
                       tex_path=args.tex,
                       placements=placements if placements else None,
                       optimize=not args.no_optimize,
                       invert_weights=args.invert_weights)
    
    print(f"Total time: {time.perf_counter() - start:.2f}s")


if __name__ == "__main__":
    main()
