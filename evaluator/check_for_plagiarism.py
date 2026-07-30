import requests

SEARCH_URL = "https://google.serper.dev/search"

SERPER_API_KEY = "a7023366529f14ed84e10b9b463b0615d443b8d5"

HEADERS = {
    "X-API-KEY": SERPER_API_KEY,
    "Content-Type": "application/json"
}


def plagiarism_match(clue):
    """
    Returns True if Google finds an exact match for the clue.
    """
    payload = {
        "q": f'"{clue}"',
        "num": 1
    }

    r = requests.post(
        SEARCH_URL,
        headers=HEADERS,
        json=payload,
        timeout=30,
    )

    r.raise_for_status()

    results = r.json().get("organic", [])

    return len(results) > 0




# import csv
# import time
# import requests

# SERPER_API_KEY = "a7023366529f14ed84e10b9b463b0615d443b8d5"

# SEARCH_URL = "https://google.serper.dev/search"

# HEADERS = {
#     "X-API-KEY": SERPER_API_KEY,
#     "Content-Type": "application/json"
# }


# def parse_line(line):
#     """Extract answer, clue and clue type from one line."""
#     parts = line.strip().split()

#     if len(parts) < 3:
#         return None

#     answer = parts[0]
#     clue_type = parts[-1]
#     clue = " ".join(parts[1:-1])

#     return answer, clue, clue_type


# def search_clue(clue):
#     """Search Google via Serper."""
#     payload = {
#         "q": f'"{clue}"',
#         "num": 5
#     }

#     r = requests.post(
#         SEARCH_URL,
#         headers=HEADERS,
#         json=payload,
#         timeout=30,
#     )

#     r.raise_for_status()

#     data = r.json()

#     return data.get("organic", [])


# experiment_names = ["gpt4_no_validator",
#                     "gpt5_no_validator",
#                     "gpt5_with_validator"]


# def main():
#     for experiment_name in experiment_names:

#       with open(f"logfiles/{experiment_name}/clues.txt", encoding="utf-8") as infile, \
#           open(f"validator/plagiarism_report_{experiment_name}.csv", "w", newline="", encoding="utf-8") as outfile:

#           writer = csv.writer(outfile)

#           writer.writerow([
#               "Answer",
#               "Clue",
#               "Type",
#               "Matches",
#               "URLs"
#           ])

#           for line in infile:

#               if not line.strip():
#                   continue

#               parsed = parse_line(line)

#               if parsed is None:
#                   continue

#               answer, clue, clue_type = parsed

#               print(f"Searching: {clue}")

#               try:
#                   results = search_clue(clue)

#                   urls = [r["link"] for r in results]

#                   writer.writerow([
#                       answer,
#                       clue,
#                       clue_type,
#                       len(results),
#                       "; ".join(urls)
#                   ])

#               except Exception as e:
#                   print(e)
#                   writer.writerow([
#                       answer,
#                       clue,
#                       clue_type,
#                       "ERROR",
#                       str(e)
#                   ])

#               # Avoid hitting rate limits
#               time.sleep(1)


# if __name__ == "__main__":
#     main()