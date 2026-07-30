

from pathlib import Path

experiment_name = "llama3_with_validator"
clue_file = Path(f"logfiles/{experiment_name}/clues.txt")

unique_answers = set()

with clue_file.open("r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue

        # First token is the answer
        answer = line.split(maxsplit=1)[0]
        unique_answers.add(answer)

print(f"Unique answers: {len(unique_answers)}")