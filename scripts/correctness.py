from generator.pre_translated_clues.generate_pre_translated_clues import *
from generator.string_clues import *
from pathlib import Path
import time
import argparse

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

num_clues_of_each_type = 10
max_rewrites=3

def write_clue_file(clues: dict[str, list[dict]], filename: str, directory: str) -> None:
    # Create directory if it doesn't exist
    output_dir = Path(directory)
    output_dir.mkdir(parents=True, exist_ok=True)

    filepath = output_dir / filename

    with open(filepath, "w", encoding="utf-8") as f:
        for answer, clue_list in clues.items():
            for clue in clue_list:
                f.write(
                    f"{answer} {clue['clue']} ({clue['pattern']}) {clue['type']}\n"
                )


# RUNNING WITHOUT VALIDATOR
def run_without_validator(model_name, experiment_name):
  total_runtime = 0
  unique_answers = set()

  for clue_type in clue_types:
    # Create logfile directory if it doesn't exist
    log_dir = Path(f"logfiles/{experiment_name}/{clue_type}")
    log_dir.mkdir(parents=True, exist_ok=True)

    with open(f"logfiles/{experiment_name}/{clue_type}/generation_{clue_type}_logfile.txt", "a", encoding="utf-8") as clue_type_logfile, \
      open(f"logfiles/{experiment_name}/clues.txt", "a", encoding="utf-8") as cluefile:
      start_time = time.perf_counter()
      clues = generate_string_clues(clue_type=clue_type, num_clues=num_clues_of_each_type, model_name=model_name)
      end_time = time.perf_counter()
      time_to_run = end_time - start_time
      total_runtime += time_to_run

      clue_type_logfile.write(f"------------------------------{clue_type}---------------------------------\n")
      for clue in clues:
          unique_answers.add(clue["answer"])
          cluefile.write(
              f"{clue['answer']} "
              f"{clue['clue']} "
              f"({clue['pattern']}) "
              f"{clue['intended_type']}\n"
          )
      clue_type_logfile.write("\n".join(map(str, clues)) + "\n")
      clue_type_logfile.write(f"time to run: {time_to_run}\n\n\n\n")

      print(clues)

  stats_file = Path(f"logfiles/{experiment_name}/generation_stats.txt")
  with open(stats_file, "w", encoding="utf-8") as generation_stats_file:
    generation_stats_file.write(f"Total runtime: {total_runtime:.2f} seconds\n")
    generation_stats_file.write(f"Unique answers: {len(unique_answers)}\n")


# RUNNING WITH VALIDATOR
def run_with_validator(model_name, experiment_name):
  this_experiment_runtimes = {}
  this_experiment_average_iterations = {}
  unique_answers = set()

  for clue_type in clue_types:
    # Create logfile directory if it doesn't exist
    log_dir = Path(f"logfiles/{experiment_name}/{clue_type}")
    log_dir.mkdir(parents=True, exist_ok=True)

    with open(f"logfiles/{experiment_name}/{clue_type}/generation_{clue_type}_logfile.txt", "a", encoding="utf-8") as logfile, \
      open(f"logfiles/{experiment_name}/{clue_type}/successful_{clue_type}_clues.txt", "a", encoding="utf-8") as successful_clue_file, \
      open(f"logfiles/{experiment_name}/{clue_type}/failed_{clue_type}_clues.txt", "a", encoding="utf-8") as failed_clue_file:
        
      start_time = time.perf_counter()
      successful_clues, average_iterations = iteratively_generate_pre_translated_clues(clue_type=clue_type, 
                                                num_clues=num_clues_of_each_type,
                                                logfile=logfile, 
                                                successful_clue_file=successful_clue_file, 
                                                failed_clue_file=failed_clue_file,
                                                max_rewrites=max_rewrites,
                                                model_name=model_name
                                                )
      end_time = time.perf_counter()
      this_experiment_runtimes[clue_type] = end_time - start_time
      this_experiment_average_iterations[clue_type] = average_iterations
      logfile.write(f"\ntime to run: {this_experiment_runtimes}\n\n")
      logfile.write(f"\nAverage Iterations: {this_experiment_average_iterations}\n\n")
      unique_answers.update(successful_clues.keys())
      write_clue_file(clues=successful_clues, filename="clues.txt", directory=f"logfiles/{experiment_name}")

  total_runtime = sum(this_experiment_runtimes.values())
  overall_average_iterations = (
      sum(this_experiment_average_iterations.values())
      / len(this_experiment_average_iterations)
  )

  stats_file = Path(f"logfiles/{experiment_name}/generation_stats.txt")
  with open(stats_file, "w", encoding="utf-8") as generation_stats_file:
    generation_stats_file.write(f"Total runtime: {total_runtime:.2f} seconds\n")
    generation_stats_file.write(f"Overall average iterations: {overall_average_iterations:.2f}\n")
    generation_stats_file.write(f"Unique answers: {len(unique_answers)}\n")



MODEL_NAMES = {
    "gpt52": "gpt-5.2-2025-12-11",
    "gpt55": "gpt-5.5-2026-04-23",
    "gpt4": "gpt-4o",
    "llama3": "meta-llama/Llama-3.3-70B-Instruct",
}


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--model",
        choices=MODEL_NAMES.keys(),
        required=True,
    )

    parser.add_argument(
        "--validator",
        action="store_true",
        help="Run with validator",
    )

    args = parser.parse_args()

    model_name = MODEL_NAMES[args.model]

    experiment_name = (
        f"{args.model}_with_validator"
        if args.validator
        else f"{args.model}_no_validator"
    )

    if args.validator:
        run_with_validator(model_name, experiment_name)
    else:
        run_without_validator(model_name, experiment_name)


if __name__ == "__main__":
    main()



