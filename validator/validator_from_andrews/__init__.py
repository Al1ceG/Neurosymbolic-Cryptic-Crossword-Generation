import re
from enum import Enum, EnumMeta
from validator.validator_from_andrews.corpora import Actions
import ast 
import Levenshtein

"""
# https://cryptics.fandom.com/wiki/Category:Setting_and_solving_aids
## List of:
*  abbreviations

### Indicator words:
*  anagram
*  container and contents
*  general deletion
*  hidden word
*  homophone
*  juxtaposition
*  letter deletion
*  letter selection
*  linking words and phrases
*  palindrome
*  reversal
*  substitution and movement

"""


class ActionEnum(object):
  def __getattr__(self,  name):
    #print(f"Trying to get '{name}'")
    try:
      return Actions.enums.index(name)
    except (ValueError) as error:
      options = ', '.join(Actions.enums)
      msg = f"'{name}' is invalid, please choose one of {options}"
      raise ValueError(msg) from None
Action = ActionEnum()


function_defs=f'''
```python
Action = Enum('Action', '{",".join(Actions.enums)}')
# External definitions
def is_synonym(phrase:str, test_synonym:str, pattern:str='') -> bool:
  # Determines whether 'test_synonym' is a reasonable synonym for 'phrase', with letters optionally matching 'pattern'
  return True # defined elsewhere
def is_abbreviation(phrase:str, test_abbreviation:str) -> bool:
  # Determines whether 'test_abbreviation' is a valid abbreviation or short form for 'phrase'
  return True # defined elsewhere
def action_type(phrase:str, action:Action) -> bool:
  # Determines whether 'phrase' might signify the given 'action'
  return True # defined elsewhere
def is_anagram(letters:str, word:str) -> bool:
  # Determines whether 'word' can be formed from 'letters' (i.e. is an anagram)
  return True # defined elsewhere
def is_homophone(phrase:str, test_homophone:str) -> bool:
  # Determines whether 'test_homophone' sounds like 'phrase'
  return True # defined elsewhere
```
'''.strip()  # , SELECT_FIRST

# def literal(word:str) -> str:
#  # Returns 'word' as a character-wise uppercase version for insertion into a crossword grid
#  return word.upper()

re_strip_punc = re.compile(r'[^A-Z]')
def pattern_to_re(pattern):
  pattern_re = str(pattern)  # Pattern is of the form '4,3' (no brackets)
  if pattern_re.endswith(','): pattern_re=pattern_re[:-1] # Snip off trailing ','
  pattern_re = pattern_re.replace(',', r'[\s\,]').replace('-', r'[\-]?')
  pattern_re = re.sub(r'(\d+)', r'[a-zA-Z]{\1}', pattern_re)
  return f'^{pattern_re}$'

class SolverState(object):
  def __init__(self, thesaurus=None, crossword_qa=None, abbreviations=None, model_synonym=None, model_homophone=None, model_abbreviation=None, model_action=None, actions=None, ):
    self.trace=[]
    self.fn_capture=[ fn+'(' for fn in "is_abbreviation,is_synonym,is_homophone,action_type,is_anagram".split(',') ] # ,literal
    
    self.thesaurus=thesaurus
    if thesaurus is not None:
      raise "thesauras is obsolete!"
      
    self.crossword_qa=crossword_qa  # If found, the synonym is confirmed
    self.model_synonym=model_synonym
    
    self.model_homophone=model_homophone
    
    self.abbreviations=abbreviations
    self.model_abbreviation=model_abbreviation

    self.model_action=model_action

    self.actions=actions
    
  def is_synonym(self, phrase:str, test_synonym:str, pattern:tuple=None) -> bool:
    # Checks whether 'test_synonym' matches 'phrase'
    act=f"""assert is_synonym('{phrase}', '{test_synonym}'{'' if pattern is None else f", pattern='{pattern}'"})"""
    res, valid, err = dict(act=act), False, []

    if test_synonym.lower() == phrase.lower():  # This is a trivial case
      valid=True
    else:
      if self.thesaurus is not None:
        # Check that both words are known (otherwise it's impossible)
        test_synonyms = self.thesaurus.refs.get(test_synonym.lower(), [])
        if len(test_synonyms)==0:
          err.append(f"'{test_synonym}' is not a word in the thesaurus")
          
        test_phrases  = self.thesaurus.refs.get(phrase.lower(), [])
        if len(test_phrases)==0:
          err.append(f"'{phrase}' is not in thesaurus")
          
        for idx in test_synonyms:
          if phrase in self.thesaurus.main[idx]:
            #print(f"Found '{phrase}' in '{self.thesaurus.main[idx]}'!")
            valid, err = True, []
            
        if not valid:
          if len(test_synonyms)>0:
            err.append(f"'{test_synonym}' is not a synonym for '{phrase}' in the thesaurus")
  
      if not valid and self.crossword_qa is not None:
        if self.crossword_qa.is_synonym(phrase, test_synonym):
          #print(f"Found '{phrase}'->'{test_synonym}' in crossword_qa!")
          valid, err = True, []
            
        if not valid:
          err.append(f"'{test_synonym}' is not a known synonym for '{phrase}' in a crossword dictionary")
  
      # Check using LLM if it hasn't matched so far, and isn't valid yet
      if not valid and self.model_synonym is not None:
        err=[] # Don't complain about explicit thesaurus stuff - we'll complain if the expert doesn't know anyway
        prompt_parts=[
          #f"""Would the answer "{test_synonym}" be sufficiently similar to "{phrase}" to be a crossword answer?""",
          #f"""In the context of a crossword clue, could "{phrase}" be answered "{test_synonym}"?""",
          #f"""In the context of a crossword clue, could "{phrase}" be answered "{test_synonym}" (either as a synonym or an example)?""",
          f"""In the context of a crossword clue, is "{test_synonym}" reasonably close (either as a synonym or an example) to "{phrase}"? Keep in mind that synonyms may be humorous, witty or cryptic so be lenient and think outside the box.""",
          #f"""Are the "{phrase}" be answered "{test_synonym}" (either as a synonym or an example)?""",
          "Please classify {{YES, NO}}",
        ]
        response=self.model_synonym(prompt_parts)  #cache_prefix='SYN_' now passed in...
        valid = 'YES' in response.upper()
        if not valid:
          # Complain about LLM not knowing
          err.append(f"'{test_synonym}' is not a synonym for '{phrase}' according to an expert")
        
    if pattern is not None:
      pattern_re = pattern_to_re(pattern)
      try:
        if not re.match(pattern_re, test_synonym):
          err.append(f"'{test_synonym}' does not match pattern='{pattern}'")
          valid=False
      except Exception as e:
        print(e)
        err.append(f"pattern='{pattern}' is not valid. A pattern should be formatted like : '6', '2,4,4', or '2-4'")
        valid=False
      
    if not valid:
      res['err']='; '.join(err)
    
    self.trace.append(res)
    return valid

  def levensthtein_sorted_list(self, term, arr):
    # Sort in order (pick nearest 'n' ) :
    #   https://rapidfuzz.github.io/Levenshtein/levenshtein.html#Levenshtein.distance
    #lev_and_arr = zip([Levenshtein.distance(term,a) for a in arr], arr)
    lev_and_arr = zip([1.-Levenshtein.ratio(term, a) for a in arr], arr)
    return list(map(lambda pair: pair[1], sorted(lev_and_arr)))
    
  def is_abbreviation(self, phrase:str, test_abbreviation:str) -> bool:
    # Checks whether 'test_abbreviation' matches 'phrase'
    act=f"assert: is_abbreviation('{phrase}', '{test_abbreviation}')"
    res, valid = dict(act=act), False

    # Take the first letter of each word in the phrase
    words = phrase.split()
    abbreviation = "".join(word[0] for word in words if word)

    # Compare with the test abbreviation (case-insensitive)
    if (abbreviation.lower() == test_abbreviation.lower()):
      return True


    if self.abbreviations is None:
      res['err']='No abbreviations dictionary available'
    else:
      err = []
      phrase0, test_abbreviation0=phrase, test_abbreviation
      # attempt to find test_abbreviation in the list...
      phrases = self.abbreviations.short_to_phrase.get(test_abbreviation, [])
      if len(phrases)==0:
        test_abbreviation=test_abbreviation.lower()
        phrases = self.abbreviations.short_to_phrase.get(test_abbreviation, [])
      if phrase in phrases or phrase.lower() in phrases:
        return True
        
      shorts = self.abbreviations.phrase_to_short.get(phrase, [])
      if len(shorts)==0:
        phrase=phrase.lower()
        shorts = self.abbreviations.phrase_to_short.get(phrase, [])
      if test_abbreviation in shorts or test_abbreviation.lower() in shorts:  
        return True
      
      # Ask an LLM if it agrees with the abbreviation
      if self.model_abbreviation is not None:
        print("CHECKING ABBREVIATION WITH LLM")
        err=[]
        prompt_parts=[
          f"""In the context of a crossword clue, is "{test_abbreviation}" an abbreviation for "{phrase}"?""",
          "Please classify {{YES, NO}}",
        ]
        response=self.model_abbreviation(prompt_parts)
        valid = 'YES' in response.upper()
        
      if not valid:
        if len(shorts)==0:
          msg='does not have a valid abbreviation'
        else:
          msg='may be abbreviated : '+', '.join([a.upper() for a in self.levensthtein_sorted_list(test_abbreviation, shorts)[:5]])
        err.append(f"'{phrase0}' {msg}")
        
        if len(phrases)==0:
          msg='is not a valid abbreviation'
        else:
          msg='is an abbreviation for : '+', '.join(self.levensthtein_sorted_list(phrase, phrases)[:5])
        err.append(f"'{test_abbreviation0}' {msg}")
        
        res['err']='; '.join(err)
    self.trace.append(res)
    return valid

  
  def is_homophone(self, phrase:str, test_homophone:str) -> bool:
    # Checks whether 'test_homophone' sounds like 'phrase'
    act=f"assert is_homophone('{phrase}', '{test_homophone}')"
    res, valid, err = dict(act=act), False, []
    
    if self.model_homophone is None:
      valid=True # Just assume Yes
    else:
      prompt_parts=[
        f"""Does "{test_homophone}" sound reasonably similar to "{phrase}" as a homophone in a cryptic crossword clue?""",
        "Please classify {{YES, NO}}",
      ]
      response=self.model_homophone(prompt_parts)  #cache_prefix='HOM_' now passed in...
      valid = 'YES' in response.upper()
      if not valid:
        #err.append(f"'{test_homophone}' is not a homophone for '{phrase}' according to an expert")
        err.append(f"'{phrase}' and '{test_homophone}' are not homophones according to an expert")

    if not valid:
      res['err']='; '.join(err)
    
    self.trace.append(res)
    return valid

  
  def action_type(self, phrase:str, action:Action) -> bool:
    # Checks whether 'phrase' might signify the given 'action'
    action_name = self.actions.enums[action]  # Must exist (action is now an integer, not an enum)
    act=f"assert action_type('{phrase}', Action.{action_name})"
    res, valid, err = dict(act=act), False, []

    ## Now that 'Action.' gives a suitable not-found error for bad actions - this is too much
    #if phrase in self.actions.phrase_to_action:
    #  action_names = self.actions.phrase_to_action[phrase] 
    #  if action.name in action_names:
    #    valid=True
    #  else:
    #    action_names = [ f'Action.{name}, ' for name in action_names ]  # Does not include the specified one
    #    #print(action_names)
    #    if len(action_names)>1: 
    #      action_names[-2] = action_names[-2].replace(', ', ' or ') 
    #    #print(f"'{action_names[-1]}'")
    #    action_names[-1] = action_names[-1].replace(', ', '') # Last one
    #    err.append(f"'{phrase}' is not Action.{action.name}, but it might be {''.join(action_names)}")
    #else:
    #  err.append(f"'{phrase}' is not Action.{action.name}, nor any other Action")
    #  # TODO : Ask an LLM whether phrase is similar to an Action?
    
    if phrase.lower() in self.actions.phrase_to_action:  
      # The phase does exist - are we attempting the right action?
      action_names = self.actions.phrase_to_action[phrase.lower()] 
      if action_name in action_names:
        valid=True
      else:
        action_names = [ f'Action.{name}, ' for name in action_names ]  # Does not include the specified one
        #print(action_names)
        if len(action_names)>1: 
          action_names[-2] = action_names[-2].replace(', ', ' or ') 
        #print(f"'{action_names[-1]}'")
        action_names[-1] = action_names[-1].replace(', ', '') # Last one
        err.append(f"'{phrase}' does not suggest Action.{action_name}, but it could well be {''.join(action_names)}")
    else:
      if False:
        # Let's see whether the Action we've specified has a phrase in it that is contained in (or contains?) our one
        phrases_for_action = self.actions.action_to_phrase[action_name] # Must exist
        phrase_padded=f" {phrase.lower()} "
        phrases_found=[]
        for p in phrases_for_action:
          if f" {p} " in phrase_padded: # The action is very likely correct, but the phrase doesn't fit...
            phrases_found.append(f"'{p}'")
        if len(phrases_found)>0:
          msg = f"Action rethink : '{phrase}' does not suggest Action.{action_name}, but these parts could : {', '.join(phrases_found)}"
          print(msg)
          err.append(msg)
        else:
          err.append(f"'{phrase}' does not suggest Action.{action_name}, nor any other Action")
      else:
        # TODO  : Ask the VectorEmbedding whether phrase is similar to an Action?
        # TOO EXPENSVE : Ask an LLM whether phrase is similar to an Action?
        action_arr=self.actions.get_closest_actions(phrase, debug=False)
        if len(action_arr)==0:
          err.append(f"'{phrase}' does not suggest Action.{action_name}, or any other Action")
        else:
          #if action==action_arr[0]:
          if action_name in action_arr:
            valid=True # Yes : It's totally fine!
          else:
            action_names = [ f'Action.{a}, ' for a in action_arr ]  # Does not include the specified one
            #for a in action_arr:
            if len(action_names)>1: 
              action_names[-2] = action_names[-2].replace(', ', ' or ') 
            #print(f"'{action_names[-1]}'")
            action_names[-1] = action_names[-1].replace(', ', '') # Last one
            err.append(f"'{phrase}' does not suggest Action.{action_name}, but it might be {''.join(action_names)}")

    if self.model_action is not None:
        prompt_parts = [
            f"""In a cryptic crossword context, does the phrase "{phrase}" reasonably indicate the action "{action_name}"?""",
            "Please classify {YES, NO}",
        ]

        response = self.model_action(prompt_parts)
        llm_valid = 'YES' in response.upper()

        if llm_valid:
            valid = True
            err.clear()  # Override vector-based error
        else:
            err.append(
                f"According to an expert, '{phrase}' does not suggest Action.{action_name}"
            )

    if not valid:
      res['err']='; '.join(err)

    self.trace.append(res)
    return valid 
  
  def is_anagram(self, word1:str, word2:str) -> bool:
    act=f"assert is_anagram('{word1}', '{word2}')"
    res=dict(act=act)
    # Checks whether 'word1' and 'word2' are anagrams of each other
    word1_upper, word2_upper = re_strip_punc.sub('', word1.upper()), re_strip_punc.sub('', word2.upper())
    ucase1, ucase2 = sorted( word1_upper ), sorted( word2_upper )
    if ucase1==ucase2:
      self.trace.append(res)
      return True # Yes - these are anagrams
    err=[]
    if len(ucase1)!=len(ucase2):
      err.append("Lengths differ")
    # Find characters missing from word1 that are in word2 (and vice-versa)
    word1_extra = ''
    for l in word1_upper:
      if l in word2_upper:
        word2_upper=word2_upper.replace(l,'',1)
      else:
        word1_extra+=l
    if len(word1_extra)>0:
      err.append(f"'{word2}' missing '{word1_extra}'")
    if len(word2_upper)>0:
      err.append(f"'{word1}' missing '{word2_upper}'")
    self.trace.append(res | dict(err=', '.join(err)))
    return False
  
  # def literal(self, word:str) -> str:
  #  # Returns 'word' as a character-wise uppercase version
  #  return re_strip_punc.sub('', word.upper())


  # def get_clue_hints(self, clue:str) -> [str]:
  #   clue_clean = [re_strip_punc.sub('', a.upper()).lower() for a in clue.split(' ')]
  #   clue_clean_len=len(clue_clean)
  #   #print(clue_clean)
  #   clues=[]
  #   for start in range(clue_clean_len):
  #     for l in range(1,3+1):
  #       if start+l>clue_clean_len: 
  #         break
  #       frag = ' '.join(clue_clean[start:start+l])
  #       #print(frag)
        
  #       # Look up frag in Abbreviations
  #       shorts = self.abbreviations.phrase_to_short.get(frag, [])
  #       if len(shorts)>0:
  #         clues.append(f"'{frag}' : Potential abbreviation{'s' if len(shorts)>1 else ''}: {' '.join([s.upper() for s in shorts])}")
          
  #       # Look up frag in Actions
  #       #if frag in self.actions.phrase_to_action:  
  #       action_names = self.actions.phrase_to_action.get(frag, [])
  #       if len(action_names)>0:
  #         clues.append(f"'{frag}' : Potential Action{'s' if len(action_names)>1 else ''}: {' '.join([f'Action.{name}' for name in action_names])}")
  #         #action_names = [ f'Action.{name}, ' for name in action_names ]
  #         #if len(action_names)>1: 
  #         #  action_names[-2] = action_names[-2].replace(', ', ' or ') 
  #         #action_names[-1] = action_names[-1].replace(', ', '') # Last one
  #         #clues.append(f"'{frag}' : Potential Actions : {''.join(action_names)}")
  #   return clues
  
  def _make_proof_namespace(self, fn=None):
    namespace = {'Action': Action, 'self': self}
    if fn is not None:
      arg_names = [a.arg for a in fn.args.args]
      defaults = fn.args.defaults
      if defaults:
        for name, default in zip(arg_names[-len(defaults):], defaults):
          if isinstance(default, ast.Constant):
            namespace[name] = default.value
    return namespace

  def _transform_assertion_src(self, s_orig):
    s = s_orig
    for fn in self.fn_capture:
      if fn in s:
        s = s.replace(fn, 'self.'+fn)
    return s

  def eval_assertion(self, s_orig, namespace=None) -> bool:
    s = self._transform_assertion_src(s_orig)
    if namespace is None:
      namespace = self._make_proof_namespace()
    try:
      res = eval(s, namespace)
    except Exception as e:
      #print(type(e), str(e) )
      str_e=str(e).replace('SolverState.', '')
      self.trace.append(dict(act=s_orig, err=str_e)) # str(type(e))+
      res=False
    #print(res, self.trace)
    return res

  def _execute_proof_statement(self, py, node, namespace):
    """Run one proof-body statement, sharing namespace across lines."""
    if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant):
      return None

    src = ast.get_source_segment(py, node)
    if src is None:
      return None

    if isinstance(node, ast.Assert):
      test_src = ast.get_source_segment(py, node.test)
      self.trace = []
      if not self.eval_assertion(test_src, namespace):
        return self.debug_when_failed(test_src)
      return None

    if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
      try:
        exec(src, namespace)
      except Exception as e:
        str_e = str(e).replace('SolverState.', '')
        return f"Error in assignment: {src} : {str_e}"
      return None

    return None
    
  def debug_when_failed(self, s):
    res=[]
    if len(self.trace)==0:
      res.append('AssertionError: assert '+s)
      #res.append('  > ERROR: Assertion Failed')
    for t in self.trace:
      err=t.get('err', None)
      if err:
        #res.append('AssertionError: '+t.get('act',''))
        #res.append('  > Hint: '+err)
        res.append('AssertionError: '+t.get('act','')+' : '+err)  # ORIGINAL NeurIPS
        #res.append('AssertionError: '+t.get('act','')+' : FAILED')  # ICML : no_hint + one_err : TODO : REVERT!
    return '\n'.join(res)

  def get_function_from_ast(self, py):
    fn, err=None, "Badly formed python output"
    try:
      parsed = ast.parse(py)
  
      comments = ast.get_docstring(parsed)
      assert comments == None # No surrounding comments
      
      #print(ast.dump(parsed, indent=2))
      fn = parsed.body[0] 
      if isinstance(fn, (ast.FunctionDef,)) and fn.name=='proof':
        #print('def proof(...) found')
        err=None 
      else:
        err="No proof(...) function defined"
    except Exception as e:  
      pass  # Swallow error (message is in 'err')
    return fn, err

  def get_assertion_list(self, py, fn):
    assertions=[]
    for node in fn.body:  # This is a list of stuff
      #print(ast.dump(node, indent=2))
      if isinstance(node, ast.Expr):
        if isinstance(node.value, ast.Constant):
          #print(f"Constant: {node.value.value}")
          continue
      if isinstance(node, ast.Assert):
        #print(f"Assertion: {ast.dump(node.test, indent=2)}")
        src=ast.get_source_segment(py, node.test)
        #print(f"Assertion: {src}")
        assertions.append(src)
        continue
      #print("Non-conforming line...")
    #print("\n\nASSERTIONS\n  "+'\n  '.join(assertions)) 
    return assertions

  def get_code_report(self, py, fn, err, clue):
    report=[]
    if err is not None:
      report.append(err) # This might report 'malformed' for instance
    else:
      namespace = self._make_proof_namespace(fn)
      for node in fn.body:
        statement_err = self._execute_proof_statement(py, node, namespace)
        if statement_err is not None:
          report.append(statement_err)
      #if len(report)>1: # ICML : one_err : TODO : REVERT!
      #  report=report[0:1]  # Strip it down to first error message
          
    if clue is not None:
      unused = self.check_proof_uses_every_word_in_clue(clue, py, fn)
      if unused:
        report.append(
          "Words: " + ", ".join(unused) + " MUST be present in at least one python assertion" 
        )

    return report


  def check_proof_uses_every_word_in_clue(self, clue: str, py: str, fn):
    """
    Ensures every non-boring word in the cryptic clue appears in
    at least one assertion string literal.
    Returns a list of unused words (lowercase).
    """

    BORING_WORDS = {
    "a", "an", "the", "in", "on", "for", "with", "by", "at", "from",
    "and", "or", "to", "of", "is", "are", "was", "were", "be", "been", "being",
    "it", "its", "it's", "some", "any", "give", "gives", "s", "appearing", "shows",
    "when", "these", "they", "them", "that", "perhaps", "maybe"
    }

    # --- Tokenise clue ---
    clue_words = {
        w.lower()
        for w in re.findall(r"[A-Z]+", clue.upper())
        if w.lower() not in BORING_WORDS
    }

    # --- Collect words from string literals in assertions and assignments ---
    used_words = set()
    for node in fn.body:
      if not isinstance(node, (
                              # ast.Assign, 
                              # ast.AnnAssign, 
                              # ast.AugAssign, 
                              ast.Assert)):
        continue
      for subnode in ast.walk(node):
        if isinstance(subnode, ast.Constant) and isinstance(subnode.value, str):
          words = re.findall(r"[A-Z]+", subnode.value.upper())
          used_words.update(w.lower() for w in words)

    # --- Find unused clue words ---
    unused = sorted(
      w for w in clue_words
      if not any(w in used for used in used_words)
    )

    return unused

