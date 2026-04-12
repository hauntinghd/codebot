"""Generate images via xAI Grok Image API (grok-imagine-image)."""
from __future__ import annotations

import asyncio
import logging
import os
import re
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger("codebot")

XAI_API_URL = "https://api.x.ai/v1/images/generations"

PLACEHOLDER_PATTERNS = [
    "unsplash.com",
    "picsum.photos",
    "placehold.co",
    "placeholder",
    "via.placeholder",
    "source.unsplash",
    "images.unsplash",
    "dummyimage",
    "lorem.space",
    "loremflickr",
    "fakeimg",
]


def _get_api_key() -> str:
    return (os.getenv("XAI_API_KEY") or "").strip()


def _is_placeholder(url: str) -> bool:
    low = url.lower()
    return any(p in low for p in PLACEHOLDER_PATTERNS)


async def generate_image(prompt: str, aspect_ratio: str = "16:9") -> Optional[str]:
    """Generate a single image via Grok and return the temporary URL."""
    key = _get_api_key()
    if not key:
        logger.warning("XAI_API_KEY not set — skipping image generation")
        return None

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                XAI_API_URL,
                headers={
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "grok-imagine-image",
                    "prompt": prompt,
                    "aspect_ratio": aspect_ratio,
                    "n": 1,
                },
            )
            if resp.status_code != 200:
                logger.warning(f"Grok image API returned {resp.status_code}: {resp.text[:300]}")
                return None
            data = resp.json()
            url = data.get("data", [{}])[0].get("url")
            return url
    except Exception as e:
        logger.warning(f"Grok image generation failed: {e}")
        return None


def _build_prompt(description: str, user_prompt: str) -> str:
    context_hint = user_prompt[:150] if user_prompt else ""
    return (
        f"Professional commercial product photography of: {description}. "
        f"{'Context: ' + context_hint + '. ' if context_hint else ''}"
        "The image must show the EXACT product described — not random objects. "
        "Studio lighting, photorealistic, white or elegant dark background, "
        "high-end e-commerce product shot."
    )


def _extract_all_placeholder_urls(content: str) -> List[Dict[str, Any]]:
    """Find ALL placeholder URLs in HTML/JS/CSS content, not just <img> tags.

    Scans for URLs in:
    - <img src="...">
    - background-image: url(...)
    - JavaScript strings: "https://..." or 'https://...'
    - Any other src/href attributes
    """
    results = []
    seen_urls = set()

    url_re = re.compile(
        r'''(?:src|href|image|img|url)\s*[:=]\s*["'(]+\s*(https?://[^"')>\s]+)''',
        re.IGNORECASE,
    )
    for m in url_re.finditer(content):
        url = m.group(1).strip()
        if _is_placeholder(url) and url not in seen_urls:
            seen_urls.add(url)
            start = m.start()
            context_before = content[max(0, start - 300):start]
            results.append({"url": url, "context_before": context_before, "pos": start})

    js_url_re = re.compile(
        r'''["'](https?://(?:source\.unsplash|images\.unsplash|picsum\.photos|placehold)[^"']+)["']''',
        re.IGNORECASE,
    )
    for m in js_url_re.finditer(content):
        url = m.group(1).strip()
        if url not in seen_urls:
            seen_urls.add(url)
            start = m.start()
            context_before = content[max(0, start - 300):start]
            results.append({"url": url, "context_before": context_before, "pos": start})

    return results


def _guess_description(context_before: str, url: str) -> str:
    """Try to extract a meaningful description from surrounding context."""
    heading_m = re.search(r'<h[1-6][^>]*>([^<]+)</h', context_before, re.IGNORECASE)
    if heading_m:
        return heading_m.group(1).strip()

    alt_m = re.search(r'alt=["\']([^"\']+)["\']', context_before[-200:], re.IGNORECASE)
    if alt_m and alt_m.group(1).strip().lower() not in ("image", "photo", "placeholder", "img", ""):
        return alt_m.group(1).strip()

    name_m = re.search(r'name["\s:]+["\']([^"\']+)["\']', context_before[-200:], re.IGNORECASE)
    if name_m:
        return name_m.group(1).strip()

    title_m = re.search(r'title["\s:]+["\']([^"\']+)["\']', context_before[-200:], re.IGNORECASE)
    if title_m:
        return title_m.group(1).strip()

    url_parts = re.findall(r'[\w-]+', url.split("?")[0].split("/")[-1])
    if url_parts and url_parts[0].lower() not in ("photo", "featured", "random", "com", "photos"):
        return " ".join(url_parts[:3])

    return "luxury product"


def _extract_image_targets(files: List[Dict[str, Any]], user_prompt: str = "") -> List[Dict[str, Any]]:
    """Find all placeholder image URLs across all file content (HTML, JS, CSS)."""
    targets = []

    for idx, f in enumerate(files):
        path = f.get("path", "")
        if not path.endswith((".html", ".htm", ".js", ".css")):
            continue
        content = f.get("content", "")
        placeholders = _extract_all_placeholder_urls(content)

        for ph in placeholders:
            desc = _guess_description(ph["context_before"], ph["url"])
            is_hero = any(
                kw in ph["context_before"][-300:].lower()
                for kw in ("hero", "banner", "jumbotron", "splash", "cover")
            )
            targets.append({
                "file_idx": idx,
                "old_src": ph["url"],
                "prompt": _build_prompt(desc, user_prompt),
                "aspect_ratio": "16:9" if is_hero else "1:1",
            })

    return targets


def _extract_js_product_images(files: List[Dict[str, Any]], user_prompt: str = "") -> List[Dict[str, Any]]:
    """Find product objects in JS arrays and ensure every one has a Grok-generated image.

    Looks for patterns like: { name: "Product Name", ..., image: "URL" }
    Returns targets for any product whose image URL is a placeholder or empty.
    """
    targets = []
    product_re = re.compile(
        r'\{\s*name\s*:\s*["\']([^"\']+)["\']\s*,'
        r'.*?image\s*:\s*["\']([^"\']*)["\']',
        re.DOTALL,
    )

    for idx, f in enumerate(files):
        if not f.get("path", "").endswith((".html", ".htm", ".js")):
            continue
        content = f.get("content", "")
        for m in product_re.finditer(content):
            product_name = m.group(1).strip()
            image_url = m.group(2).strip()
            if not product_name:
                continue
            # If image is already a Grok URL (grok.x.ai or xai-), skip
            if "grok.x.ai" in image_url or "xai-" in image_url:
                continue
            targets.append({
                "file_idx": idx,
                "old_src": image_url,
                "product_name": product_name,
                "prompt": _build_prompt(product_name, user_prompt),
                "aspect_ratio": "1:1",
            })

    return targets


async def enhance_files_with_images(
    files: List[Dict[str, Any]],
    max_images: int = 20,
    user_prompt: str = "",
) -> List[Dict[str, Any]]:
    """Post-process generated files: replace placeholder image URLs with Grok-generated images."""
    key = _get_api_key()
    if not key:
        logger.info("No XAI_API_KEY — skipping image generation")
        return files

    # Phase 1: Find all placeholder URLs (hero images, static img tags, etc.)
    url_targets = _extract_image_targets(files, user_prompt)

    # Phase 2: Find product images in JS arrays that need replacement
    product_targets = _extract_js_product_images(files, user_prompt)

    # Deduplicate: don't re-process URLs already found in phase 1
    phase1_urls = {t["old_src"] for t in url_targets}
    for pt in product_targets:
        if pt["old_src"] and pt["old_src"] not in phase1_urls:
            url_targets.append(pt)
            phase1_urls.add(pt["old_src"])
        elif not pt["old_src"] or pt["old_src"] in ("#", ""):
            url_targets.append(pt)

    if not url_targets:
        logger.info("No placeholder images found to replace")
        return files

    url_targets = url_targets[:max_images]

    logger.info(f"Generating {len(url_targets)} images via Grok Image API...")
    for i, t in enumerate(url_targets):
        src_preview = t.get("old_src", "")[:60] or "(empty)"
        prompt_preview = t["prompt"][:80]
        logger.info(f"  Image {i+1}: {src_preview} -> {prompt_preview}...")

    tasks = [generate_image(t["prompt"], t["aspect_ratio"]) for t in url_targets]
    urls = await asyncio.gather(*tasks)

    for target, url in zip(url_targets, urls):
        if not url:
            continue
        idx = target["file_idx"]
        old_src = target["old_src"]
        if old_src and old_src not in ("#", ""):
            files[idx]["content"] = files[idx]["content"].replace(old_src, url)
        else:
            # Empty/missing image URL in a product object — inject the generated URL
            # Find the product by name and set its image
            product_name = target.get("product_name", "")
            if product_name:
                pattern = re.compile(
                    r'(name\s*:\s*["\']' + re.escape(product_name) + r'["\'].*?image\s*:\s*["\'])([^"\']*?)(["\'])',
                    re.DOTALL,
                )
                files[idx]["content"] = pattern.sub(r'\1' + url + r'\3', files[idx]["content"], count=1)

    generated_count = sum(1 for u in urls if u)
    logger.info(f"Generated {generated_count}/{len(url_targets)} images successfully")

    return files
