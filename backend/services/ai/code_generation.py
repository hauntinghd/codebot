"""
Grok Code Fast 1 integration for Architecture Mode code generation.
"""
from typing import Any, Dict, Optional
import requests
import json
import os

def generate_code_with_deepseek(prompt: str, batch: Optional[int] = None) -> str:
    """
    Generate code using Grok Code Fast 1 via xAI API for a given prompt.
    Args:
        prompt: The code generation prompt (str)
        batch: Optional batch number for multi-batch generation
    Returns:
        Generated code string
    """
    api_key = os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACEHUB_API_TOKEN")
    if not api_key or api_key == "":
        raise ValueError("HF_TOKEN not set")
    
    model_id = os.environ.get("CODING_MODEL", "Qwen/Qwen2.5-Coder-32B-Instruct")
    url = f"https://api-inference.huggingface.co/models/{model_id}"
    headers = {"Authorization": f"Bearer {api_key}"}
    payload = {
        "inputs": prompt,
        "parameters": {
            "max_new_tokens": 2048,
            "temperature": 0.2,
            "do_sample": True
        }
    }
    
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    data = response.json()
    return data[0]["generated_text"]
