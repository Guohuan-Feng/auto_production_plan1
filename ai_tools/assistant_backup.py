import os
import json
import time
from openai import AzureOpenAI
from dotenv import load_dotenv


def assistant_input_process(input):
    # 配置代理环境变量
    load_dotenv()
    proxy = os.getenv("PROXY_URL")
    if not proxy:
        raise RuntimeError("PROXY_URL missing")

    os.environ["HTTP_PROXY"] = proxy
    os.environ["HTTPS_PROXY"] = proxy

    client = AzureOpenAI(
        azure_endpoint=os.getenv("ENDPOINT_URL", "https://openaichatgpt-xchina.openai.azure.com/"),
        api_version="2024-05-01-preview" #
    )

    assistant = client.beta.assistants.create(
        model="gpt-4o-2024-11-20",  # replace with model deployment name
        name="Production_Planner",
        instructions="""You are a parameter extraction assistant. Your task is:\n
        1. From the user’s input, determine if they mention changing any of these six parameters:\n
           - min_inventory\n
           - max_inventory\n
           - OEE\n
           - CT\n
           - force_positive\n
           - force_zero\n
           Initial value of these four value are 3000, 9000, 0.95, 105, {}, {}
        2. If the user clearly or implicitly specifies a new value for any parameter, whether as an absolute number or as a relative change (e.g. “half”, “double”, “reduce by 20%”, “increase by 1000 units”), then:\n
           - Absolute: extract that numeric value;\n
           - Relative: compute the new value by applying the indicated factor or percentage to the current value (e.g. “half” → min_inventory*0.5 and max_inventory*0.5; “reduce by 20%” → min_inventory*0.8 and max_inventory*0.8);\n
          - Change the day must work: if one day must work, change parameter force_positive, which is a dict, means the day must work. If the start of work requires any three consecutive working days\n
           - Change the day must not work: if one day must not work, change parameter force_zero, which is a dict, like {1: None}, that means this week's Monday must not work. Days from 1 to 14, means this Monday to next week's Friday\n
           Otherwise, set that parameter to null.\n
        3. Always output a single JSON object containing exactly these three fields, for example:\n
                    {\n
                     \"min_inventory\": 3000,\n
                     \"max_inventory\": 9000,\n
                     \"OEE\": 0.95,\n
                     \"CT\": 105,\n
                     \"force_positive\": {"3": null, "4": null, "5": null}\n
                     \"force_zero\": {"6": null, "7": null}\n
                     }\n
        4. Do not output any extra text—only the JSON object.\n
        """,
        tools=[{"type": "code_interpreter"}]
        , tool_resources={"code_interpreter": {"file_ids": []}},
        temperature=1,
        top_p=1
    )

    # Create a thread
    thread = client.beta.threads.create()

    # Add a user question to the thread
    message = client.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content=input
    )

    # Run the thread
    run = client.beta.threads.runs.create(
        thread_id=thread.id,
        assistant_id=assistant.id
    )

    # Looping until the run completes or fails
    while run.status in ['queued', 'in_progress', 'cancelling']:
        time.sleep(1)
        run = client.beta.threads.runs.retrieve(
            thread_id=thread.id,
            run_id=run.id
        )

    if run.status == 'completed':
        messages = client.beta.threads.messages.list(
            thread_id=thread.id
        )

        # 输出
        message = messages.to_json()
        message_dict = json.loads(message)
        # 提取所有 value 的值
        values = []
        for item in message_dict["data"]:  # 遍历 data 列表
            for content in item.get("content", []):  # 遍历 content 列表
                text = content.get("text", {})  # 获取 text 字段
                value = text.get("value", "")  # 获取 value 字段
                values.append(value)  # 保存 value 值到列表中
        # 输出结果
        # for idx, value in enumerate(values):
        #     print(f"Message {idx + 1}:")
        #     print(value)
        #     print()
    elif run.status == 'requires_action':
        # the assistant requires calling some functions
        # and submit the tool outputs back to the run
        pass
    else:
        print(run.status)
    return values[0]
