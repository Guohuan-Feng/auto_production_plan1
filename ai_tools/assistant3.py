import os
import time           
# from dotenv import load_dotenv
from openai import AzureOpenAI
from openai.types.chat import ChatCompletion

PROXY_URL   = "http://fun4wx:qawaearata0A!@rb-proxy-unix-szh.bosch.com:8080"
ENDPOINT_URL = "https://openaichatgpt-xchina.openai.azure.com/"
0DEPLOYMENT_NAME = "gpt-4o"

def assistant_input_check(user_input: str) -> str:

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
        "content": """You are a Production Auditor, responsible for reviewing whether the two-week production schedule complies with the rules.
        The input is a JSON string with fixed fields:
        - plan: Daily production for two weeks (1–14)
        - cap: Maximum daily capacity
        - force_positive: Days that are forced production
        - rules:
        * Weekdays (Mon–Fri) must include at least one continuous block of production.
        * The length of this block must be >= week1_min_consecutive_days (days 1–5) or week2_min_consecutive_days (days 8–12).
        * It is NOT required that all weekdays produce, only that one valid block exists.
        * Weekend days (Sat=6,13; Sun=7,14) are ignored for continuity checks.
        * Each week must satisfy the minimum consecutive weekday production days:
            - week1_min_consecutive_days for days 1–5,
            - week2_min_consecutive_days for days 8–12.
        * IMPORTANT RULE:
            If a day is in force_positive:
                - It is always valid.
                - It MUST NOT generate any violation.
                - It MUST be excluded from continuity checks and minimum-day checks.
                - It MUST be EXCLUDED from minimum consecutive-day checks.
        * If the input also includes a long_term_plan (12-month forecast), you must provide a similar "analysis" field for it, containing reasoning, advantages, and risks.

        The output must be a single valid JSON, and the top-level field order is recommended (example):
        {
        "action": "accept" | "tweak",
        "valid": true | false,
        "violations": [
            {"day": , "reason": " "}
        ]
        "analysis": {
            "reasoning": "Explain why this plan is structured this way",
            "advantages": "Summarize the key strengths of this plan",
            "risks": "Highlight possible risks or weak points"
        },
        "long_term_analysis": {
            "reasoning": "Explain why this plan is structured this way",
            "advantages": "Summarize the key strengths of this plan",
            "risks": "Highlight possible risks or weak points"
        }
        }
        "accept" means the plan is compliant.
        Only output pure JSON to ensure that json.loads can be directly parsed. 
        When action = "accept", violations can be set to an empty array or omitted."""
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