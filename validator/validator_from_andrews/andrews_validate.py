import sys
import os
import pandas as pd
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from llm import get_model_gemini, get_model_openai
from validator_utils import *
from corpora import *

def does_wordplay_make_sense(clue, definition, answer, pattern, wordplay, flog=sys.stdout):
  abbreviations = Abbreviations()
  embedder = VectorEmbedder()
  actions = Actions(embedder=embedder)
  crossword_qa = CrosswordQA()
  # Select LLMs
  model_for_translation = get_model_openai()
  model_for_synonyms = get_model_openai('gpt-5-mini')
  model_for_homophones = get_model_openai()
  model_for_abbreviations = get_model_openai()
  model_for_actions = get_model_openai()

  solver_config = {
      'thesaurus': None,  # Obselete??
      'crossword_qa': crossword_qa,  # Crossword Q&A database for synonym validation
      'abbreviations': abbreviations,  # Abbreviations dictionary
      'model_synonym': model_for_synonyms,  # LLM model for synonym validation
      'model_homophone': model_for_homophones,  # LLM model for homophone validation
      'model_abbreviation': model_for_abbreviations,
      'model_action': model_for_actions,
      'actions': actions,  # Actions dictionary for wordplay indicators
    }

  # Generate prompt to generate a proof from this clue
  success_rewrite, response_text = iteratively_create_proof_of_clue(model=model_for_translation, 
                                            clue=clue,
                                            definition=definition, 
                                            solver_config=solver_config, 
                                            answer=answer, 
                                            pattern=pattern, 
                                            wordplay=wordplay, 
                                            max_rewrites=1,
                                            flog=flog)

  if success_rewrite == -1:
    print("Invalid code or unsuccessful conversion to DSL")
    return 0, False
  else:
    print("Andrews validity : True")
    return (success_rewrite + 1), True # return the number of write attempts
