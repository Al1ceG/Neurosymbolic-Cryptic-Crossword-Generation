import time
import subprocess
import re
import os
from pathlib import Path
import sys
import argparse

from grid_maker.create_grid_with_llm import build_crossword
from grid_maker.validate_grid import validate_crossword

ROOT = Path(__file__).resolve().parent.parent

N_RUNS = 3  # number of repeats for LLM / GenXWord / SMT+LLM

LLM_LABEL = "LLM"


# Maps each clue file to the column header it should appear under in the
# LaTeX table. Edit this if you add more clue sets.
COLUMN_LABELS = {
    "the_times_1.txt": "Times 1",
    "the_times_2.txt": "Times 2",
    "gpt5_no_validator_1.txt": "GPT 1",
    "gpt5_no_validator_2.txt": "GPT 2",
    "gpt5_with_validator_1.txt": "GPT 3",
    "gpt5_with_validator_2.txt": "GPT 4",
}


def get_grid_string(output, llm=False):
    """
    Extract the grid rows from a solver's stdout.

    If llm=False (default): scans the whole output for any lines that
    look like grid rows (old behaviour).

    If llm=True: only considers the grid block that appears immediately
    before the "Total time: ..." line (i.e. the final solved grid),
    ignoring earlier "Initial grid" / "Repair N grid" attempts.
    """

    lines = output.splitlines()

    if llm:
        # Find the "Total time:" line
        total_idx = next(
            (i for i, line in enumerate(lines)
             if line.strip().lower().startswith("total time")),
            None,
        )

        if total_idx is None:
            # No "Total time:" marker found — nothing to extract
            candidate_lines = []
        else:
            # Walk backwards, skipping any blank line(s) right above it
            j = total_idx - 1
            while j >= 0 and not lines[j].strip():
                j -= 1

            # Collect the contiguous run of grid-looking lines
            grid_block = []
            while (
                j >= 0
                and re.fullmatch(r"[\sA-Z#-]+", lines[j])
                and len(lines[j].strip()) >= 13
            ):
                grid_block.insert(0, lines[j])
                j -= 1

            candidate_lines = grid_block
    else:
        candidate_lines = lines

    # Extract lines that look like grid rows
    grid_lines = [
        line.strip()
        for line in candidate_lines
        if re.fullmatch(r"[\sA-Z#-]+", line)
        and len(line.strip()) >= 13
    ]

    # "- - A B -" -> "##AB#"
    normalised_rows = [
        line.replace(" ", "").replace("-", "#")
        for line in grid_lines
    ]

    grid_string = "\n".join(normalised_rows)
    return grid_string


def get_info_from_smt_string(output: str):
    success = 0
    num_placed = 0
    runtime = 0.0

    # Check whether a solution was found
    if "Solution found!" in output:
        success = 1

        m = re.search(r"Solution found!\s+(\d+)\s+words placed", output)
        if m:
            num_placed = int(m.group(1))

    m = re.search(r"Total time:\s*([\d.]+)s", output)
    if m:
        runtime = float(m.group(1))

    return success, num_placed, runtime


# def create_clue_files():
#     large_clue_sets = [
#         "logfiles/gpt5_no_validator/clues.txt",
#         "logfiles/gpt5_with_validator/clues.txt",
#         "logfiles/the_times/clues.txt",
#     ]

#     output_dir = Path("logfiles/grid_generation")
#     output_dir.mkdir(parents=True, exist_ok=True)

#     for clue_file in large_clue_sets:
#         clue_path = Path(clue_file)

#         with clue_path.open("r", encoding="utf-8") as f:
#             lines = f.readlines()

#         # Split by 1-indexed line number
#         odd_lines = lines[0::2]   # lines 1, 3, 5, ...
#         even_lines = lines[1::2]  # lines 2, 4, 6, ...

#         dataset_name = clue_path.parent.name

#         odd_output = output_dir / f"{dataset_name}_1.txt"
#         even_output = output_dir / f"{dataset_name}_2.txt"

#         with odd_output.open("w", encoding="utf-8") as f:
#             f.writelines(odd_lines)

#         with even_output.open("w", encoding="utf-8") as f:
#             f.writelines(even_lines)

#         print(f"Wrote {len(odd_lines)} lines to {odd_output}")
#         print(f"Wrote {len(even_lines)} lines to {even_output}")


CLUE_DIR = "clue_sets/"

CLUE_SETS = ["gpt5_no_validator_1.txt",
             "gpt5_no_validator_2.txt",
             "gpt5_with_validator_1.txt",
             "gpt5_with_validator_2.txt",
             "the_times_1.txt",
             "the_times_2.txt"]


# ---------------------------------------------------------------------------
# Stats helpers
# ---------------------------------------------------------------------------

def stats_from_validation(validation_info, runtime, clues_placed=None):
    """
    Build a common stats dict from a validate_crossword() result.

    clues_placed: override for the "clues placed" figure (e.g. the number
    parsed out of the SMT solver's own stdout). If not given, falls back
    to validation_info["total_words"] (words actually present in the grid).
    """
    if clues_placed is None:
        clues_placed = validation_info.get("total_words", 0)

    density = validation_info.get("density", 0) or 0

    return {
        "runtime": runtime,
        "density": density,
        "clues_placed": clues_placed,
        "wrong_words": validation_info.get("wrong_words", 0),
        "is_13x13": validation_info.get("grid_size") == "13x13",
    }


def average_stats(stats_list):
    """
    Average a list of stats dicts (as produced by stats_from_validation).
    Entries that are None (failed/timed-out run) are excluded from the
    numeric averages but still count towards the total attempts, so the
    13x13 count is reported as "X / len(stats_list)".
    """
    total_attempts = len(stats_list)
    valid = [s for s in stats_list if s is not None]
    n = len(valid)

    if n == 0:
        return {
            "runtime": None,
            "density": None,
            "clues_placed": None,
            "wrong_words": None,
            "full_size_count": 0,
            "runs_completed": 0,
            "total_attempts": total_attempts,
        }

    return {
        "runtime": sum(s["runtime"] for s in valid) / n,
        "density": sum(s["density"] for s in valid) / n,
        "clues_placed": sum(s["clues_placed"] for s in valid) / n,
        "wrong_words": sum(s["wrong_words"] for s in valid) / n,
        "full_size_count": sum(1 for s in valid if s["is_13x13"]),
        "runs_completed": n,
        "total_attempts": total_attempts,
    }


def write_average(logfile, label, avg):
    logfile.write(f"\n----- {label} averages "
                   f"({avg['runs_completed']}/{avg['total_attempts']} runs completed) -----\n")
    if avg["runs_completed"] == 0:
        logfile.write("No successful runs.\n")
        return
    logfile.write(f"Avg time to run: {avg['runtime']:.2f}s\n")
    logfile.write(f"Avg density: {avg['density']:.2f}%\n")
    logfile.write(f"Avg clues placed: {avg['clues_placed']:.2f}\n")
    logfile.write(f"Avg illegal (wrong) words: {avg['wrong_words']:.2f}\n")
    logfile.write(
        f"Grid generated at full 13x13 size: "
        f"{avg['full_size_count']}/{avg['total_attempts']}\n"
    )




# ---------------------------------------------------------------------------
# Single-run generators (each returns a stats dict, or (success, stats) for SMT)
# ---------------------------------------------------------------------------

def create_grid_with_llm(clue_file, logfile):
    start_time = time.perf_counter()
    response = build_crossword(clues_file=clue_file)
    end_time = time.perf_counter()
    runtime = end_time - start_time

    print(response)
    logfile.write(f"{response} \n")

    validation_info = validate_crossword(response_text=response,
                                          clues_file=clue_file,
                                          logfile=logfile)
    print(validation_info)
    logfile.write(f"\nGeneration time: {runtime} \n")

    return stats_from_validation(validation_info, runtime)


def create_grid_with_genxword(clue_file, logfile):
    start_time = time.perf_counter()
    result = subprocess.run(
        [
            "genxword",
            "-o", "grid_maker/My Crossword",
            "-n", "22",
            clue_file,
            "p"
        ],
        input="13, 13\nY\n",
        capture_output=True,
        text=True,
    )
    end_time = time.perf_counter()
    runtime = end_time - start_time

    print("STDOUT:")
    print(result.stdout)

    print("STDERR:")
    print(repr(result.stderr))

    output = result.stdout

    grid_string = get_grid_string(output=output)

    validation_info = validate_crossword(response_text=grid_string,
                                          clues_file=clue_file,
                                          logfile=logfile)
    print(validation_info)
    logfile.write(f"\nGeneration time: {runtime} \n")

    return stats_from_validation(validation_info, runtime)


def create_grid_with_smt(clue_file, logfile, min_quality, llm, max_repairs=1, opt=True):

    commands = [
                "python",
                "smt_grid_gen/crossword.py",
                "--clues", clue_file,
                "--size", "13",
                "--min-quality", min_quality,
            ]

    if llm:
        commands.append("--llm")
        commands.append("--max-repairs")
        commands.append(str(max_repairs))

    if opt==False:
        commands.append("--no-optimize")

    try:
        result = subprocess.run(
            commands,
            capture_output=True,
            text=True,
            timeout=200,
        )
    except subprocess.TimeoutExpired:
        print(f"Timed out at quality={min_quality}")
        logfile.write(f"Timed out at quality={min_quality}\n")
        return 0, None  # success=False, stats=None

    output = result.stdout
    print("STDOUT:")
    print(output)

    logfile.write(f"STDOUT:\n {output}")

    print(f"STERR: {result.stderr}\n")

    grid_string = get_grid_string(output=output, llm=llm)

    success, clues_placed, runtime = get_info_from_smt_string(output=output)

    validation_info = validate_crossword(response_text=grid_string,
                                          clues_file=clue_file,
                                          logfile=logfile)
    print(validation_info)
    logfile.write(f"\nGrid Validation Information:\n{validation_info} \n")
    logfile.write(f"\nGeneration time: {runtime} \n")

    stats = stats_from_validation(validation_info, runtime, clues_placed=clues_placed)

    return success, stats

    # Generate from a clues file and write a PDF-ready TikZ file
    # python crossword.py --clues clues/gpt5_clues1.txt --size 13 --min-quality 15 --tex puzzle.tex


def find_best_quality(clue_file, logfile, low=10, high=25, llm=False, max_repairs=1, opt=True):
    """
    Binary search for the highest minimum-quality that solves within 200s.
    Assumes quality is an integer between low and high.

    Returns (best_quality, best_stats) for the best successful attempt found
    during the search. best_stats is None if nothing succeeded (e.g. every
    attempt timed out).
    """
    best_quality = None
    best_stats = None

    while low <= high:
        mid = (low + high) // 2

        logfile.write(f"Testing quality={mid}\n")
        print(f"Testing SMT with quality={mid}")


        success, stats = create_grid_with_smt(clue_file=clue_file, 
                                              logfile=logfile, 
                                              min_quality=str(mid), 
                                              llm=llm, 
                                              max_repairs=max_repairs, 
                                              opt=opt)


        if success:
            best_quality = stats["clues_placed"]
            best_stats = stats
            low = stats["clues_placed"] + 1      # Try higher quality
        else:
            high = mid - 1     # Too difficult (includes timeouts)

    return best_quality, best_stats



def run_smt_llm_block(clue_file, logfile, clue_set, label, max_repairs, opt):
    """Run the SMT+LLM binary search N_RUNS times and average the best result of each."""
    logfile.write(f"===== SMT + LLM Binary Search ({label}) =====\n")
    smt_llm_runs = []
    for i in range(N_RUNS):
        logfile.write(f"\n--- Run {i + 1}/{N_RUNS} ---\n")
        best_quality, best_stats = find_best_quality(
            clue_file, logfile, llm=True, max_repairs=max_repairs, opt=opt
        )
        smt_llm_runs.append(best_stats)

        if best_stats is not None:
            logfile.write(f"Best quality within 200s: {best_quality}\n")
            print(f"[{label}] Best quality for {clue_set} (run {i + 1}): {best_quality}")
        else:
            logfile.write("No quality solved within 200s (all attempts timed out or failed).\n")
            print(f"[{label}] No quality solved for {clue_set} (run {i + 1})")

    avg = average_stats(smt_llm_runs)
    write_average(logfile, f"SMT + LLM ({label})", avg)
    logfile.write("\n\n")


def run_smt_grid_gen(clue_file, logfile, clue_set):
              logfile.write("===== SMT Binary Search (single run) =====\n")
              best_quality, best_stats = find_best_quality(clue_file, logfile, llm=False)

              smt_avg = average_stats([best_stats])
              if best_stats is not None:
                  logfile.write(f"\nBest quality within 200s: {best_quality}\n")
                  print(f"Best quality for {clue_set}: {best_quality}")
                  write_average(logfile, "SMT", smt_avg)
              else:
                  logfile.write("\nNo quality solved within 200s.\n")
                  print(f"No quality solved for {clue_set}")
              logfile.write("\n\n")

def parse_args():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--method",
        choices=[
            "llm",
            "genxword",
            "smt",
            "smt-llm-1-opt",
            "smt-llm-3-opt",
            "smt-llm-1-noopt",
            "smt-llm-3-noopt",
            "all",
        ],
        default="all",
        help="Which generator to run."
    )

    return parser.parse_args()


def main():
    args = parse_args()

    os.makedirs(CLUE_DIR, exist_ok=True)
    os.makedirs("logfiles/grid_generation_results", exist_ok=True)

    for clue_set in CLUE_SETS:
        clue_file = os.path.join(CLUE_DIR, clue_set)

        log_name = os.path.splitext(clue_set)[0] + "_results.txt"
        log_path = os.path.join("logfiles/grid_generation_results", log_name)

        with open(log_path, "w") as logfile:
            logfile.write(f"=== Experiment for {clue_set} ===\n\n")

            # ---------------- LLM (averaged over N_RUNS) ----------------
            if args.method in ("llm", "all"):
                logfile.write("===== LLM =====\n")
                llm_runs = []
                for i in range(N_RUNS):
                    print(f"\nRunning LLM on {clue_set} (run {i + 1}/{N_RUNS})")
                    logfile.write(f"\n--- Run {i + 1}/{N_RUNS} ---\n")
                    llm_runs.append(create_grid_with_llm(clue_file, logfile))
                llm_avg = average_stats(llm_runs)
                write_average(logfile, "LLM", llm_avg)
                logfile.write("\n\n")

            # ---------------- GenXWord (single run, no averaging) ----------------
            if args.method in ("genxword", "all"):
                logfile.write("===== GenXWord =====\n")
                genx_stats = create_grid_with_genxword(clue_file, logfile)
                genx_avg = average_stats([genx_stats])
                write_average(logfile, "GenXWord", genx_avg)
                logfile.write("\n\n")

            # ---------------- SMT (single run, no averaging) ----------------
            if args.method in ("smt", "all"):
                run_smt_grid_gen(clue_file=clue_file, logfile=logfile, clue_set=clue_set)

            # ---------------- SMT + LLM variants (each: N_RUNS binary searches, averaged) ----------------
            if args.method in ("smt-llm-1-opt", "all"):
                run_smt_llm_block(
                    clue_file, logfile, clue_set,
                    "1 repair, optimized",
                    max_repairs=1,
                    opt=True,
                )
            if args.method in ("smt-llm-3-opt", "all"):
                run_smt_llm_block(
                    clue_file, logfile, clue_set,
                    "3 repairs, optimized",
                    max_repairs=3,
                    opt=True,
                )

            if args.method in ("smt-llm-1-noopt", "all"):
                run_smt_llm_block(
                    clue_file, logfile, clue_set,
                    "1 repair, no-optimize",
                    max_repairs=1,
                    opt=False,
                )

            if args.method in ("smt-llm-3-noopt", "all"):
                run_smt_llm_block(
                    clue_file, logfile, clue_set,
                    "3 repairs, no-optimize",
                    max_repairs=3,
                    opt=False,
                )

            print(f"All experiments completed for {clue_set}.")


if __name__ == "__main__":
    main()
