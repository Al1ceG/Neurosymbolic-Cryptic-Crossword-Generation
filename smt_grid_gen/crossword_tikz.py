"""
crossword_tikz.py — render a crossword as a compilable LaTeX/TikZ file.

Two input modes
---------------
1. Grid file  (--grid)
   A plain-text file where each character is either a letter (white cell) or
   '#' (black cell).  The grid is rendered directly — no solving required.

2. Solve mode  (--words / --clues)
   Words are encoded as a SAT problem, solved with Z3, and the result is
   rendered.  Mirrors crossword.py's interface.

Usage
-----
  python crossword_tikz.py --grid puzzle.txt [-o out.tex]
  python crossword_tikz.py --words CAT,DOG,COT,OAT --size 5 --min-quality 4
  python crossword_tikz.py --clues clues/gpt5_clues1.txt --size 13 -o out.tex

Compile the output with:
  pdflatex crossword.tex
"""

import argparse
import sys

from crossword import encode_problem, interpret, solve


# ---------------------------------------------------------------------------
# Grid parsing  (for --grid mode)
# ---------------------------------------------------------------------------

def parse_grid(text: str) -> tuple[list[list], int, int]:
    """
    Parse a plain-text crossword grid.

    Each character should be either a letter (white cell — stored as uppercase)
    or '#' (black/empty cell — stored as None).  Lines of different lengths are
    right-padded with '#' to the width of the longest line.

    Returns (grid, nrows, ncols).
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
    return grid, nrows, ncols


# ---------------------------------------------------------------------------
# Clue numbering from a raw grid  (for --grid mode)
# ---------------------------------------------------------------------------

def compute_cell_numbers_from_grid(
    grid: list[list], nrows: int, ncols: int
) -> dict[tuple, int]:
    """
    Assign clue numbers to cells that start an Across or Down entry.

    A cell (col, row) receives a number when it contains a letter AND:
      • it is at the left edge or its left neighbour is black, AND its right
        neighbour is a letter  (→ starts an Across entry), OR
      • it is at the top edge or its upper neighbour is black, AND its lower
        neighbour is a letter  (→ starts a Down entry).

    Numbers are assigned in reading order (top-to-bottom, left-to-right).
    Returns {(col, row): number}.
    """
    starts = set()
    for row in range(nrows):
        for col in range(ncols):
            if grid[row][col] is None:
                continue
            left_black   = col == 0 or grid[row][col - 1] is None
            right_letter = col + 1 < ncols and grid[row][col + 1] is not None
            top_black    = row == 0 or grid[row - 1][col] is None
            below_letter = row + 1 < nrows and grid[row + 1][col] is not None
            if (left_black and right_letter) or (top_black and below_letter):
                starts.add((col, row))
    ordered = sorted(starts, key=lambda p: (p[1], p[0]))
    return {pos: i + 1 for i, pos in enumerate(ordered)}


# ---------------------------------------------------------------------------
# Grid reconstruction
# ---------------------------------------------------------------------------

def build_grid(placements: list[tuple], size: int) -> list[list]:
    """
    Reconstruct the character grid from placements.
    Returns a size×size list-of-lists; None means an empty (black) cell.
    """
    grid = [[None] * size for _ in range(size)]
    for word, x, y, orientation in placements:
        for k, ch in enumerate(word):
            if orientation == "horizontal":
                grid[y][x + k] = ch
            else:
                grid[y + k][x] = ch
    return grid


# ---------------------------------------------------------------------------
# Clue numbering
# ---------------------------------------------------------------------------

def compute_cell_numbers(placements: list[tuple]) -> dict[tuple, int]:
    """
    Assign a clue number to every cell that starts an Across or Down entry.
    Numbers are assigned in reading order (top-to-bottom, left-to-right).
    Returns {(col, row): number}.
    """
    starts = {(x, y) for _, x, y, _ in placements}
    ordered = sorted(starts, key=lambda p: (p[1], p[0]))
    return {pos: i + 1 for i, pos in enumerate(ordered)}


# ---------------------------------------------------------------------------
# TikZ / LaTeX rendering
# ---------------------------------------------------------------------------

def render_tikz(grid: list[list], size: int,
                cell_numbers: dict[tuple, int],
                cell_size: float = 1.0,
                ncols: int | None = None) -> str:
    """
    Build the TikZ picture string.

    `size` sets the number of rows (and columns when the grid is square).
    Pass `ncols` explicitly for non-square grids.

    Coordinate system: TikZ y increases upward, so grid row 0 (top) maps to
    tikz_y = nrows - 1.
    """
    nrows = size
    if ncols is None:
        ncols = size
    cs = cell_size
    lines = [
        rf"\begin{{tikzpicture}}[x={cs}cm, y={cs}cm]",
        "",
        "  % ---- Black (empty) cells ----------------------------------------",
    ]

    for row in range(nrows):
        for col in range(ncols):
            if grid[row][col] is None:
                ty = nrows - 1 - row
                lines.append(
                    f"  \\fill[black] ({col},{ty}) rectangle ({col+1},{ty+1});"
                )

    lines += [
        "",
        "  % ---- Grid lines --------------------------------------------------",
        f"  \\draw[step=1,thin,black!40] (0,0) grid ({ncols},{nrows});",
        f"  \\draw[very thick] (0,0) rectangle ({ncols},{nrows});",
        "",
        "  % ---- Clue numbers ------------------------------------------------",
    ]

    for (col, row), number in cell_numbers.items():
        ty = nrows - 1 - row
        lines.append(
            f"  \\node[anchor=north west, inner sep=1.5pt, "
            f"font=\\tiny\\sffamily] at ({col},{ty+1}) {{{number}}};"
        )

    lines += [
        "",
        "  % ---- Letters -----------------------------------------------------",
    ]

    for row in range(nrows):
        for col in range(ncols):
            ch = grid[row][col]
            if ch is not None:
                ty = nrows - 1 - row
                lines.append(
                    f"  \\node[font=\\normalsize\\bfseries\\sffamily] "
                    f"at ({col+0.5},{ty+0.5}) {{{ch}}};"
                )

    lines += ["", r"\end{tikzpicture}"]
    return "\n".join(lines)


def render_latex(tikz_picture: str) -> str:
    """Wrap the TikZ picture in a minimal standalone LaTeX document."""
    return "\n".join([
        r"\documentclass{standalone}",
        r"\usepackage{tikz}",
        r"\begin{document}",
        tikz_picture,
        r"\end{document}",
        "",
    ])


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Render a crossword grid as a LaTeX/TikZ file."
    )

    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument(
        "--grid",
        metavar="FILE",
        help="Plain-text grid file: letters for white cells, '#' for black cells",
    )
    source.add_argument(
        "--words",
        help="Comma-separated list of words to solve, e.g. CAT,DOG,COT,OAT",
    )
    source.add_argument(
        "--clues",
        metavar="FILE",
        help="Clues file; the first word of each non-empty line is used",
    )

    parser.add_argument(
        "--size",
        type=int,
        default=12,
        help="Grid side length for solve mode (default: 12)",
    )
    parser.add_argument(
        "--min-quality",
        type=int,
        default=0,
        dest="min_quality",
        help="Minimum words to place in solve mode (default: 0)",
    )
    parser.add_argument(
        "--cell-size",
        type=float,
        default=1.0,
        dest="cell_size",
        metavar="CM",
        help="Cell size in centimetres (default: 1.0)",
    )
    parser.add_argument(
        "--output", "-o",
        default="crossword.tex",
        help="Output .tex file (default: crossword.tex)",
    )
    args = parser.parse_args()

    # ------------------------------------------------------------------
    # Grid-file mode
    # ------------------------------------------------------------------
    if args.grid is not None:
        try:
            with open(args.grid) as f:
                text = f.read()
        except OSError as e:
            print(f"Error reading grid file: {e}", file=sys.stderr)
            sys.exit(1)
        grid, nrows, ncols = parse_grid(text)
        cell_numbers = compute_cell_numbers_from_grid(grid, nrows, ncols)
        print(f"Grid: {nrows} rows × {ncols} cols, "
              f"{sum(c is not None for row in grid for c in row)} white cells, "
              f"{len(cell_numbers)} numbered entries")
        tikz = render_tikz(grid, nrows, cell_numbers,
                           cell_size=args.cell_size, ncols=ncols)

    # ------------------------------------------------------------------
    # Solve mode  (--words / --clues)
    # ------------------------------------------------------------------
    else:
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
            print("Error: no words found", file=sys.stderr)
            sys.exit(1)

        words = list(dict.fromkeys(w.upper() for w in words))
        size, min_quality = args.size, args.min_quality

        assert size > 0, f"Grid size ({size}) must be positive"
        longest = max(words, key=len)
        assert size >= len(longest), (
            f'"{longest}" ({len(longest)} chars) does not fit in a {size}×{size} grid'
        )
        assert min_quality >= 0, "min_quality must be non-negative"

        print(f"Encoding {len(words)} words, {size}×{size} grid, "
              f"min-quality={min_quality} …")
        constraints, placement_vars, *_ = encode_problem(words, size, min_quality)
        print(f"Solving ({len(constraints)} constraints) …")
        model = solve(constraints)
        if model is None:
            print("UNSAT — no solution found. "
                  "Try a larger grid, fewer words, or a lower min-quality.",
                  file=sys.stderr)
            sys.exit(1)

        placements = interpret(model, placement_vars, size)
        print(f"Solution: {len(placements)} words placed")
        grid = build_grid(placements, size)
        cell_numbers = compute_cell_numbers(placements)
        tikz = render_tikz(grid, size, cell_numbers, cell_size=args.cell_size)

    # ------------------------------------------------------------------
    # Write output
    # ------------------------------------------------------------------
    latex = render_latex(tikz)
    with open(args.output, "w") as f:
        f.write(latex)
    print(f"Written to {args.output}")


if __name__ == "__main__":
    main()
