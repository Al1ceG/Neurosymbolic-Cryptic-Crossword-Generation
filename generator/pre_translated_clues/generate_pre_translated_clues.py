from validator.validator_from_andrews.corpora import Actions
from validator.validator_from_andrews.llm import get_model_openai
from validator.validator_from_andrews.validator_utils import *
from validator.validator_from_andrews.corpora import *
from generator.pre_translated_clues.generator_prompts import *
from generator.pre_translated_clues.generator_utils import *
from generator.pre_translated_clues.generator_feedback import *
from collections import defaultdict


abbreviations = Abbreviations()
embedder = VectorEmbedder()
actions = Actions(embedder=embedder)
crossword_qa = CrosswordQA()
# Select LLMs
model_for_translation = get_model_openai()
model_for_synonyms = get_model_openai('gpt-4o')
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
ss=SolverState(**solver_config)

# store generated clues
successful_clues = defaultdict(list)

def store_successful_generated_clue(py, 
                         clue_text, 
                         clue_answer, 
                         clue_pattern, 
                         clue_type,
                         successful_clue_file,
                         ):
  print(py)
  successful_clues[clue_answer].append({
    "clue": clue_text,
    "pattern": clue_pattern,
    "type": clue_type,
    "python": py,
  })
  # successful_clues[clue_answer] = clue_text + f" ({clue_pattern}) {clue_type}"
  successful_clue_file.write('\n' + py  + '\n')


def iteratively_generate_pre_translated_clues(max_rewrites=1, 
                                              clue_type=None, 
                                              num_clues=1, 
                                              logfile=sys.stdout, 
                                              successful_clue_file=None, 
                                              failed_clue_file=None, 
                                              num_examples=1,
                                              feedback=False,
                                              temperature=1.0,
                                              top_p=1.0,
                                              model_name="gpt-5"):
  
  model = get_model_openai(model_name, temperature=temperature, top_p=top_p)
  num_iterations = 0

  ERROR_TYPES = (
      "synonym errors",
      "abbreviation errors",
      "action errors",
      "unused word errors",
      "string errors",
  )

  stats = {
      "num_successful": 0,
      "num_failed": 0,
      "num_generated": num_clues,
      "errors": dict.fromkeys(ERROR_TYPES, 0),
      "total_num_writes": 0,
      "total_num_quality_rewrites": 0,
      "per clue stats": np.zeros((num_clues, len(ERROR_TYPES) + 2), dtype=int),
  }

  for clue_num in range(num_clues):

    success_rewrite=-1
    num_quality_rewrites = 0
    py, report, clue_evaluation_report=None,None,None
    last_clue_failed = True

    for rewrite in range(max_rewrites+1):
      logfile.write(f"\n#REWRITE#:{rewrite:d}:REWRITE-START::\n")

      if rewrite==0:
        # first try
        prompt_whole = prompt_background(clue_type=clue_type, num_examples=num_examples)
      else:
        if clue_evaluation_report is None:
          # send same prompt again, but with error message too. We need to fix validity.
          report_full = '\n'.join(report)
          prompt_whole = prompt_report_previous_errors(py, report_full)
        else:
          # send same prompt again, but with evaluation hints too. We need to fix quality of clue.
          prompt_whole = prompt_report_evaluation(py, clue_evaluation_report)
      
      # log prompt
      log_something(rewrite_num=rewrite, log_type="PROMPT", logfile=logfile, thing_to_log=prompt_whole[0])

      # call model
      response = model(prompt_whole)
      log_something(rewrite_num=rewrite, log_type="RESPONSE", logfile=logfile, thing_to_log=response)

      # # extract python section from response
      # py = extract_python_from_response(response)
      # log_something(rewrite_num=rewrite, log_type="EXTRACTED_PYTHON", logfile=logfile, thing_to_log=py)

      # # analyze python (check validity)
      # fn, err = ss.get_function_from_ast(py)
      # clue_text = get_arg_from_dsl(py, "clue")
      # clue_answer = get_arg_from_dsl(py, "answer")
      # clue_pattern = get_arg_from_dsl(py, "pattern")
      # report = ss.get_code_report(py, fn, err, clue=clue_text)

      # extract python section from response
      py = extract_python_from_response(response)
      log_something(rewrite_num=rewrite, log_type="EXTRACTED_PYTHON", logfile=logfile, thing_to_log=py)

      # analyze python (check validity) - guard against unparsable/missing code
      if not py or not py.strip():
        report = ["No valid Python code block could be extracted from the model response."]
        fn, err = None, None
        clue_text = clue_answer = clue_pattern = None
      else:
        try:
          fn, err = ss.get_function_from_ast(py)
          clue_text = get_arg_from_dsl(py, "clue")
          clue_answer = get_arg_from_dsl(py, "answer")
          clue_pattern = get_arg_from_dsl(py, "pattern")
          report = ss.get_code_report(py, fn, err, clue=clue_text)
        except SyntaxError as e:
          report = [f"SyntaxError while parsing extracted code: {e}"]
          fn, err = None, e
          clue_text = clue_answer = clue_pattern = None
        except Exception as e:
          report = [f"Unexpected error while analyzing extracted code: {e}"]
          fn, err = None, e
          clue_text = clue_answer = clue_pattern = None

      if len(report)==0:
        # log number of successful rewrite
        logfile.write(f"\n#REWRITE#:{rewrite:d}:SUCCESS!\n")

        if feedback:
          # check quality
          clue_evaluation_report = get_clue_evaluation(clue_text)

          # If clue passes evaluation
          if clue_evaluation_report is None:
            logfile.write(f"\n#REWRITE#:{rewrite:d}:EVALUATION SUCCESS\n")
            success_rewrite=rewrite
            last_clue_failed = False

            # store generated clue
            store_successful_generated_clue(py=py, 
                                 clue_text=clue_text, 
                                 clue_answer=clue_answer, 
                                 clue_pattern=clue_pattern,
                                 clue_type=clue_type,
                                 successful_clue_file=successful_clue_file
                                 )
            break

          # Clue fails evaluation
          else:
            logfile.write(f"\n#REWRITE#:{rewrite:d}:EVALUATION FAIL\n")
            log_something(rewrite_num=rewrite, log_type="EVALUATION-REPORT", logfile=logfile, thing_to_log=clue_evaluation_report)
            num_quality_rewrites += 1
            last_clue_failed = True

        else:
          success_rewrite=rewrite
          last_clue_failed = False
          # store generated clue
          store_successful_generated_clue(py=py, 
                               clue_text=clue_text, 
                               clue_answer=clue_answer, 
                               clue_pattern=clue_pattern,
                               clue_type=clue_type,
                               successful_clue_file=successful_clue_file
                               )
          break

      else:
        # log report for unsuccessful rewrite
        log_something(rewrite_num=rewrite, log_type="ERROR-TRACE", logfile=logfile, thing_to_log='\n'.join(report))

        last_clue_failed = True

        # reset evaluation report: we need to go back to fix validity
        clue_evaluation_report = None

      # end this rewrite, loop again
      logfile.write(f"\n#REWRITE#:{rewrite:d}:REWRITE-END")


    # If clue failed, store the clue in the failed file
    if last_clue_failed:
      print(py)
      failed_clue_file.write('\n' + (py or '<no code extracted>') + '\n')

    # update stats
    num_iterations = num_iterations + rewrite + 1
    stats = update_stats(stats=stats,
                         report=report, 
                         clue_num=clue_num, 
                         ERROR_TYPES=ERROR_TYPES, 
                         num_all_rewrites_for_clue=rewrite,
                         num_quality_rewrites_for_clue=num_quality_rewrites)
        
  print(f"FINAL STATS: \n {stats}")
  log_something(rewrite_num=-1, log_type="FINAL-STATS", logfile=logfile, thing_to_log=stats)

  average_iterations = num_iterations / num_clues

  return successful_clues, average_iterations



if __name__ == "__main__":
  # GENERATE CLUES WITH CORRECT FILES
  clue_type="anagram"
  num_examples=1
  max_rewrites=3
  num_clues=5
  feedback=False
  temperature=1.0
  top_p=1.0
  model_name='gpt-5'

  with open(f"logfiles/validator_fix/{clue_type}/generation_{clue_type}_logfile.txt", "a", encoding="utf-8") as logfile, \
    open(f"logfiles/validator_fix/{clue_type}/successful_{clue_type}_clues.txt", "a", encoding="utf-8") as successful_clue_file, \
    open(f"logfiles/validator_fix/{clue_type}/failed_{clue_type}_clues.txt", "a", encoding="utf-8") as failed_clue_file:
      
    iteratively_generate_pre_translated_clues(clue_type=clue_type, 
                                              num_clues=num_clues,
                                              logfile=logfile, 
                                              successful_clue_file=successful_clue_file, 
                                              failed_clue_file=failed_clue_file,
                                              num_examples=num_examples,
                                              max_rewrites=max_rewrites,
                                              feedback=feedback,
                                              temperature=temperature,
                                              top_p=top_p,
                                              model_name=model_name
                                              )
    
