
def classify_error(line: str) -> str:
    if "is_synonym(" in line:
        return "synonym errors"
    if "is_abbreviation(" in line:
        return "abbreviation errors"
    if "action_type(" in line:
        return "action errors"
    if "unused" in line.lower():
        return "unused word errors"
    # default: string / structural mismatch
    return "string errors"


def update_stats(stats, report, clue_num, ERROR_TYPES, num_all_rewrites_for_clue, num_quality_rewrites_for_clue):
  # LOG STATS FOR THIS CLUE
  stats["total_num_writes"] += num_all_rewrites_for_clue + 1
  stats["total_num_quality_rewrites"] += num_quality_rewrites_for_clue
  stats["per clue stats"][clue_num, 0] = num_all_rewrites_for_clue
  stats["per clue stats"][clue_num, 1] = num_quality_rewrites_for_clue

  if len(report) == 0:
    stats["num_successful"] += 1
  else:
    stats["num_failed"] += 1  
    for line in report:
        category = classify_error(line)
        stats["errors"][category] += 1
        col_idx = ERROR_TYPES.index(category)
        stats["per clue stats"][clue_num, col_idx + 2] += 1  

  return stats


def log_something(logfile, rewrite_num, log_type, thing_to_log):
  logfile.write(f"\n#REWRITE#:{rewrite_num:d}:{log_type}-START::\n")
  logfile.write( f"\n {thing_to_log}\n" )
  logfile.write(f"\n#{log_type}-END#")


def get_arg_from_dsl(code, arg_name):
    import ast

    tree = ast.parse(code)

    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "proof":
            args = node.args
            arg_names = [a.arg for a in args.args]
            defaults = args.defaults

            for name, default in zip(arg_names[-len(defaults):], defaults):
                if name == arg_name:
                    if isinstance(default, ast.Constant):
                        return default.value
                    raise ValueError(f"{arg_name} must be a literal")

    return None


# def get_clue_from_dsl(code):
#     import ast
#     try:
#         tree = ast.parse(code)
#     except SyntaxError as e:
#         print(f"Syntax error in DSL: {e}")
#         return None

#     # Expect exactly one top-level function: proof
#     for node in tree.body:
#         if isinstance(node, ast.FunctionDef) and node.name == "proof":
#             args = node.args

#             # Positional args with defaults
#             if not args.defaults:
#                 return None

#             # Align arg names with defaults
#             arg_names = [a.arg for a in args.args]
#             defaults = args.defaults
#             default_names = arg_names[-len(defaults):]

#             for name, default in zip(default_names, defaults):
#                 if name == "clue":
#                     if isinstance(default, ast.Constant) and isinstance(default.value, str):
#                         return default.value
#                     else:
#                         raise ValueError("clue must be a literal string")

#     return None