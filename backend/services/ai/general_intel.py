"""
HuggingFace Qwen2.5-3B-Instruct integration for general intelligence (research).
"""
from typing import Any, Optional

def generate_research_with_qwen(prompt: str, max_new_tokens: int = 2048) -> str:
    """
    Generate research/plan text using Qwen2.5-3B-Instruct from HuggingFace.
    Args:
        prompt: The research prompt (str)
        max_new_tokens: Max tokens to generate
    Returns:
        Generated research string
    """
    from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
    import torch
    import os
    model_id = "Qwen/Qwen2.5-3B-Instruct"
    hf_token = os.environ.get("HUGGINGFACEHUB_API_TOKEN")
    if not hasattr(generate_research_with_qwen, "_pipe"):
        tokenizer = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True, token=hf_token)
        model = AutoModelForCausalLM.from_pretrained(model_id, torch_dtype=torch.float16, device_map="auto", trust_remote_code=True, token=hf_token)
        pipe = pipeline("text-generation", model=model, tokenizer=tokenizer, device_map="auto", token=hf_token)
        generate_research_with_qwen._pipe = pipe
    else:
        pipe = generate_research_with_qwen._pipe
    result = pipe(prompt, max_new_tokens=max_new_tokens, temperature=0.2, do_sample=True)
    return result[0]["generated_text"]
