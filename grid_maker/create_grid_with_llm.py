import json
from pathlib import Path
from validator.validator_from_andrews.llm import *


def build_crossword(clues_file="grid_maker/clues.txt"):
    # Load your wrapper
    model = get_model_openai(model_name="gpt-5.5-2026-04-23", max_tokens=64000)

    clues = Path(clues_file).read_text(encoding="utf-8")

    prompt = f"""
      You are an expert crossword constructor.

      The following are crossword answers with their clues.

      Your task is to reconstruct a valid crossword layout.

      Requirements:
      - Select as many answers from the provided list of clues as you can.
      - Every selected answer appears exactly once.
      - Every answer is placed either horizontally or vertically.
      - Words intersect only on identical letters.
      - Every intersection must belong to both words.
      - No adjacent words may touch unless they intersect.
      - The entire crossword must fit inside a 13×13 grid.
      - Use '#' for black squares.
      - Use uppercase letters only.
      - The grid must be rectangular (13 strings of length 13).

      Ensure that you return a VALID crossword grid that conforms to these requirements.

      Return ONLY the grid. in this format(with no Markdow, JSON, or explanations):

      Example format:

      OBSERVE#MATCH
      P#Y#E#N###R##
      E#R#L#AWKWARD
      R#U#E#M###M##
      APPEARED#SPED
      T###S#L#G#L#E
      ISRAEL#REPEAT
      O#E#D#N#N###E
      N#C##REMEMBER
      ##Y#K#C#R#R#G
      ANCIENT#O#I#E
      ##L#P#A#U#N#N
      SHEET#RESPECT

      Clues:

      {clues}
      """

    response = model(prompt)

    return response


def print_crossword(crossword):
    print("\nGRID\n")

    for row in crossword["grid"]:
        print(row)

    print("\nACROSS\n")
    for clue in crossword["across"]:
        print(f'{clue["number"]:>2}. {clue["clue"]}')

    print("\nDOWN\n")
    for clue in crossword["down"]:
        print(f'{clue["number"]:>2}. {clue["clue"]}')


if __name__ == "__main__":
    crossword = build_crossword()
    print_crossword(crossword)