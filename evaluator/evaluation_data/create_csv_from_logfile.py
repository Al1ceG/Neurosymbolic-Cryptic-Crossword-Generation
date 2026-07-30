import re
from pathlib import Path
import csv
from evaluator.evaluation_data.create_csv_from_dict import clue_to_csv_row

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
    "status", # ADD A STATUS COLUMN
]


PROOF_HEADER_RE = re.compile(
    r'def proof\(answer="(?P<answer>[^"]+)",\s*clue="(?P<clue>[^"]+)",\s*pattern=\'?(?P<pattern>\d+)\'?\):'
)

DEFINITION_RE = re.compile(r'definition:\s*(.+)', re.IGNORECASE)

def parse_proof_block(block: str) -> dict:
    header_match = PROOF_HEADER_RE.search(block)
    if not header_match:
        raise ValueError("Could not parse proof header")

    answer = header_match.group("answer")
    clue = header_match.group("clue")
    pattern = header_match.group("pattern")

    def_match = DEFINITION_RE.search(block)
    definition = def_match.group(1).strip() if def_match else ""

    # Infer wordplay by removing definition from clue
    wordplay = re.sub(
        re.escape(definition),
        "",
        clue,
        flags=re.IGNORECASE,
    ).strip()

    wordplay = re.sub(r"\s{2,}", " ", wordplay)

    return {
        "clue": clue,
        "answer": answer,
        "pattern": pattern,
        "definition": definition,
        "wordplay_part": wordplay,
    }

def parse_proof_file(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8")

    blocks = re.split(r'\ndef proof\(', text)
    clues = []

    for block in blocks[1:]:
        block = "def proof(" + block
        try:
            clues.append(parse_proof_block(block))
        except ValueError:
            continue

    return clues

def clue_to_csv_row_from_file(clue_dict: dict, status: str, clue_type: str) -> dict:
    base_row = clue_to_csv_row(clue_dict)
    base_row["status"] = status
    base_row["clue_type"] = clue_type
    print(base_row)
    return base_row


def export_logfile_clues_to_csv(log_dir, output_path):
    log_dir = Path(log_dir)

    files = (
        list(log_dir.rglob("*successful*.txt")) +
        list(log_dir.rglob("*failed*.txt"))
    )

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()

        for file in files:
            status = "successful" if "successful" in file.name else "failed"
            clue_type = file.parent.name
            clues = parse_proof_file(file)

            for clue in clues:
                row = clue_to_csv_row_from_file(clue, status, clue_type)
                writer.writerow(row)


export_logfile_clues_to_csv(
    "logfiles/log_files_test_pre_translated_clues",
    "evaluator/evaluation_data/pre_translated_new.csv",
)

