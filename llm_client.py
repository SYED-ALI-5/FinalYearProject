import os
import requests

OPENAI_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
LOCAL_ENDPOINT = os.getenv("LOCAL_LLM_ENDPOINT")

def call_openai(prompt):
    import openai
    openai.api_key = OPENAI_KEY
    resp = openai.ChatCompletion.create(
        model=OPENAI_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=200
    )
    return resp['choices'][0]['message']['content']

def call_local(prompt):
    resp = requests.post(LOCAL_ENDPOINT + "/generate", json={"prompt": prompt}, timeout=30)
    return resp.json().get("text","")

def call_llm(prompt):
    if OPENAI_KEY:
        return call_openai(prompt)
    elif LOCAL_ENDPOINT:
        return call_local(prompt)
    else:
        raise RuntimeError("No LLM configured. Set OPENAI_API_KEY or LOCAL_LLM_ENDPOINT")
