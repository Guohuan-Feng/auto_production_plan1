import os
import time           
# from dotenv import load_dotenv
from openai import AzureOpenAI
from openai.types.chat import ChatCompletion

PROXY_URL   = "http://fun4wx:qawaearata0A!@rb-proxy-unix-szh.bosch.com:8080"
ENDPOINT_URL = "https://openaichatgpt-xchina.openai.azure.com/"
0DEPLOYMENT_NAME = "gpt-4o"

def assistant_input_optimize(user_input: str) -> str:

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
        "content": """You are a production planner. The user will provide key information when there is no solution.
        Task: Return a new reasonable modified value {"min_inventory": <int>, "max_inventory": <int>}. Other params are only for reference and cannot be modified.
        #cap[d]: daily qualified capacity limit
        #shipments[d]: fixed shipments
        #force_zero / force_positive: forced stop/full production date
        #iis: list of constraint names triggered by Gurobi IIS
        Return format: {"min_inventory": <int>, "max_inventory": <int>}. The output should be pure JSON, without other text."""
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
        temperature=0.7,
        top_p=0.95,
        frequency_penalty=0,
        presence_penalty=0,
        stream=False         
    )

    return completion.choices[0].message.content.strip()
