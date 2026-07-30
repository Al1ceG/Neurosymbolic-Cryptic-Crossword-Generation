from validator.validator_from_andrews.corpora import Actions


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
'''.strip()

def prompt_background(clue_type=None, num_examples=1):
  prompt_background = f'''

  You are a cryptic crossword compiler and formal verifier.

  Your task is to generate an original cryptic crossword clue {(f"(of a {clue_type} type)" if clue_type is not None else "")} together with a
  FORMAL, STRUCTURED PROOF of the wordplay.

  ---
  Available Proof Functions / Concepts

  The following are the ONLY allowed semantic operations in the proof.
  Do not invent new operations.

  {function_defs}

  All proof steps must correspond to these operations.

  ---
  Clue Requirements

  - Use British cryptic crossword conventions.
  - The clue must contain EXACTLY ONE definition.
  - The surface reading must be natural English.
  - The answer length must match the pattern.

  ---
  Required Output Format (MANDATORY)

  The contents must follow this structure:

  {chr(10).join(str(item) for item in get_example_of_correct_type(clue_type=clue_type, num_examples=num_examples))}

  ---
  Constraints

  - You MUST use a ```python``` block, with both opening and closing backticks
  - Use ONLY operations specified above.
  - Do NOT use any variables. Each line of code must be independent from one another.
  - Do NOT use any curly braces to indiciate definition words.
  - Do NOT include any text outside the multiline string.
  - Do NOT omit intermediate steps.

  ---
  Task

  Generate one original cryptic crossword clue {(f"(of a {clue_type} type)" if clue_type is not None else "")}
  and its complete structured proof that satisfies all of the above constraints.

  Output must start with exactly three backticks, the word python, then a newline.
  End the output with exactly three backticks on a line by themselves.
  Do not omit these backticks under any circumstances.
  '''

  return [prompt_background]


def get_example_of_correct_type(clue_type, num_examples=1):
  example = ""

  clue_type = clue_type.upper() if clue_type is not None else clue_type

  match (clue_type):
    case "ANAGRAM":
      example =   '''
                  ```python
                    def proof(answer="DECIMAL", clue="the point of medical treatment", pattern='7'):
                      answer = "DECIMAL"
                      clue = "The point of medical treatment"
                      pattern = 7

                      """
                      definition: {the point} of medical treatment
                      wordplay: (MEDICAL)* (*treatment = anagram) 
                      """

                      assert is_synonym("the point", "DECIMAL", pattern='7')
                      assert action_type("treatment", Action.ANAGRAM)
                      assert is_anagram("MEDICAL", "DECIMAL")
                  ```
                  '''
      example_2 = '''
                  ```python
                    def proof(answer="OCEANIA", clue="A canoe I adapted for Pacific region", pattern='7'):
                      """
                      definition: pacific region
                      wordplay: A CANOE I (anagram)
                      """
                      
                      # Check if the answer is a synonym for 'pacific region'
                      assert is_synonym("pacific region", "OCEANIA", pattern='7')
                      
                      # Check if the clue suggests an anagram action
                      assert action_type("adapted", Action.ANAGRAM)
                      
                      # Verify that 'OCEANIA' can be arranged from the letters of 'A CANOE I'
                      assert is_anagram("A CANOE I", "OCEANIA")
                  ```
                  '''
      example_3 = '''
                  ```python
                    def proof(answer="REGULATOR", clue="A ruler got mistaken for governor", pattern='9'):
                      """
                      definition: governor
                      wordplay: A RULER GOT (anagram)
                      """
                      assert is_synonym("governor", "REGULATOR", pattern='9')
                      assert action_type("mistaken", Action.ANAGRAM)
                      assert is_anagram("A RULER GOT", "REGULATOR")
                  ```
                  '''
      example_4 = '''
                  ```python
                    def proof(answer="OPPORTUNIST", clue="Moving up into sport, one seeing opening", pattern='11'):
                        """
                        definition: one seeing opening
                        wordplay: (UP INTO SPORT)* (*Moving = anagram) 
                        """
                        assert is_synonym("one seeing opening", "OPPORTUNIST", pattern='11')
                        assert action_type("Moving", Action.ANAGRAM)
                        assert is_anagram("UP INTO SPORT", "OPPORTUNIST")
                  ```
                  '''
      example_5 = '''
                  ```python
                    def proof(answer="PERSONALITIES", clue="Celebrities are pointless, I suspect", pattern='13'):
                      """
                      definition: celebrities
                      wordplay: ARE POINTLESS I (anagram)
                      """
                      assert is_synonym("celebrities", "PERSONALITIES", pattern='13')
                      assert action_type("suspect", Action.ANAGRAM)
                      assert is_anagram("ARE POINTLESS I", "PERSONALITIES")
                  ```
                  '''
    case "CONTAINER":
      example = '''
                ```python
                  def proof(answer="SUPERMARKET", clue="Fat bags for every brand that’s a big seller", pattern='11'):

                      """
                      definition: fat bags for every brand that’s {a big seller}
                      wordplay: SUET (fat) (bags = goes outside) of (PER (for every) + MARK (brand)) 
                      """
                      
                      assert is_synonym("fat", "SUET")
                      assert action_type("bags", Action.GOES_OUTSIDE)
                      assert "SUET" == "SU" + "ET"
                      assert is_abbreviation("for every", "PER")
                      assert is_synonym("brand", "MARK")
                      assert "SU" + "PER" + "MARK" + "ET" == "SUPERMARKET"
                      assert is_synonym("a big seller", "SUPERMARKET", pattern='11')
                ```
                '''
      example_2 = '''
                  ```python
                    def proof(answer="BRITTEN", clue="Composer plagued by mosquitoes crossing river", pattern='7'):
                      """
                      definition: composer
                      wordplay: BITTEN (plagued by mosquitoes) put inside (crossing) R (river)
                      """ 
                      assert is_synonym("composer", "BRITTEN", pattern='7')
                      assert is_synonym("plagued by mosquitoes", "BITTEN")
                      assert action_type("crossing", Action.GOES_INSIDE)
                      assert is_abbreviation("river", "R")
                      assert "BITTEN" == "B" + "ITTEN" 
                      assert "B" + "R" + "ITTEN" == "BRITTEN"
                  ```
                  '''
      example_3 = '''
                  ```python
                    def proof(answer="EMU", clue="Australian native, Mike, visiting European Union", pattern='3'):
                      """ 
                      definition: australian native
                      wordplay: M (mike) goes inside (visiting) EU (european union)
                      """
                      assert is_synonym("australian native", "EMU", pattern='3')
                      assert is_abbreviation("Mike", "M")
                      assert is_synonym("European Union", "EU")
                      assert action_type("visiting", Action.GOES_INSIDE)
                      assert "E" + "M" + "U" == "EMU"  # Fixed to correctly represent the insertion
                  ```
                  '''
      example_4 = '''
                  ```python
                    def proof(answer="AWKWARD", clue="Difficult week, Grant admits", pattern='7'):
                      """
                      definition: difficult
                      wordplay: (AWARD) (grant) surrounds (admits) WK (week)
                      """
                      assert is_synonym("difficult", "AWKWARD", pattern='7')
                      assert is_synonym("grant", "AWARD")
                      assert action_type("admits", Action.GOES_INSIDE)
                      assert is_abbreviation("week", "WK")
                      assert "AWARD" == "AW" + "ARD"
                      assert "AW" + "WK" + "ARD" == "AWKWARD"
                  ```
                  '''
      example_5 = '''
                  ```python
                    def proof(answer="SCABBIEST", clue="Most despicable taxi drivers blocking street", pattern='9'):
                      """
                      definition: most despicable
                      wordplay: CABBIES (taxi drivers) put inside (S + T) (street) 
                      """
                      assert is_synonym("most despicable", "SCABBIEST", pattern='9')
                      assert is_synonym("taxi drivers", "CABBIES")
                      assert action_type("blocking", Action.GOES_INSIDE)
                      assert is_abbreviation("street", "ST")
                      assert "S" + "CABBIES" + "T" == "SCABBIEST"
                  ```
                  '''
    case "CHARADE":
      example = '''
                ```python
                  def proof(answer="RELIABLE", clue="Dependable about being under an obligation?", pattern='8'):

                      """
                      definition: {dependable} about being under an obligation?
                      wordplay: RE (about) + LIABLE (being under an obligation) 
                      """
                      
                      assert is_synonym("dependable", "RELIABLE", pattern='8')
                      assert is_abbreviation("about", "RE")
                      assert is_synonym("being under an obligation", "LIABLE")
                      assert "RE"+"LIABLE"=="RELIABLE"
                ```
                '''
      example_2 = '''
                  ```python
                    def proof(answer="AWARD", clue="Honour a hospital department", pattern='5'):
                      """
                      definition: honour
                      wordplay: A + WARD (hospital department)
                      """
                      assert is_synonym("honour", "AWARD", pattern='5')
                      assert is_synonym("hospital department", "WARD")
                      assert "A" + "WARD" == "AWARD"
                  ```
                  '''
      example_3 = '''
                  ```python
                    def proof(answer="INCH", clue="Move slowly in church", pattern='4'):
                      """
                      definition: move slowly
                      wordplay: IN + CH (church)
                      """
                      assert is_synonym("move slowly", "INCH", pattern='4')
                      assert action_type("in", Action.GOES_NEXT_TO)
                      assert is_synonym("church", "CH")
                      assert "IN" + "CH" == "INCH"
                  ```
                  '''
      example_4 = '''
                  ```python
                    def proof(answer="CONE", clue="Firm, northeastern, solid", pattern='4'):
                      """
                      definition: solid
                      wordplay: CO (firm) + NE (northeastern)
                      """
                      assert is_synonym("solid", "CONE", pattern='4')
                      assert is_synonym("firm", "CO") 
                      assert is_abbreviation("northeastern", "NE")
                      assert "CO" + "NE" == "CONE"
                  ```
                  '''
      example_5 = '''
                  ```python
                    def proof(answer="CONTACT", clue="Meeting prisoner with diplomacy", pattern='7'):
                      """
                      definition: meeting
                      wordplay: CON (prisoner) + TACT (diplomacy)
                      """
                      assert is_synonym("meeting", "CONTACT", pattern='7')
                      assert is_synonym("prisoner", "CON")
                      assert is_synonym("diplomacy", "TACT")
                      assert "CON" + "TACT" == "CONTACT"
                  ```
                  '''
    case "DOUBLE_DEFINITION":
      example = '''
                ```python
                  def proof(answer="BALL", clue="Great time for bouncer?", pattern='4'):
                  
                    """
                    definition: great time
                    wordplay: double definition. great time // bouncer
                    """

                    assert is_synonym("great time", "BALL", pattern='4')
                    assert is_synonym("bouncer", "BALL")
                ```
                '''
      example_2 = '''
                  ```python
                    def proof(answer="LIE", clue="Get down story", pattern='3'):
                      """
                      definition: get down
                      wordplay: double definition. get down // story
                      """
                      assert is_synonym("get down", "LIE", pattern='3')
                      assert is_synonym("story", "LIE", pattern='3')
                  ```
                  '''
      example_3 = '''
                  ```python
                    def proof(answer="LIE", clue="Get down story", pattern='3'):
                      """
                      definition: get down
                      wordplay: double definition. get down // story
                      """
                      assert is_synonym("get down", "LIE", pattern='3')
                      assert is_synonym("story", "LIE", pattern='3')
                  ```
                  '''
      example_4 = '''
                  ```python
                    def proof(answer="IN ORDER", clue="Straight, as might be a nun?", pattern='2,5'):
                      """
                      definition: straight
                      wordplay: double definition. straight // as might be a nun?
                      """
                      assert is_synonym("straight", "IN ORDER", pattern='2,5')
                      assert is_synonym("as might be a nun?", "IN ORDER")
                  ```
                  '''
      example_5 = '''
                  ```python
                    def proof(answer="REUNION", clue="Meeting of old friends in French island", pattern='7'):
                      """
                      definition: meeting of old friends
                      wordplay: double definition. French island called Reunion // meeting of old friends
                      """
                      assert is_synonym("meeting of old friends", "REUNION", pattern='7')
                      assert is_synonym("French island", "REUNION")
                  ```
                  '''
    case "HIDDEN":
      example = '''
                ```python
                  def proof(answer="SAP", clue="Some ignoramus, a proper idiot!", pattern='3'):

                    """
                    definition: idiot
                    wordplay: some (ignoramu)S A P(roper)
                    
                    """
                    assert is_synonym("idiot", "SAP", pattern='3')
                    assert action_type("Some", Action.SUBSTRING)
                    assert "SAP" in "IGNORAMUS A PROPER".replace(" ", "")
                ```
                '''
      example_2 = '''
                  ```python
                    def proof(answer="MINOR", clue="Less important vitamin — order reduced", pattern='5'):
                      """
                      definition: less important
                      wordplay: (vita)MIN — OR(der) reduced
                      """ 
                      assert is_synonym("less important", "MINOR", pattern='5')
                      assert action_type("reduced", Action.SUBSTRING)
                      assert "MINOR" in "VITAMIN ORDER".replace(" ", "")
                  ```
                  '''
      example_3 = '''
                  ```python
                    def proof(answer="CAB", clue="Vehicle seen in America, Britain", pattern='3'):
                      """
                      definition: vehicle
                      wordplay: seen in (ameri)CA B(ritain)
                      """
                      assert is_synonym("vehicle", "CAB", pattern='3')
                      assert action_type("seen in ", Action.SUBSTRING)
                      assert "CAB" in "AMERICA BRITAIN".replace(" ", "")
                  ```
                  '''
      example_4 = '''
                  ```python
                    def proof(answer="PINCH", clue="Contribution to hardship in Chelmsford nick", pattern='5'):
                      """
                      definition: nick
                      wordplay: contribution to (hardshi)P IN CH(elmsford)
                      """ 
                      assert is_synonym("nick", "PINCH", pattern='5')
                      assert action_type("contribution", Action.SUBSTRING)
                      assert "PINCH" in "HARDSHIP IN CHELMSFORD".replace(" ", "")
                  ```
                  '''
      example_5 = '''
                  ```python
                    def proof(answer="CANTONESE", clue="Partially recant one’s explicit language", pattern='9'):
                      """
                      definition: language
                      wordplay: partially (re)CANT ONES E(xplicit)
                      """
                      assert is_synonym("language", "CANTONESE", pattern='9')
                      assert action_type("Partially", Action.SUBSTRING)
                      assert "CANTONESE" in "RECANT ONES EXPLICIT".replace(" ", "")
                  ```
                  '''
    case "DELETION":
      example = '''
                ```python
                  def proof(answer="BOO", clue="Voice criticism of short novel?", pattern='3'):
                    """
                    definition: voice criticism
                    wordplay: short BOOK (novel) = BOO
                    """

                    assert is_synonym("voice criticism", "BOO") 
                    assert is_synonym("novel", "BOOK", pattern='4')
                    assert action_type("short", Action.REMOVE_LAST)
                    assert "BOOK"[:-1] == "BOO"
                ```
                '''
      example_2 = '''
                  ```python
                    def proof(answer="LONE", clue="Single copy not initiated", pattern='4'):
                      """
                      definition: single
                      wordplay: not initiated CLONE (copy) -> LONE
                      """
                      assert is_synonym("single", "LONE", pattern='4')
                      assert action_type("not initiated", Action.REMOVE_FIRST)
                      assert "CLONE"[1:] == "LONE"
                      assert is_synonym("copy", "CLONE")
                  ```
                  '''
      example_3 = '''
                  ```python
                    def proof(answer="ANGER", clue="Daughter escaping peril shows passion", pattern='5'):
                      """
                      definition: passion
                      wordplay: DANGER (peril) - D (daughter) = ANGER
                      """
                      assert is_synonym("passion", "ANGER", pattern='5')
                      assert is_synonym("peril", "DANGER")
                      assert is_synonym("daughter", "D")
                      assert action_type("escaping", Action.REMOVE_SUBSTRING)
                      assert "DANGER"[1:] == "ANGER"
                  ```
                  '''
      example_4 = '''
                  ```python
                    def proof(answer="MORAL", clue="No time for human message from story", pattern='5'):
                      """
                      definition: message from story
                      wordplay: MORTAL (human) - T (time) = MORAL
                      """
                      assert is_synonym("message from story", "MORAL", pattern='5')
                      assert is_synonym("human", "MORTAL")
                      assert action_type("No time for", Action.REMOVE_SUBSTRING)
                      assert "MORTAL".replace("T", "") == "MORAL"
                  ```
                  '''
      example_5 = '''
                  ```python
                    def proof(answer="ROUND", clue="Ignoring its tip, earth’s spherical", pattern='5'):
                      """
                      definition: spherical
                      wordplay: GROUND (earth) ignoring G (its tip) = ROUND
                      """
                      assert is_synonym("spherical", "ROUND", pattern='5')
                      assert is_synonym("earth", "GROUND")
                      assert action_type("Ignoring its tip", Action.REMOVE_FIRST)
                      assert "GROUND"[1:] == "ROUND"
                  ```
                  '''
    case "HOMOPHONE":
        example = '''
                  ```python
                  def proof(answer="CAESER", clue="Arrest that woman, said Roman leader?", pattern='6'):
                      """
                      definition: Roman leader
                      wordplay: homophone of 'seize her' (arrest that woman) = CAESAR
                      """
                      assert is_synonym("Roman leader", "CAESER", pattern='6')
                      assert is_synonym("Arrest that woman", "seize her")
                      assert action_type("said", Action.HOMOPHONE)
                      assert is_homophone("seize her", "CAESER")
                  ```
                  '''
        example_2, example_3, example_4, example_5 = None, None, None, None
    case "ANAGRAM_AND_CHARADE":
        example = '''
                  ```python
                  def proof(answer="LOURDES", clue="Learner so rude about holy site in France", pattern='7'):
                      """
                      definition: holy site in France
                      wordplay: L (learner) + (SO RUDE)* (*about = anagram)
                      """
                      assert is_synonym("LOURDES", "holy site in France", pattern='7')
                      assert is_abbreviation("Learner", "L")
                      assert action_type("about", Action.ANAGRAM)
                      assert is_anagram("so rude", "OURDES")
                      assert "L" + "OURDES" == "LOURDES"
                  ```
                  '''
        example_2, example_3, example_4, example_5 = None, None, None, None
    case "CHARADE_AND_DELETION":
        example = '''
                  ```python
                  def proof(answer="BECOMING", clue="Attractive tailless insect approaching", pattern='8'):
                      """
                      definition: attractive
                      wordplay: BEE (insect) - E (tailless) + COMING (approaching)
                      """
                      assert is_synonym("attractive", "BECOMING", pattern='8')
                      assert is_synonym("insect", "BEE")
                      assert action_type("tailless", Action.REMOVE_LAST)
                      assert "BEE"[-1] = "BE"
                      assert is_synonym("approaching", "COMING")
                      assert "BE" + "COMING" == "BECOMING"
                  ```
                  '''
        example_2, example_3, example_4, example_5 = None, None, None, None
    case "CHARADE_AND_CONTAINER":
        example = '''
                  ```python
                  def proof(answer="THRILLED", clue="The daughter crossing stream is very happy", pattern='8'):
                      """
                      definition: very happy
                      wordplay: THE D (the daughter) surrounds RILL (stream)
                      """
                      assert is_synonym("very happy", "THRILLED", pattern='8')
                      assert is_synonym("the", "THE")
                      assert is_abbreviation("daughter", "D")
                      assert "THE" + "D" == "TH" + "ED"
                      assert is_synonym("river", "RILL")
                      assert action_type("crossing", Action.GOES_OUTSIDE)
                      assert "TH" + "RILL" + "ED" == "THRILLED"
                  ```
                  '''
        example_2, example_3, example_4, example_5 = None, None, None, None
    case _ :
      # mixed clue
      example = '''
                ```python
                  def proof(answer="ENROL", clue="Record single about maintaining resistance", pattern='5'):
                    """
                    definition: {Record} single about maintaining resistance
                    wordplay: (LONE)< (single, <about) maintaining R (resistance) 
                    """
                    assert is_synonym("record", "ENROL", pattern='5')
                    assert is_synomym("single", "LONE")
                    assert action_type("about", Action.REVERSE) and "LONE"[::-1] == "ENOL"
                    assert action_type("maintaining", Action.GOES_OUTSIDE)
                    assert is_abbreviation("resistance", "R")
                    assert "ENOL" == "EN" + "OL"
                    assert "EN" + "R" + "OL" == "ENROL"
                ```
                '''
      example_2, example_3, example_4, example_5 = None, None, None, None
  examples = [example, example_2, example_3, example_4, example_5]
  return examples[:num_examples]
  

# create function for rewrites
def prompt_report_previous_errors(py, report_full):
  prompt_report_errors = f'''
  # The following draft code SOLUTION was returned for a cryptic crossword clue and proof:
  ```python
  {py}proof()
  ```
  # PROBLEM : the SOLUTION above failed because of the following reported errors (python assertions without errors were valid):
  ```
  {report_full}
  ``` 
  # Please re-implement the SOLUTION above (altering the docstring/ clue/ python proof as required), taking care to fix each of the problems identified, and keep a good quality clue. Return the whole function.
  '''

  return [prompt_report_errors]


def prompt_report_evaluation(py, clue_evaluation_report):
    prompt_report_evaluation = f'''
    # The following draft code SOLUTION was returned for a cryptic crossword clue and proof:
    ```python
    {py}proof()
    ```
    # PROBLEM : the SOLUTION above passed all assertions, but the clue does not sound enough like a normal sentence.

    {clue_evaluation_report}
    
    # Please re-implement the SOLUTION above (altering the docstring/ clue/ python proof as required), taking care to fix each of the problems identified, and keep a good quality clue. 
    Return the whole function, and still define clue="xxx" in the function arguments.
    '''

    return [prompt_report_evaluation]

