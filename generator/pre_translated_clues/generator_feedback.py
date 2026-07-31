from evaluator.perplexity import compute_perplexity
# other metrics here


THRESHOLDS = {
  "perplexity" : 500
}


def get_clue_evaluation(clue_text):
  '''
  Returns a string explaining what is wrong with the clue, and ideas of how to fix it
  '''
  clue_stats = compute_clue_stats(clue_text)
  compare = compare_to_thresholds(clue_stats) 

  return generate_report(compare)



def compute_clue_stats(clue_text):
  '''
  Returns a dictionary with each metric and that metric's value
  '''

  perplexity = compute_perplexity(clue_text)

  return {"perplexity": perplexity}



def compare_to_thresholds(clue_stats):

  '''
  Returns a dictionary with each metric, with value True is that metric is within thresholds and False if not
  '''

  metric_checks = {}
  for metric in clue_stats.keys():
    if clue_stats[metric] > THRESHOLDS[metric]: # FOR PERPLEXITY, LOWER IS BETTER
      metric_checks[metric] = False
    else:
      metric_checks[metric] = True
  return metric_checks



def generate_report(metric_checks):
  report = ""
  for metric, is_ok in metric_checks.items():
    if not is_ok:
      report += '''The clue does not sound natural enough. 
                    Please make the clue sound more like a natural English sentence, 
                    BUT MAKE SURE THE WORDPLAY OF THE CLUE REMAINS VALID.

                    Here are some changes you could make:
                     - Use a more natural sounding indicator word
                     - Swap the order of the wordplay and definition.
                     - Add punctuation to change the meaning.
                     - Adding or removing article words.
      '''

  if report == "":
    return None
  else:
    return report
