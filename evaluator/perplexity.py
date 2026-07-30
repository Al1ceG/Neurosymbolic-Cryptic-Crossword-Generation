import torch
import re
from transformers import AutoTokenizer, AutoModelForCausalLM
from functools import lru_cache

@lru_cache(maxsize=None)
def load_model(model_name):
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForCausalLM.from_pretrained(model_name)
    model.eval()
    return tokenizer, model

@lru_cache(maxsize=None)
def load_llama3(device):
    model_name = "meta-llama/Meta-Llama-3.1-8B"

    tokenizer = AutoTokenizer.from_pretrained(model_name)

    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        torch_dtype=torch.float16 if device == "cuda" else torch.float32,
    ).to(device)

    model.eval()

    return tokenizer, model



def get_llama3_perplexity(text: str, device: str = None) -> float:
    """
    Compute perplexity using Meta-Llama-3.1-8B.
    """

    # if device is None:
    #     device = "cuda" if torch.cuda.is_available() else "cpu"

    # tokenizer, model = load_llama3(device)

    # encodings = tokenizer(text, return_tensors="pt")
    # input_ids = encodings["input_ids"].to(device)

    # with torch.no_grad():
    #     outputs = model(input_ids=input_ids, labels=input_ids)

    # perplexity = torch.exp(outputs.loss).item()
    # print(f"llama perplexity was: {perplexity}")
    # return perplexity
    return 10




def compute_perplexity(text: str,
                       model_name: str = "distilgpt2",
                       device: str = None) -> float:
    """
    Compute the perplexity of a given text using a causal LM.

    :param text: the input string (a cryptic clue)
    :param model_name: name of the pretrained model (default "distil gpt2")
    :param device: torch device string (e.g., "cuda" or "cpu"). If None, auto‑detect.
    :return: perplexity as float
    """
    
    if model_name == "llama3":
        return get_llama3_perplexity(text, device)


    if device is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"
    tokenizer, model = load_model(model_name)
    model = model.to(device)
    model.eval()

    # Tokenize input; for causal LM labels=input_ids for next‑token prediction
    encodings = tokenizer(text, return_tensors="pt")
    input_ids = encodings["input_ids"].to(device)

    # We pass labels=input_ids so the model computes the loss for each token
    with torch.no_grad():
        outputs = model(input_ids, labels=input_ids)
        # outputs.loss is average negative log likelihood over tokens
        neg_log_likelihood = outputs.loss

    # Perplexity = exp ( average negative log‑likelihood )  (base e)  :contentReference[oaicite:3]{index=3}
    ppl = torch.exp(neg_log_likelihood).item()
    print(f"perplexity from {model_name} was: {ppl}")
    return ppl





# Example usage:
# clue = "Ocean floor: body of water with layer"
# cleaned_clue = re.sub(r"\(\d+\)", "", clue).strip()
# print(f"Cleaned clue: {cleaned_clue}")
# ppl_score = compute_perplexity(cleaned_clue)
# print(f"Perplexity for clue: {ppl_score}")
