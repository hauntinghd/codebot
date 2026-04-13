#!/usr/bin/env python3
import os
import requests
import json

def check_model(token, model, timeout=30):
    url = f"https://router.huggingface.co/models/{model}"
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    payload = {"inputs": "Hello world", "options": {"wait_for_model": True}, "parameters": {"max_new_tokens": 16}}
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
    except Exception as e:
        return {"model": model, "status": "error", "detail": str(e)}
    out = {"model": model, "status_code": resp.status_code}
    try:
        out_json = resp.json()
        out["json"] = out_json if isinstance(out_json, (dict, list)) else str(out_json)
    except Exception:
        out["text"] = resp.text[:1000]
    return out


def main():
    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACEHUB_API_TOKEN")
    if not token:
        print("Missing HF token in environment (HF_TOKEN/HUGGINGFACEHUB_API_TOKEN)")
        return

    candidates = [
        os.environ.get("HF_PLANNING_MODEL", "google/flan-ul2"),
        "google/flan-t5-large",
        "google/flan-t5-xl",
        "google/flan-ul2",
        "gpt2",
        "gpt2-medium",
        "bigscience/bloomz-560m",
        "bigscience/bloomz-1b1",
        "facebook/opt-1.3b",
        "tiiuae/falcon-7b-instruct",
        "tiiuae/falcon-40b-instruct",
        "openassistant/gpt-oa-3",
        "mistralai/mistral-7b-instruct-v0.1",
        "meta-llama/Llama-2-7b-chat-hf",
    ]

    results = []
    for m in candidates:
        if not m:
            continue
        print(f"Testing model: {m}")
        r = check_model(token, m)
        print(json.dumps(r, indent=2, ensure_ascii=False)[:2000])
        results.append(r)

    success = [r for r in results if r.get("status_code") == 200]
    print("\nSummary - models responding with HTTP 200:")
    for s in success:
        print(" -", s["model"])

if __name__ == '__main__':
    main()
