from pathlib import Path
import re
from collections import Counter


def load_answers(clues_file):
    """
    Extract answers from clues.txt.

    Assumes each line begins with the answer.
    Example:
        SEMINAR Class remains mixed (7) anagram
    """

    answers = []

    for line in Path(clues_file).read_text(encoding="utf8").splitlines():
        line = line.strip()
        if not line:
            continue

        # First word is the answer
        answer = line.split()[0].upper()

        # Keep only A-Z characters
        answer = re.sub(r"[^A-Z]", "", answer)

        if answer:
            answers.append(answer)

    return answers


def parse_grid(text):
    """
    Parse a crossword grid of any size, square or not.

    - Rows are uppercased and stripped.
    - Short rows are right-padded with '#' up to the width of the
      longest row (so ragged input doesn't blow up).
    - If the grid still isn't square (rows != cols), it is padded
      with extra '#' rows and/or '#' columns up to
      max(original_rows, original_cols), so the result is always a
      square grid.

    Returns:
        grid: list[str]              -- the final, square, padded grid
        errors: list[str]            -- any structural problems found
        original_size: tuple[int,int] -- (rows, cols) before padding
    """

    lines = [
        line.strip().upper()
        for line in text.strip().splitlines()
        if line.strip()
    ]

    errors = []

    if not lines:
        raise ValueError("Grid is empty")

    original_rows = len(lines)
    original_cols = max(len(row) for row in lines)
    original_size = (original_rows, original_cols)

    row_lengths = [len(row) for row in lines]
    if len(set(row_lengths)) != 1:
        errors.append(
            "Input rows had inconsistent lengths "
            f"(row lengths: {row_lengths}); short rows were padded with '#'"
        )

    # Pad every row to the max width found
    width = original_cols
    lines = [row.ljust(width, "#") for row in lines]

    # Pad to square using the larger of rows/cols
    target = max(original_rows, width)

    if original_rows != width:
        errors.append(
            f"Grid was not square ({original_rows}x{width}); "
            f"padded to {target}x{target} with '#'"
        )

    # Pad columns (widen each row) if needed
    if width < target:
        lines = [row.ljust(target, "#") for row in lines]

    # Pad rows (add blank rows) if needed
    if original_rows < target:
        lines = lines + (["#" * target] * (target - original_rows))

    # Character validation (after padding, so only real bad input shows up)
    for r, row in enumerate(lines):
        if not re.fullmatch(r"[A-Z#]+", row):
            errors.append(
                f"Row {r + 1} contains invalid characters"
            )

    return lines, errors, original_size


def extract_across(grid):
    words = []

    rows = len(grid)
    cols = len(grid[0])

    for r in range(rows):
        c = 0

        while c < cols:

            if grid[r][c] == "#":
                c += 1
                continue

            if c == 0 or grid[r][c - 1] == "#":

                start = c

                while c < cols and grid[r][c] != "#":
                    c += 1

                word = grid[r][start:c]

                if len(word) > 1:
                    words.append(("A", r, start, word))

            else:
                c += 1

    return words


def extract_down(grid):
    words = []

    rows = len(grid)
    cols = len(grid[0])

    for c in range(cols):

        r = 0

        while r < rows:

            if grid[r][c] == "#":
                r += 1
                continue

            if r == 0 or grid[r - 1][c] == "#":

                start = r

                while r < rows and grid[r][c] != "#":
                    r += 1

                word = "".join(
                    grid[i][c]
                    for i in range(start, r)
                )

                if len(word) > 1:
                    words.append(("D", start, c, word))

            else:
                r += 1

    return words


def validate_touching(grid):
    """
    Ensure words only touch by crossing.

    Rejects patterns like

    CAT
      DOG

    where letters are adjacent without intersecting.
    """

    rows = len(grid)
    cols = len(grid[0])

    for r in range(rows):
        for c in range(cols):

            if grid[r][c] == "#":
                continue

            horiz = (
                (c > 0 and grid[r][c - 1] != "#")
                or (c < cols - 1 and grid[r][c + 1] != "#")
            )

            vert = (
                (r > 0 and grid[r - 1][c] != "#")
                or (r < rows - 1 and grid[r + 1][c] != "#")
            )

            # Horizontal-only letters cannot have vertical neighbours
            if horiz and not vert:

                if r > 0:
                    if (
                        grid[r - 1][c] != "#"
                        and (c == 0 or grid[r - 1][c - 1] == "#")
                        and (c == cols - 1 or grid[r - 1][c + 1] == "#")
                    ):
                        raise ValueError(
                            f"Illegal touching near {(r, c)}"
                        )

                if r < rows - 1:
                    if (
                        grid[r + 1][c] != "#"
                        and (c == 0 or grid[r + 1][c - 1] == "#")
                        and (c == cols - 1 or grid[r + 1][c + 1] == "#")
                    ):
                        raise ValueError(
                            f"Illegal touching near {(r, c)}"
                        )

            # Vertical-only letters cannot have horizontal neighbours
            if vert and not horiz:

                if c > 0:
                    if (
                        grid[r][c - 1] != "#"
                        and (r == 0 or grid[r - 1][c - 1] == "#")
                        and (r == rows - 1 or grid[r + 1][c - 1] == "#")
                    ):
                        raise ValueError(
                            f"Illegal touching near {(r, c)}"
                        )

                if c < cols - 1:
                    if (
                        grid[r][c + 1] != "#"
                        and (r == 0 or grid[r - 1][c + 1] == "#")
                        and (r == rows - 1 or grid[r + 1][c + 1] == "#")
                    ):
                        raise ValueError(
                            f"Illegal touching near {(r, c)}"
                        )


def validate_crossword(response_text, clues_file, logfile, expected_word_count=None):
    """
    expected_word_count: optional int. If provided, the report checks the
    number of placed words against it. If None, this check is skipped
    entirely (since the "right" word count depends on the puzzle, not
    just the grid dimensions).
    """
    report = []

    mistakes = 0

    answers = set(load_answers(clues_file))

    try:
        grid, parse_errors, original_size = parse_grid(response_text)
    except Exception as e:
        report.append(f"GRID FORMAT ERROR: {e}")
        mistakes += 1

        # save_report(logfile, report)

        return {
            "valid": False,
            "mistakes": mistakes,
        }

    across = extract_across(grid)
    down = extract_down(grid)

    placed = across + down

    words = [w for _, _, _, w in placed]

    # -----------------------
    # Basic grid statistics
    # -----------------------

    filled_cells = sum(
        1
        for row in grid
        for cell in row
        if cell != "#"
    )

    rows = len(grid)
    cols = len(grid[0])
    total_cells = rows * cols

    density = (filled_cells / total_cells) * 100

    report.append("CROSSWORD GRID REPORT")
    report.append("=" * 40)
    report.append("")

    orig_rows, orig_cols = original_size
    if (orig_rows, orig_cols) != (rows, cols):
        report.append(f"Original size: {orig_rows}x{orig_cols}")
        report.append(f"Padded to square: {rows}x{cols}")
    else:
        report.append(f"Grid size: {rows}x{cols}")

    if parse_errors:
        for err in parse_errors:
            report.append(f"NOTE: {err}")

    report.append(f"Filled cells: {filled_cells}/{total_cells}")
    report.append(f"Density: {density:.2f}%")
    report.append("")

    # -----------------------
    # Word statistics
    # -----------------------

    correct_words = [
        w for w in words
        if w in answers
    ]

    wrong_words = [
        w for w in words
        if w not in answers
    ]

    report.append("WORD PLACEMENT")
    report.append("-" * 40)
    report.append(f"Total words found: {len(words)}")
    report.append(f"Words matching clues: {len(correct_words)}")
    report.append(f"Words not in clues: {len(wrong_words)}")

    if wrong_words:
        mistakes += len(wrong_words)

        report.append("")
        report.append("Unknown words:")
        for word in wrong_words:
            report.append(f"  - {word}")

    report.append("")

    # -----------------------
    # Missing clues
    # -----------------------

    missing = sorted(
        answers - set(words)
    )

    report.append("MISSING CLUES")
    report.append("-" * 40)
    report.append(f"Missing answers: {len(missing)}")

    if missing:
        mistakes += len(missing)

        for word in missing:
            report.append(f"  - {word}")

    report.append("")

    # -----------------------
    # Duplicate words
    # -----------------------

    counts = Counter(words)

    duplicates = {
        word: count
        for word, count in counts.items()
        if count > 1
    }

    report.append("DUPLICATES")
    report.append("-" * 40)

    if duplicates:
        mistakes += len(duplicates)

        for word, count in duplicates.items():
            report.append(
                f"{word}: appears {count} times"
            )
    else:
        report.append("None")

    report.append("")

    # -----------------------
    # Word count (only checked if caller supplies an expectation)
    # -----------------------

    report.append("EXPECTED STRUCTURE")
    report.append("-" * 40)

    if expected_word_count is not None:
        if len(placed) != expected_word_count:
            mistakes += 1
            report.append(
                f"Expected {expected_word_count} words, found {len(placed)}"
            )
        else:
            report.append(
                f"Correct number of words ({expected_word_count})"
            )
    else:
        report.append(f"Words placed: {len(placed)} (no expected count supplied)")

    report.append("")

    # -----------------------
    # Touching validation
    # -----------------------

    touching_errors = []

    try:
        validate_touching(grid)

    except Exception as e:
        touching_errors.append(str(e))

    report.append("TOUCHING RULES")
    report.append("-" * 40)

    if touching_errors:

        mistakes += len(touching_errors)

        for error in touching_errors:
            report.append(error)

    else:
        report.append("No illegal touching detected")

    report.append("")

    # -----------------------
    # Final score
    # -----------------------

    score = max(
        0,
        100 - mistakes * 5
    )

    report.append("FINAL RESULT")
    report.append("-" * 40)
    report.append(f"Mistakes: {mistakes}")
    report.append(f"Quality score: {score}/100")

    # save_report(logfile, report)

    return {
        "original_size": f"{orig_rows}x{orig_cols}",
        "grid_size": f"{rows}x{cols}",
        "density": round(density, 2),

        "filled_cells": filled_cells,

        "total_words": len(words),
        "correct_words": len(correct_words),

        "missing_clues": len(missing),
        "wrong_words": len(wrong_words),

        "duplicates": duplicates,
    }


def save_report(logfile, lines):
    logfile.write("\n".join(lines))
    logfile.write("\n\n" + "=" * 40 + "\n\n")
    logfile.flush()