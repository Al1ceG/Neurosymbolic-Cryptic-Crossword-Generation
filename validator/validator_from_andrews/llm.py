from omegaconf import OmegaConf
import time
from openai import InternalServerError
# from genai_pricing.genai_pricing import openai_client, openai_prompt_cost

conf = OmegaConf.load('config.yaml')


def get_model_gemini(model_name="gemini-1.5-flash-001", free=False):  # gemini-1.5-flash
  if free:
    # This is the 'free' version (not VertexAI)
    import google.generativeai as genai
    from google.generativeai import GenerativeModel
    genai.configure(api_key=conf.APIKey.GEMINI_PUBLIC)
    print(f"'...{conf.APIKey.GEMINI_PUBLIC}[-6:]'")
  # https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/configure-safety-attributes#configure_thresholds
    safety_settings = [ {
        "category": "HARM_CATEGORY_HARASSMENT",
        "threshold": "BLOCK_ONLY_HIGH"
      },  {
        "category": "HARM_CATEGORY_HATE_SPEECH",
        "threshold": "BLOCK_ONLY_HIGH"
      },  {
        "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
        "threshold": "BLOCK_ONLY_HIGH"
      },  {
        "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
        "threshold": "BLOCK_ONLY_HIGH"
      },
    ]
    
  else:
    #  export GOOGLE_APPLICATION_CREDENTIALS="key-vertexai-iam.json"
    import vertexai
    from vertexai.generative_models import GenerativeModel, HarmCategory, HarmBlockThreshold
    PROJECT_ID = conf.APIKey.VERTEX_AI.PROJECT_ID
    REGION     = conf.APIKey.VERTEX_AI.REGION  # e.g. us-central1 or asia-southeast1
    vertexai.init(project=PROJECT_ID, location=REGION) 
    safety_settings = {
      HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_ONLY_HIGH,  # BLOCK_NONE is not allowed...
      HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_ONLY_HIGH,
      HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
      HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
    }    
  
  # Set up the model
  #   https://cloud.google.com/vertex-ai/generative-ai/docs/model-reference/gemini#:~:text=Top-K%20changes
  generation_config = {
    "temperature": 1.0,  # Default for gemini-1.0-pro-002
    "top_p": 1,  # Effectively look at all probabilities
    #"top_p": .9,  # Focus more on top probs
    #"top_k": 1,  # Not used by gemini-pro-1.0 (!)
    "max_output_tokens": 2048,
  }
  
  return GenerativeModel(model_name=model_name,
                         generation_config=generation_config,
                         safety_settings=safety_settings,
                        )  


get_model = get_model_gemini



from openai import OpenAI

def get_model_openai(model_name="gpt-4o-mini", temperature=1.0, top_p=1.0, max_tokens=16384):
    if model_name == "llama3":
       model_name = "meta-llama/Llama-3.3-70B-Instruct"
    elif model_name == "gpt-5":
       model_name = "gpt-5.2-2025-12-11"

    if model_name.startswith("meta-llama/"):
        client = OpenAI(
            base_url="https://elm.edina.ac.uk/api/v1",
            api_key=conf.APIKey.ELM_SECRET,
        )
        backend = "chat"

    else:
        client = OpenAI(
            api_key=conf.APIKey.OPENAI_SECRET
        )
        backend = "responses"

    def generate_content(prompt, **kwargs):

        if backend == "chat":
            for attempt in range(5):
              try:
                  response = client.chat.completions.create(
                  model=model_name,
                  messages=[
                      {"role": "user", "content": str(prompt)}
                  ],
                  # temperature=kwargs.get("temperature", temperature),
                  # top_p=kwargs.get("top_p", top_p),
                  max_tokens=kwargs.get("max_tokens", max_tokens)
                  )
                  break
              except InternalServerError as e:
                  if attempt == 4:
                      raise
                  wait = 2 ** attempt
                  print(f"Server error, retrying in {wait}s...")
                  time.sleep(wait)
    
            return response.choices[0].message.content.strip()

        else:
            response = client.responses.create(
                model=model_name,
                input=str(prompt),
                # temperature=kwargs.get("temperature", temperature),
                max_output_tokens=kwargs.get("max_tokens", max_tokens),
                # top_p=kwargs.get("top_p", top_p),
            )

            return response.output_text.strip()

    return generate_content



# def get_model_openai(model_name="gpt-4o-mini", temperature=1.0, top_p=1.0, max_tokens=16384):
#     """
#     Initializes an OpenAI model (GPT-5, GPT-4.1, GPT-4o, etc.)
#     using the modern Responses API, robustly extracting text.
#     """

#     from openai import OpenAI

#     client = OpenAI(api_key=conf.APIKey.OPENAI_SECRET)
#     print(f"Using paid OpenAI key: ...{conf.APIKey.OPENAI_SECRET[-6:]}")

#     generation_config = {
#         "model": model_name,
#         "temperature": temperature,
#         "max_tokens": max_tokens,
#         "top_p": top_p,
#     }

#     def generate_content(prompt, **kwargs):
#         params = {
#           "model": generation_config["model"],
#           "input": str(prompt),
#           "temperature": kwargs.get("temperature", generation_config["temperature"]),
#           "max_output_tokens": kwargs.get("max_tokens", generation_config["max_tokens"]),
#         }

#         # Only include top_p for non-Pro models
#         if "pro" not in generation_config["model"]:
#             params["top_p"] = kwargs.get("top_p", generation_config["top_p"])

#         # Enable stronger reasoning for Pro
#         if "pro" in generation_config["model"]:
#             params["reasoning"] = {
#                 "effort": kwargs.get("reasoning_effort", "high")
#             }

#         response = client.responses.create(**params)

#         # # GET ESTIMATE OF PRICE
#         # answer = response.output_text
#         # estimate = openai_prompt_cost(model_name, prompt, answer, response) # <- use this line in your project
#         # print("Cost (USD):", estimate["total_cost"])
#         # print("Details:", estimate)

#         # Try the convenient output_text first
#         text = response.output_text or ""

#         # If empty, robustly extract all text from structured output
#         if not text.strip() and hasattr(response, "output") and response.output:
#             chunks = []
#             for item in response.output:
#                 if getattr(item, "type", None) == "message":
#                     for content in getattr(item, "content", []):
#                         if content.get("type") == "output_text" and content.get("text"):
#                             chunks.append(content["text"])
#             text = "\n".join(chunks)

#         # Final fallback: log if still empty
#         if not text.strip():
#             print("WARNING: Model returned no text output!")
#             print("Raw response object:", response)

#         return text.strip()
    

#     return generate_content


# def get_model_openai(model_name="gpt-4o-mini"):
#     """
#     Initializes an OpenAI model (GPT-5, GPT-4.1, GPT-4o, etc.)
#     using the modern Responses API, with backward compatibility.
#     """

#     from openai import OpenAI

#     client = OpenAI(api_key=conf.APIKey.OPENAI_SECRET)
#     print(f"Using paid OpenAI key: ...{conf.APIKey.OPENAI_SECRET[-6:]}")

#     generation_config = {
#         "model": model_name,
#         "temperature": 1.0,
#         "max_tokens": 2048,
#         "top_p": 1.0,
#     }

#     def generate_content(prompt, **kwargs):
#         response = client.responses.create(
#             model=generation_config["model"],
#             input=str(prompt),
#             temperature=kwargs.get("temperature", generation_config["temperature"]),
#             max_output_tokens=kwargs.get("max_tokens", generation_config["max_tokens"]),
#             top_p=kwargs.get("top_p", generation_config["top_p"]),
#         )

#         # Safely extract text output
#         return response.output_text

#     return generate_content


def get_model_openai_old(model_name="gpt-4o-mini"):
    """
    Initializes an OpenAI model for text or multimodal generation.
    """

    # For production / paid access
    import openai
    from openai import OpenAI
    openai.api_key = conf.APIKey.OPENAI_SECRET
    print(f"Using paid OpenAI key: ...{conf.APIKey.OPENAI_SECRET[-6:]}")

    # Configure the client
    client = OpenAI(api_key=openai.api_key)

    # Define generation defaults (similar to your Gemini config)
    generation_config = {
        "model": model_name,
        "temperature": 1.0,
        "max_tokens": 2048,
        "top_p": 1.0,
    }

    # Return a wrapper for easier use
    def generate_content(prompt, **kwargs):
      completion = client.chat.completions.create(
        model=generation_config["model"],
        messages=[{"role": "user", "content": str(prompt)}],  # ensure prompt is a string
        temperature=kwargs.get("temperature", generation_config["temperature"]),
        max_tokens=kwargs.get("max_tokens", generation_config["max_tokens"]),
        top_p=kwargs.get("top_p", generation_config["top_p"]),
        )
      return completion.choices[0].message.content

    return generate_content
