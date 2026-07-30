from validator.validator_from_andrews.validator_prompts import *
import re
from validator.validator_from_andrews.__init__ import SolverState, function_defs

def iteratively_create_proof_of_clue(model, clue, solver_config,
                       answer=None, pattern=None, wordplay=None, definition=None,
                       max_rewrites=0, add_wordplay_hints=False, wordplay_rubric='', 
                       flog=sys.stdout,
                      ):
  
  ss=SolverState(**solver_config)
    
  prompt_background = prompt_explain_task_and_possible_functions()
  prompt_question = prompt_translate_specific_clue(clue, 
                                                   answer=answer, 
                                                   pattern=pattern, 
                                                   wordplay=wordplay, 
                                                   definition=definition)

  py, report=None,None  # Need to be set to actual values before use...

  success_rewrite=-1
  for rewrite in range(max_rewrites+1):
    if rewrite==0:
       # first try
      prompt_whole = prompt_background + prompt_question
    else:
      # send same prompt again, but with error message too
      prompt_whole = prompt_report_previous_errors(prompt_background, prompt_question, py, report)

    flog.write(f"\n#REWRITE#:{rewrite:d}:START::\n")
    flog.write( '\n---PARTSEP---\n'.join(prompt_whole) )
    flog.write(f"\n#END#")
    
    response = model(prompt_whole)

    flog.write(f"\n#REWRITE#:{rewrite:d}:RESPONSE:(WHOLE)::\n")
    flog.write(response)
    flog.write(f"\n#END#")
    
    flog.write(f"\n#REWRITE#:{rewrite:d}:RESPONSE:(PY)::\n")
    py = extract_python_from_response(response)
    flog.write(py)
    flog.write(f"\n#END#")
    
    fn, err = ss.get_function_from_ast(py)
    report = ss.get_code_report(py, fn, err, clue=clue)
    
    if len(report)==0:
      flog.write(f"\n#REWRITE#:{rewrite:d}:SUCCESS!\n")
      success_rewrite=rewrite
      break
    else:
      flog.write(f"\n#REWRITE#:{rewrite:d}:ERROR TRACE ::\n")
      flog.write('\n'.join(report))
      flog.write(f"\n#END#")
    flog.write(f"\n#REWRITE#:{rewrite:d}:END")
      
  return success_rewrite, response


def strip_str(whole, s):
    if whole.startswith(s): whole=whole[len(s):]
    if whole.endswith(s):   whole=whole[:-len(s)]
    return whole

def _clean_extracted_python(code):
    code = re.sub(r"\bproof\(\)\s*$", "", code.strip())
    return code.strip()


def _extract_proof_function_fallback(content):
    print("USING FALLBACK TO PULL OUT PYTHON FROM LLM RESPONSE")
    match = re.search(r'^\s*def proof\s*\(', content, re.MULTILINE)
    if not match:
        return ""

    lines = content[match.start():].split('\n')
    result_lines = []
    for i, line in enumerate(lines):
        stripped = line.lstrip()
        if i > 0:
            if stripped.startswith('proof()') or stripped.startswith('```'):
                break
            if stripped and not line.startswith((' ', '\t')):
                break
        result_lines.append(line)

    return _clean_extracted_python('\n'.join(result_lines))


def extract_python_from_response(content):
    # Prefer fenced markdown blocks when present
    match = re.search(r"```python\s*(.*?)\s*```", content, re.DOTALL | re.IGNORECASE)
    if match:
        return _clean_extracted_python(match.group(1))

    return _extract_proof_function_fallback(content)

