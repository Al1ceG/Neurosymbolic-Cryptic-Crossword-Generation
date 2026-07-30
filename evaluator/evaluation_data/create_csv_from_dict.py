from evaluator.perplexity import compute_perplexity
from evaluator.llm_feedback import evaluate_clue_with_llm
from evaluator.polysemy import polysemy_score
from evaluator.is_thematic import thematic_fit_score
from evaluator.semantic_distance import semantic_distance
import csv
from testing.test_clues_times import all_times


CSV_COLUMNS = [
    "clue_text",
    "wordplay",
    "definition",
    "answer",
    "pattern",
    "num_chars",
    "num_words",
    "clue_type",
    "perplexity",
    "thematic_fit",
    "semantic_distance",
    "polysemy",
    "llm_wit",
    "llm_uniqueness",
    "llm_fairness",
    "llm_surface_read",
    "llm_overall",
]


def count_chars_in_clue(clue_text: str) -> int:
    return len(clue_text)

def count_words_in_clue(clue_text: str) -> int:
    return len(clue_text.split())


def clue_to_csv_row(clue_dict: dict) -> dict:
    clue_text = clue_dict["clue"]
    wordplay = clue_dict.get("wordplay_part", "")
    definition = clue_dict.get("definition", "")
    answer = clue_dict["answer"]
    pattern = clue_dict["pattern"]
    clue_type = clue_dict.get("intended_type", "")

    # numeric structure
    num_chars = count_chars_in_clue(clue_text)
    num_words = count_words_in_clue(clue_text)

    # computed metrics
    perplexity = compute_perplexity(clue_text)
    thematic_fit = thematic_fit_score(clue_text)      
    semantic_dist = semantic_distance(wordplay, answer)
    polysemy = polysemy_score(clue_text)

    # LLM-based evaluation
    llm_eval = evaluate_clue_with_llm(clue_text)

    return {
        "clue_text": clue_text,
        "wordplay": wordplay,
        "definition": definition,
        "answer": answer,
        "pattern": pattern,
        "num_chars": num_chars,
        "num_words": num_words,
        "clue_type": clue_type,
        "perplexity": perplexity,
        "thematic_fit": thematic_fit,
        "semantic_distance": semantic_dist,
        "polysemy": polysemy,
        "llm_wit": llm_eval["wit"],
        "llm_uniqueness": llm_eval["uniqueness"],
        "llm_fairness": llm_eval["fairness_and_precision"],
        "llm_surface_read": llm_eval["surface_reading"],
        "llm_overall": llm_eval["overall_score"],
    }


def export_clues_to_csv(clues, output_path):
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()

        for clue in clues:
            row = clue_to_csv_row(clue)
            writer.writerow(row)


export_clues_to_csv(all_times, "evaluator/evaluation_data/times.csv")
