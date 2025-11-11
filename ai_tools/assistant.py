import os
import time           
# from dotenv import load_dotenv
from openai import AzureOpenAI
from openai.types.chat import ChatCompletion

PROXY_URL   = "http://fun4wx:qawaearata0A!@rb-proxy-unix-szh.bosch.com:8080"
ENDPOINT_URL = "https://openaichatgpt-xchina.openai.azure.com/"
DEPLOYMENT_NAME = "gpt-4o"

def assistant_input_process(user_input: str) -> str:

    os.environ["HTTP_PROXY"] = PROXY_URL
    os.environ["HTTPS_PROXY"] = PROXY_URL

    client = AzureOpenAI(
        azure_endpoint=ENDPOINT_URL,
        api_key=AZURE_OPENAI_API_KEY,
        api_version="2025-01-01-preview"
    )

    messages = [
    {
        "role": "system",
        "content": """You are a parameter-extraction assistant. Your task is:
        1. From the user’s input, determine if they mention changing any of these six parameters:
        - min_inventory
        - max_inventory
        - OEE
        - CT
        - force_positive
        - force_zero
        Initial value of these four values are 3000, 9000, 0.95, 105, {}, {}
        2. If the user clearly or implicitly specifies a new value for any parameter, whether as an absolute number or as a relative change (e.g. “half”, “double”, “reduce by 20%”, “increase by 1000 units”), then:
        - Absolute: extract that numeric value;
        - Relative: compute the new value by applying the indicated factor or percentage to the current value (e.g. “half” → min_inventory*0.5 and max_inventory*0.5; “reduce by 20%” → min_inventory*0.8 and max_inventory*0.8);
        - Change the day must work: if one day must work, change parameter force_positive, which is a dict, means the day must work. If the start of work requires any three consecutive working days
        - Change the day must not work: if one day must not work, change parameter force_zero, which is a dict, like {1: None}, that means this week's Monday must not work. Days from 1 to 14, means this Monday to next week's Friday
        Otherwise, set that parameter to null.
        3. Always output a single JSON object containing exactly these three fields, for example:
        {
        "min_inventory": 3000,
        "max_inventory": 9000,
        "OEE": 0.95,
        "CT": 105,
        "force_positive": {"3": null, "4": null, "5": null},
        "force_zero": {"6": null, "7": null},
        "week1_min_consecutive_days": 3,
        "week2_min_consecutive_days": 3
        }
        4. Do not output any extra text—only the JSON object.
        5. IMPORTANT: Never modify `force_positive` or `force_zero`. Always keep them exactly the same as provided in the input (do not add, remove, or replace any keys/values).
        6. If the user mentions a long-term forecast (e.g., "long term", "12-month forecast", "one-year forecast", "long-term forecast"), then set "long_term": true; otherwise, set "long_term": false.
"""
    },  
    {
        "role": "user",
        "content": user_input
    }
]


    completion: ChatCompletion = client.chat.completions.create(
        model=DEPLOYMENT_NAME,
        messages=messages,
        max_tokens=4096,     
        temperature=0.3,
        top_p=0.95,
        frequency_penalty=0,
        presence_penalty=0,
        stream=False         
    )

    return completion.choices[0].message.content.strip()
