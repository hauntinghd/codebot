"""Image generation utilities for Stable Diffusion XL and Hugging Face models."""
import os
from typing import Optional
from PIL import Image
import torch
from diffusers import StableDiffusionPipeline
from huggingface_hub import hf_hub_download

# Cache loaded models
_sd_pipeline = None
_hf_pipeline = None

def get_sdxl_pipeline(model_id: str = "stabilityai/stable-diffusion-xl-base-1.0", device: Optional[str] = None):
    global _sd_pipeline
    if _sd_pipeline is None:
        _sd_pipeline = StableDiffusionPipeline.from_pretrained(model_id, torch_dtype=torch.float16)
        _sd_pipeline = _sd_pipeline.to(device or ("cuda" if torch.cuda.is_available() else "cpu"))
    return _sd_pipeline


def generate_image_sdxl(prompt: str, model_id: str = "stabilityai/stable-diffusion-xl-base-1.0", device: Optional[str] = None, width: int = 1024, height: int = 1024, num_inference_steps: int = 30) -> Image.Image:
    pipe = get_sdxl_pipeline(model_id, device)
    image = pipe(prompt, width=width, height=height, num_inference_steps=num_inference_steps).images[0]
    return image


def generate_image_huggingface(prompt: str, model_id: str, device: Optional[str] = None, width: int = 1024, height: int = 1024, num_inference_steps: int = 30) -> Image.Image:
    global _hf_pipeline
    if _hf_pipeline is None:
        _hf_pipeline = StableDiffusionPipeline.from_pretrained(model_id, torch_dtype=torch.float16)
        _hf_pipeline = _hf_pipeline.to(device or ("cuda" if torch.cuda.is_available() else "cpu"))
    image = _hf_pipeline(prompt, width=width, height=height, num_inference_steps=num_inference_steps).images[0]
    return image

