#!/usr/bin/env python3
import sys
from . import function_defs


def prompt_explain_task_and_possible_functions():
  prompt_parts = [
    '''
The task is to produce a formal proof using python code, where the docstring will also include an informal proof as an aid.
The following are functions that can be used in your output code:\n''', 
    function_defs,
    '''
The following are examples of simple functions that prove that each puzzle solution is correct:''', 
    proof_code_examples('ONCE'),
    proof_code_examples('DECIMAL'),
    proof_code_examples('YOKE'),
    proof_code_examples('RELIABLE'),
    proof_code_examples('DELINEATE'),
    proof_code_examples('SUPERMARKET'),
    proof_code_examples('ENROL'),
  ]
  return prompt_parts


def prompt_translate_specific_clue(clue, answer, pattern, wordplay, definition):
  '''
  Input constraints:
  Pattern must be an integer, no brackets
  Answer must be in all upper case
  Clue must have ' not "
  Clue does not have {} brackets
  '''
    
  prompt_parts = [
    f'''
      # Please complete the following in a similar manner, and return the whole function:
      ```python
      def proof(answer="{answer.upper()}", clue="{clue}", pattern='{pattern}'):
        \"\"\"
        definition: {definition}
        wordplay: {wordplay}
        \"\"\" 
        '''
  ]
  return prompt_parts

def prompt_report_previous_errors(prompt_base, prompt_question, py, report):
  # This is for a re-request, assuming that len(report)>0
  report_full = '\n'.join(report)

  prompt_for_python = '\n'.join(  # Take off blank and commented-out lines
    [ line 
        for prompt_section in prompt_question
          for line in prompt_section.split('\n') 
            if not (len(line.strip())==0 or line.startswith('#'))
    ]
  ) 

  prompt_parts = prompt_base + [
    f'''
# The following draft code SOLUTION was returned for a newly posed problem:
```python
{py}proof()
```''',
    f'''
# PROBLEM : the SOLUTION above failed because of the following reported errors (python assertions without errors were valid):
```
{report_full}
```''', 
    f'''
# Please re-implement the SOLUTION above (altering both the docstring and the python code as required), taking care to fix each of the problems identified, and return the whole function:
{prompt_for_python}
''', 
  ]
  return prompt_parts



def proof_code_examples(answer='ONCE', pattern=None, solver_state_hinter=None):
  if answer=='ONCE':
    clue='head decapitated {long ago}'
    plan=f'''
  'head': wordplay
  'decapitated': action
  'long ago': definition'''
    # https://timesforthetimes.co.uk/quick-cryptic-2609-by-orpheus
    wordplay="[b]ONCE (head decapitated = remove first letter of BONCE)"
    py=f'''
  assert is_synonym("head", "BONCE")
  assert action_type("decapitated", Action.REMOVE_FIRST) and "BONCE"[1:] == "ONCE"
  assert is_synonym("long ago", "ONCE", pattern='4')'''

  if answer=='DECIMAL':
    clue='{the point} of medical treatment'
    wordplay="(MEDICAL)* (*treatment = anagram)"
    plan=f'''
  'the point': definition
  'of': null
  'medical': wordplay
  'treatment': action'''
    py=f'''
  assert is_synonym("the point", "DECIMAL", pattern='7')
  assert action_type("treatment", Action.ANAGRAM)
  assert is_anagram("MEDICAL", "DECIMAL")'''
  # assert literal('medical')=='MEDICAL' 

  if answer=='RELIABLE':
    clue='{dependable} about being under an obligation?'
    wordplay="RE (about) + LIABLE (being under an obligation)"
    plan=f'''
  'dependable': definition
  'about': wordplay
  'being under an obligation': wordplay'''
    py=f'''
  assert is_synonym("dependable", "RELIABLE", pattern='8')
  assert is_abbreviation("about", "RE")
  assert is_synonym("being under an obligation", "LIABLE")
  assert "RE"+"LIABLE"=="RELIABLE"'''

  if answer=='DELINEATE':
    clue='{sketch} produced by aileen and ted'
    wordplay="(AILEEN + TED)* (*produced by = anagram)"
    plan=f'''
  'sketch': definition
  'produced by': action
  'aileen': wordplay
  'and': nil
  'ted': wordplay'''
    py=f'''
  assert is_synonym("sketch", "DELINEATE", pattern='9')
  assert action_type("produced by", Action.ANAGRAM)
  assert "AILEEN" + "TED" == "AILEENTED"
  assert is_anagram("AILEENTED", "DELINEATE")'''
  #assert literal('aileen')=='AILEEN' and literal('ted')=='TED' 

  if answer=='YOKE':
    clue='{part of garment} could be yellow, we hear'
    wordplay="(we hear = homophone) of YOLK (which is yellow)"
    plan=f'''
  'part of garment': definition
  'could be': wordplay
  'yellow': wordplay
  'we hear': action'''
    py=f'''
  assert is_synonym("part of garment", "YOKE", pattern='4')
  assert is_synonym("yellow", "YOLK")
  assert action_type("we hear", Action.HOMOPHONE)
  assert is_homophone("YOLK", "YOKE")'''

  if answer=='SUPERMARKET':
    clue='fat bags for every brand that’s {a big seller}'
    wordplay="SUET (fat) (bags = goes outside) of (PER (for every) + MARK (brand))"
    plan=f'''
    'fat': wordplay
    'bags': action
    'for every': wordplay
    'brand': wordplay
    'that\'s': nil
    'a big seller': definition'''
    py=f'''
  assert is_synonym("fat", "SUET")
  assert action_type("bags", Action.GOES_OUTSIDE)
  assert "SUET" == "SU" + "ET"
  assert is_abbreviation("for every", "PER")
  assert is_synonym("brand", "MARK")
  assert "SU" + "PER" + "MARK" + "ET" == "SUPERMARKET"
  assert is_synonym("a big seller", "SUPERMARKET", pattern='11')'''

  if answer=='ENROL':
    clue='{Record} single about maintaining resistance'
    wordplay="(LONE)< (single, <about) maintaining R (resistance)"
    plan=f'''
    'record': definition
    'single': wordplay
    'about': action
    'maintaining': action
    'resistance': wordplay'''
    py=f'''
  assert is_synonym("record", "ENROL", pattern='5')
  assert is_synonym("single", "LONE")
  assert action_type("about", Action.REVERSE) and "LONE"[::-1] == "ENOL"
  assert action_type("maintaining", Action.GOES_OUTSIDE)
  assert is_abbreviation("resistance", "R")
  assert "ENOL" == "EN" + "OL"
  assert "EN" + "R" + "OL" == "ENROL"'''

  clue_no_def = clue.replace('{', '').replace('}', '')  # Remove definition indicators
  defn = f'''
    def proof(answer="{answer.upper()}", clue="{clue_no_def}", pattern='{len(answer) if pattern is None else pattern}'):'''.strip()

  res=f'''
```python
{defn}
  """
  definition: {clue}
  wordplay: {wordplay} 
  """
  {py.strip()}
proof()
```'''  
  return res
