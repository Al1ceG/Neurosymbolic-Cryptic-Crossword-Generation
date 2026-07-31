import os
import argparse

from pathlib import Path
from statistics import mean

from evaluator.perplexity import compute_perplexity
from evaluator.semantic_distance import semantic_distance
from evaluator.check_for_plagiarism import plagiarism_match


clue_types = [
    "anagram",
    "charade",
    "container",
    "deletion",
    "double_definition",
    "hidden",
    "homophone",
    "anagram_and_charade",
    "charade_and_deletion",
    "charade_and_container",
]


def parse_line(line):
    """
    Parse a clue line of the form:

        ANSWER clue text (7) anagram
        ANSWER clue text (8) (8) charade

    Returns:
        answer, clue_string, clue_type
    """
    line = line.strip()

    # Extract clue type (last word)
    clue_type = line.rsplit(" ", 1)[1]
    remainder = line.rsplit(" ", 1)[0]

    # Extract answer (first word)
    first_space = remainder.find(" ")
    answer = remainder[:first_space]
    clue_string = remainder[first_space + 1 :]

    # Remove trailing enumeration(s), e.g. (7)
    while clue_string.endswith(")"):
        open_idx = clue_string.rfind("(")
        if open_idx == -1:
            break
        clue_string = clue_string[:open_idx].rstrip()

    return answer, clue_string, clue_type


def parse_args():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--model",
        required=True,
        choices=["gpt52", "gpt55", "gpt4", "llama3", "times"],
        help="Model used to generate clues.",
    )

    parser.add_argument(
        "--validator",
        action="store_true",
        help="Evaluate *_with_validator experiment.",
    )

    parser.add_argument(
        "--correct_only",
        action="store_true",
        help="Evaluate clues.correct.txt instead of clues.txt.",
    )

    return parser.parse_args()



def main():
    args = parse_args()

    if args.model != "times":
        experiment_name = (
            f"{args.model}_with_validator"
            if args.validator
            else f"{args.model}_no_validator"
        )

        clue_filename = (
            "clues_correct.txt"
            if args.correct_only
            else "clues.txt"
        )

        clue_file = Path("logfiles") / experiment_name / clue_filename

    else:
        if args.validator or args.correct_only:
            raise ValueError("--validator and --correct_only cannot be used with model='times'")

        clue_file = Path("clue_sets") / "time_full_set.txt"
        experiment_name = "the_times"

    if not clue_file.exists():
        raise FileNotFoundError(clue_file)

    # Accumulators across all clue types
    all_perplexities_distilgpt2 = []
    all_perplexities_gpt2 = []
    all_perplexities_gpt2_xl = []
    all_semantic_distances = []
    all_num_characters = []
    all_num_words = []
    all_plagiarism = []

    experiment_stats = {}

    with clue_file.open("r", encoding="utf-8") as f:
        parsed = [parse_line(line) for line in f if line.strip()]

    for clue_type in clue_types:

        perplexities_distilgpt2 = []
        perplexities_gpt2 = []
        perplexities_gpt2_xl = []
        semantic_distances = []
        num_characters = []
        num_words = []
        plagiarism = []

        for answer, clue_string, parsed_clue_type in parsed:

            if parsed_clue_type != clue_type:
                continue
            
            perplexity_distilgpt2 = compute_perplexity(clue_string, model_name="distilgpt2")
            perplexity_gpt2 = compute_perplexity(clue_string, model_name="gpt2")
            perplexity_gpt2_xl = compute_perplexity(clue_string, model_name="gpt2-xl")
            semantic_dist = semantic_distance(clue_string, answer)
            is_plagiarised = plagiarism_match(clue_string)

            perplexities_distilgpt2.append(perplexity_distilgpt2)
            perplexities_gpt2.append(perplexity_gpt2)
            perplexities_gpt2_xl.append(perplexity_gpt2_xl)
            plagiarism.append(is_plagiarised)

            semantic_distances.append(semantic_dist)
            num_characters.append(len(clue_string))
            num_words.append(len(clue_string.split()))

            # Also accumulate for the overall mean
            all_perplexities_distilgpt2.append(perplexity_distilgpt2)
            all_perplexities_gpt2.append(perplexity_gpt2)
            all_perplexities_gpt2_xl.append(perplexity_gpt2_xl)
            all_semantic_distances.append(semantic_dist)
            all_num_characters.append(len(clue_string))
            all_num_words.append(len(clue_string.split()))
            all_plagiarism.append(is_plagiarised)
        
        if len(perplexities_distilgpt2) != 0:
          experiment_stats[clue_type] = {
              "num_clues": len(perplexities_distilgpt2),
              "mean_perplexity_distilgpt2": mean(perplexities_distilgpt2),
              "mean_perplexity_gpt2": mean(perplexities_gpt2),
              "mean_perplexity_gpt2_xl": mean(perplexities_gpt2_xl),
              "mean_semantic_distance": mean(semantic_distances),
              "mean_num_characters": mean(num_characters),
              "mean_num_words": mean(num_words),
              "plagiarism_count": sum(plagiarism),
              "plagiarism_percentage":
                  100 * sum(plagiarism) / len(plagiarism)
                  if plagiarism else 0,
          }

    # Overall statistics across all clue types
    if all_perplexities_distilgpt2:
        experiment_stats["all"] = {
            "num_clues": len(all_perplexities_distilgpt2),
            "mean_perplexity_distilgpt2": mean(all_perplexities_distilgpt2),
            "mean_perplexity_gpt2": mean(all_perplexities_gpt2),
            "mean_perplexity_gpt2_xl": mean(all_perplexities_gpt2_xl),
            "mean_semantic_distance": mean(all_semantic_distances),
            "mean_num_characters": mean(all_num_characters),
            "mean_num_words": mean(all_num_words),
            "plagiarism_count": sum(all_plagiarism),
            "plagiarism_percentage":
                100 * sum(all_plagiarism) / len(all_plagiarism),
        }


    print(f"\n=== {experiment_name} ===")
    for clue_type, values in experiment_stats.items():
        print(f"{clue_type}: {values}")

    if args.correct_only:
        logfile = f"logfiles/{experiment_name}/quality_stats_correct_only.txt"
    else:
        logfile = f"logfiles/{experiment_name}/quality_stats.txt"
    os.makedirs(os.path.dirname(logfile), exist_ok=True)

    with open(logfile, "w") as f:
        f.write(f"\n=== {experiment_name} ===\n")
        for clue_type, values in experiment_stats.items():
            f.write(f"{clue_type}: {values}\n")



if __name__ == "__main__":
    main()
