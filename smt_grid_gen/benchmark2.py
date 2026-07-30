"""
benchmark.py — run crossword.py across a matrix of configurations and log results.

Each run's full stdout/stderr is written to logs/<config_id>.log.
A summary CSV is written to logs/summary.csv when all runs complete.

Usage:
    python benchmark.py              # run everything
    python benchmark.py --dry-run    # print commands without executing
"""

import argparse
import csv
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from itertools import product
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration matrix
# ---------------------------------------------------------------------------

CLUE_FILES = [
    "clues/gpt5_clues1.txt",
    "clues/times_clues1.txt",
]

GRID_SIZE = 13
MIN_QUALITIES = [15, 17, 19, 21]
PYTHON = str(Path("env/bin/python"))

# Each config is (label, extra_flags)
CONFIGS = [
    ("no_llm",                    []),
    ("llm_no_opt",                ["--llm", "--no-optimize"]),
    ("llm_opt",                   ["--llm"]),
    ("llm_no_opt_repair1",        ["--llm", "--no-optimize", "--max-repairs", "1"]),
    ("llm_opt_repair1",           ["--llm", "--max-repairs", "1"]),
    ("llm_no_opt_repair2",        ["--llm", "--no-optimize", "--max-repairs", "2"]),
    ("llm_opt_repair2",           ["--llm", "--max-repairs", "2"]),
]

LOG_DIR = Path("logs2")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def clue_label(clue_file: str) -> str:
    return Path(clue_file).stem


def run_id(clue_file: str, quality: int, config_label: str) -> str:
    return f"{clue_label(clue_file)}_q{quality}_{config_label}"


def parse_output(stdout: str) -> dict:
    """Extract key metrics from the solver's stdout."""
    info = {"words_placed": None, "encode_secs": None, "solve_secs": None, "solution": False}

    m = re.search(r"Solution found!\s+(\d+)\s+words placed", stdout)
    if m:
        info["solution"] = True
        info["words_placed"] = int(m.group(1))

    m = re.search(r"Encoded\s+\d+\s+constraints\s+in\s+([\d.]+)s", stdout)
    if m:
        info["encode_secs"] = float(m.group(1))

    m = re.search(r"Solver finished in\s+([\d.]+)s", stdout)
    if m:
        info["solve_secs"] = float(m.group(1))

    if "unsatisfiable" in stdout.lower() or "unsat" in stdout.lower():
        info["solution"] = False

    return info


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true",
                    help="Print commands without running them")
    args = ap.parse_args()

    LOG_DIR.mkdir(exist_ok=True)

    runs = list(product(CLUE_FILES, MIN_QUALITIES, CONFIGS))
    total = len(runs)
    print(f"Benchmark: {total} runs  |  log dir: {LOG_DIR}/  |  {datetime.now():%Y-%m-%d %H:%M}")
    print()

    summary_rows = []

    for idx, (clue_file, quality, (config_label, extra_flags)) in enumerate(runs, 1):
        rid = run_id(clue_file, quality, config_label)
        log_path = LOG_DIR / f"{rid}.log"

        cmd = [
            PYTHON, "crossword.py",
            "--clues", clue_file,
            "--size", str(GRID_SIZE),
            "--min-quality", str(quality),
            *extra_flags,
        ]

        print(f"[{idx:2d}/{total}] {rid}")
        print(f"        cmd: {' '.join(cmd)}")

        if args.dry_run:
            continue

        wall_start = time.perf_counter()
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=1200,        # 20-minute hard wall-clock limit per run
            )
            wall_secs = time.perf_counter() - wall_start
            stdout = proc.stdout
            stderr = proc.stderr
            exit_code = proc.returncode
        except subprocess.TimeoutExpired as e:
            wall_secs = time.perf_counter() - wall_start
            stdout = e.stdout or ""
            stderr = (e.stderr or "") + "\n[TIMEOUT after 1200s]"
            exit_code = -1

        # Write full log
        with open(log_path, "w") as f:
            f.write(f"# run_id:    {rid}\n")
            f.write(f"# command:   {' '.join(cmd)}\n")
            f.write(f"# timestamp: {datetime.now():%Y-%m-%d %H:%M:%S}\n")
            f.write(f"# exit_code: {exit_code}\n")
            f.write(f"# wall_secs: {wall_secs:.1f}\n")
            f.write("\n--- STDOUT ---\n")
            f.write(stdout)
            if stderr:
                f.write("\n--- STDERR ---\n")
                f.write(stderr)

        parsed = parse_output(stdout)
        result_str = "OK" if parsed["solution"] else ("TIMEOUT" if exit_code == -1 else "UNSAT/FAIL")
        print(f"        → {result_str}  |  words={parsed['words_placed']}  "
              f"|  encode={parsed['encode_secs']}s  |  solve={parsed['solve_secs']}s  "
              f"|  wall={wall_secs:.1f}s")
        print()

        summary_rows.append({
            "run_id":       rid,
            "clues":        clue_label(clue_file),
            "quality":      quality,
            "config":       config_label,
            "solution":     parsed["solution"],
            "words_placed": parsed["words_placed"],
            "encode_secs":  parsed["encode_secs"],
            "solve_secs":   parsed["solve_secs"],
            "wall_secs":    round(wall_secs, 1),
            "exit_code":    exit_code,
            "log":          str(log_path),
        })

    if args.dry_run:
        print("(dry run — no commands executed)")
        return

    # Write summary CSV
    csv_path = LOG_DIR / "summary.csv"
    fieldnames = ["run_id", "clues", "quality", "config", "solution",
                  "words_placed", "encode_secs", "solve_secs", "wall_secs",
                  "exit_code", "log"]
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(summary_rows)

    # Print quick summary table
    solved = sum(1 for r in summary_rows if r["solution"])
    print(f"\n{'='*60}")
    print(f"Completed {len(summary_rows)} runs: {solved} solved, "
          f"{len(summary_rows) - solved} failed/unsat/timeout")
    print(f"Summary CSV: {csv_path}")
    print(f"Logs:        {LOG_DIR}/")


if __name__ == "__main__":
    main()
