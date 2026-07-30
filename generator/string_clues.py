from validator.validator_from_andrews.llm import get_model_openai
import json
import re

def get_example(clue_type):
  if clue_type =="anagram":
    example = '''{
                "clue": "Mob rage about trade restriction",
                "pattern": "7",
                "answer": "EMBARGO",
                "intended_type": "anagram",
                "definition": "trade restriction",
                "wordplay_part": "mob rage about",
                "wordplay_explanation": "MOB RAGE anagram",
                "indicator": "about"
                }
              '''
  elif clue_type == "charade":
    example = '''{
                "clue": "Group continue to swing in popular trend",
                "pattern": "9",
                "answer": "BANDWAGON",
                "intended_type": "charade",
                "definition": "popular trend",
                "wordplay_part": "group continue to swing",
                "wordplay_explanation": "BAND (group) + WAG ON (continue to swing)",
                "indicator": "none"
                }
              '''
  elif clue_type == "container":
    example = '''{
                "clue" :"wild about editor describing US governance?",
                "pattern" : "7",
                "answer" : "FEDERAL",
                "definition" : "describing US governance?",
                "wordplay_explanation" : "FERAL (wild) put inside (about) ED (editor)",
                "wordplay_part" : "wild about editor",
                "intended_type" : "container",
                "indicator" : "about"
                }
              '''
  elif clue_type == "deletion":
    example = '''{
                "clue": "Voice criticism of short novel?",
                "pattern": "3",
                "answer": "BOO",
                "intended_type": "deletion",
                "definition": "voice criticism",
                "wordplay_part": "short novel?",
                "wordplay_explanation": "short BOOK (novel) -> BOO",
                "indicator": "short"
                }
              '''
  elif clue_type == "double_definition":
    example = '''{
                "clue" : "Hair of the dog? Scientist may need it",
                "pattern" : "3,4",
                "answer" : "LAB COAT",
                "definition" : "scientist may need it",
                "wordplay_explanation" : "double definition. the coat of a labrador (Lab) // a scientist's lab coat",
                "wordplay_part" : "hair of the dog?",
                "intended_type" : "double_definition",
                "indicator" : "none"
                }
                '''
  elif clue_type == "hidden":
    example = '''{
                "clue": "Clue wraith in Tolkein hides",
                "pattern": "4",
                "answer": "HINT",
                "intended_type": "hidden",
                "definition": "clue",
                "wordplay_part": "wraith in Tolkein hides",
                "wordplay_explanation": "(wrait)H IN T(olkein)",
                "indicator": "hides"
                }
              '''
  elif clue_type == "homophone":
    example = '''
                {
                "clue": "Arrest that woman, said Roman leader?",
                "pattern": "6",
                "answer": "CAESAR",
                "intended_type": "homophone",
                "definition": "Roman leader?",
                "wordplay_part": "Arrest that woman, said",
                "wordplay_explanation": "homophone of 'seize her' (arrest that woman) = CAESAR",
                "indicator": "said" }
              '''
  elif clue_type == "anagram_and_charade":
    example = '''
                {
                "clue": "Learner so rude about holy site in France",
                "pattern": "7",
                "answer": "LOURDES",
                "intended_type": "anagram_and_charade",
                "definition": "holy site in France",
                "wordplay_part": "Learner so rude about",
                "wordplay_explanation": "L (learner) + (SO RUDE)* (*about = anagram)",
                "indicator": "about" }
              '''
  elif clue_type == "charade_and_container":
    example = '''
                {
                "clue": "The daughter crossing stream is very happy",
                "pattern": "8",
                "answer": "THRILLED",
                "intended_type": "charade_and_container",
                "definition": "very happy",
                "wordplay_part": "The daughter crossing stream is",
                "wordplay_explanation": "THE D (the daughter) surrounds RILL (stream)",
                "indicator": "crossing" }
              '''
  elif clue_type == "charade_and_deletion":
    example = '''
                {
                "clue": "Attractive tailless insect approaching",
                "pattern": "8",
                "answer": "BECOMING",
                "intended_type": "charade_and_deletion",
                "definition": "Attractive",
                "wordplay_part": "tailless insect approaching",
                "wordplay_explanation": "BEE (insect) - E (tailless) + COMING (approaching)",
                "indicator": "tailless" }
              '''
  else:
    raise RuntimeError("Incorrect clue type to generate string clue")
  
  return example


def extract_dict(response):
    # Find the first {...} block
    match = re.search(r"\{.*\}", response, re.DOTALL)

    if match is None:
        raise ValueError("No dictionary found in response.")

    return json.loads(match.group())


def generate_string_clues(clue_type, num_clues, model_name):
  clues = []
  example = get_example(clue_type)
  model = get_model_openai(model_name)

  prompt = f'''
    Generate me a cryptic crossword clue with a {clue_type}
    wordplay type.
    Give me your clue in this dictionary format.
    Don’t use this example clue in your answers,
    come up with your own.

    {example}
  '''

  for i in range(num_clues):
    while True:
        response = model(prompt)

        try:
            clue = extract_dict(response)
            print(clue)
            clues.append(clue)
            break
        except json.JSONDecodeError:
            print("Invalid JSON, retrying...")

  return clues

