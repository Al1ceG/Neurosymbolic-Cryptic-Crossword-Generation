"""
test_suggest_grid.py — manual smoke-test for suggest_grid.

Run with:
    OPENAI_API_KEY=sk-... python test_suggest_grid.py
"""

from crossword import suggest_grid

WORDS = ["CAT", "DOG", "COT", "OAT"]
SIZE  = 5
MIN_Q = 3



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


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

print(f"Calling suggest_grid(words={WORDS}, s={SIZE}, m={MIN_Q}) …")
placements = suggest_grid(WORDS, SIZE, MIN_Q)

print(f"\nResult ({len(placements)} placement(s)):")
for p in placements:
    print(" ", p)

errors = validate_placements(placements, WORDS, SIZE)

print()
if errors:
    print("VALIDATION FAILED:")
    for e in errors:
        print(" ", e)

    clean = remove_invalid_placements(placements, WORDS, SIZE)
    removed = [p for p in placements if p not in clean]
    print(f"\nRemoved {len(removed)} invalid placement(s): {removed}")
    print(f"Clean placements ({len(clean)}):")
    for p in clean:
        print(" ", p)
else:
    print("All checks passed.")

