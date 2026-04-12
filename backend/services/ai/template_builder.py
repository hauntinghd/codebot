"""Template-based builder for high-quality sites."""
from __future__ import annotations
import json
import os
from pathlib import Path


def get_template_path(template_name: str) -> Path:
    """Get path to a template file."""
    templates_dir = Path(__file__).parent / "templates"
    return templates_dir / f"{template_name}.html"


def load_template(template_name: str) -> str:
    """Load a template file."""
    path = get_template_path(template_name)
    if path.exists():
        return path.read_text()
    return ""


# Curated Unsplash image collections for different niches
NICHE_IMAGES = {
    "plushie": [
        "https://images.unsplash.com/photo-1558679908-541bcf1249ff?w=400&h=400&fit=crop",
        "https://images.unsplash.com/photo-1563396983906-b3795482a59a?w=400&h=400&fit=crop",
        "https://images.unsplash.com/photo-1566576912321-d58ddd7a6088?w=400&h=400&fit=crop",
        "https://images.unsplash.com/photo-1585366119957-e9730b6d0f60?w=400&h=400&fit=crop",
        "https://images.unsplash.com/photo-1530325553241-4f6e7690cf36?w=400&h=400&fit=crop",
        "https://images.unsplash.com/photo-1582845512747-e42001c95638?w=400&h=400&fit=crop",
        "https://images.unsplash.com/photo-1596461404969-9ae70f2830c1?w=400&h=400&fit=crop",
        "https://images.unsplash.com/photo-1608889825205-eebdb9fc5806?w=400&h=400&fit=crop",
    ],
    "clothing": [
        "https://images.unsplash.com/photo-1523381210434-271e8be1f52b?w=400&h=400&fit=crop",
        "https://images.unsplash.com/photo-1489987707025-afc232f7ea0f?w=400&h=400&fit=crop",
        "https://images.unsplash.com/photo-1556905055-8f358a7a47b2?w=400&h=400&fit=crop",
        "https://images.unsplash.com/photo-1562157873-818bc0726f68?w=400&h=400&fit=crop",
        "https://images.unsplash.com/photo-1434389677669-e08b4cac3105?w=400&h=400&fit=crop",
        "https://images.unsplash.com/photo-1525507119028-ed4c629a60a3?w=400&h=400&fit=crop",
        "https://images.unsplash.com/photo-1515886657613-9f3515b0c78f?w=400&h=400&fit=crop",
        "https://images.unsplash.com/photo-1539008835657-9e8e9680c956?w=400&h=400&fit=crop",
    ],
    "jewelry": [
        "https://images.unsplash.com/photo-1515562141207-7a88fb7ce338?w=400&h=400&fit=crop",
        "https://images.unsplash.com/photo-1599643478518-a784e5dc4c8f?w=400&h=400&fit=crop",
        "https://images.unsplash.com/photo-1573408301185-9146fe634ad0?w=400&h=400&fit=crop",
        "https://images.unsplash.com/photo-1611591437281-460bfbe1220a?w=400&h=400&fit=crop",
        "https://images.unsplash.com/photo-1605100804763-247f67b3557e?w=400&h=400&fit=crop",
        "https://images.unsplash.com/photo-1602173574767-37ac01994b2a?w=400&h=400&fit=crop",
        "https://images.unsplash.com/photo-1535632066927-ab7c9ab60908?w=400&h=400&fit=crop",
        "https://images.unsplash.com/photo-1506630448388-4e683c67ddb0?w=400&h=400&fit=crop",
    ],
    "cosmetics": [
        "https://images.unsplash.com/photo-1596462502278-27bfdc403348?w=400&h=400&fit=crop",
        "https://images.unsplash.com/photo-1522335789203-aabd1fc54bc9?w=400&h=400&fit=crop",
        "https://images.unsplash.com/photo-1571781926291-c477ebfd024b?w=400&h=400&fit=crop",
        "https://images.unsplash.com/photo-1586495777744-4413f21062fa?w=400&h=400&fit=crop",
        "https://images.unsplash.com/photo-1512496015851-a90fb38ba796?w=400&h=400&fit=crop",
        "https://images.unsplash.com/photo-1598440947619-2c35fc9aa908?w=400&h=400&fit=crop",
        "https://images.unsplash.com/photo-1583209814683-c023dd293cc6?w=400&h=400&fit=crop",
        "https://images.unsplash.com/photo-1631214524020-7e18db9a8f92?w=400&h=400&fit=crop",
    ],
    "electronics": [
        "https://images.unsplash.com/photo-1588423771073-b8903fbb85b5?w=400&h=400&fit=crop",
        "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=400&h=400&fit=crop",
        "https://images.unsplash.com/photo-1546868871-7041f2a55e12?w=400&h=400&fit=crop",
        "https://images.unsplash.com/photo-1583394838336-acd977736f90?w=400&h=400&fit=crop",
        "https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=400&h=400&fit=crop",
        "https://images.unsplash.com/photo-1585298723682-7115561c51b7?w=400&h=400&fit=crop",
        "https://images.unsplash.com/photo-1606107557195-0e29a4b5b4aa?w=400&h=400&fit=crop",
        "https://images.unsplash.com/photo-1612198188060-c7c2a3b66eae?w=400&h=400&fit=crop",
    ],
    "saas": [
        "https://images.unsplash.com/photo-1551434678-e076c223a692?w=600&h=400&fit=crop",
        "https://images.unsplash.com/photo-1460925895917-afdab827c52f?w=600&h=400&fit=crop",
        "https://images.unsplash.com/photo-1553877522-43269d4ea984?w=600&h=400&fit=crop",
        "https://images.unsplash.com/photo-1559136555-9303baea8ebd?w=600&h=400&fit=crop",
    ],
    "default": [
        "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=400&h=400&fit=crop",
        "https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=400&h=400&fit=crop",
        "https://images.unsplash.com/photo-1526170375885-4d8ecf77b99f?w=400&h=400&fit=crop",
        "https://images.unsplash.com/photo-1560343090-f0409e92791a?w=400&h=400&fit=crop",
        "https://images.unsplash.com/photo-1572635196237-14b3f281503f?w=400&h=400&fit=crop",
        "https://images.unsplash.com/photo-1503602642458-232111445657?w=400&h=400&fit=crop",
        "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=400&h=400&fit=crop",
        "https://images.unsplash.com/photo-1585386959984-a4155224a1ad?w=400&h=400&fit=crop",
    ],
}

# Color schemes for different aesthetics
COLOR_SCHEMES = {
    "feminine": {
        "primary": "#ec4899",  # Pink
        "secondary": "#f472b6",  # Light pink
        "accent": "#a855f7",  # Purple
    },
    "masculine": {
        "primary": "#3b82f6",  # Blue
        "secondary": "#1e40af",  # Dark blue
        "accent": "#0f172a",  # Slate
    },
    "luxury": {
        "primary": "#ca8a04",  # Gold
        "secondary": "#78350f",  # Brown
        "accent": "#1f2937",  # Dark gray
    },
    "modern": {
        "primary": "#0ea5e9",  # Cyan
        "secondary": "#6366f1",  # Indigo
        "accent": "#ec4899",  # Pink
    },
    "nature": {
        "primary": "#22c55e",  # Green
        "secondary": "#15803d",  # Dark green
        "accent": "#84cc16",  # Lime
    },
    "default": {
        "primary": "#6366f1",  # Indigo
        "secondary": "#8b5cf6",  # Violet
        "accent": "#ec4899",  # Pink
    },
}

# Sample product names by niche
PRODUCT_NAMES = {
    "plushie": [
        ("Cuddly Bear", "Plushies"),
        ("Fluffy Bunny", "Plushies"),
        ("Sweet Penguin", "Plushies"),
        ("Cozy Kitten", "Plushies"),
        ("Gentle Elephant", "Plushies"),
        ("Dreamy Unicorn", "Plushies"),
        ("Sleepy Sloth", "Plushies"),
        ("Happy Puppy", "Plushies"),
    ],
    "clothing": [
        ("Classic Tee", "Tops"),
        ("Denim Jacket", "Outerwear"),
        ("Summer Dress", "Dresses"),
        ("Cozy Hoodie", "Tops"),
        ("Slim Jeans", "Bottoms"),
        ("Knit Sweater", "Tops"),
        ("Midi Skirt", "Bottoms"),
        ("Linen Shirt", "Tops"),
    ],
    "jewelry": [
        ("Gold Pendant", "Necklaces"),
        ("Diamond Studs", "Earrings"),
        ("Silver Ring", "Rings"),
        ("Pearl Bracelet", "Bracelets"),
        ("Rose Earrings", "Earrings"),
        ("Chain Necklace", "Necklaces"),
        ("Crystal Ring", "Rings"),
        ("Charm Bracelet", "Bracelets"),
    ],
    "default": [
        ("Premium Product", "Featured"),
        ("Classic Item", "Bestsellers"),
        ("New Arrival", "New"),
        ("Top Seller", "Popular"),
        ("Special Edition", "Limited"),
        ("Essential Pick", "Basics"),
        ("Trending Now", "Hot"),
        ("Customer Favorite", "Popular"),
    ],
}


def detect_niche(requirements: str) -> str:
    """Detect the niche from requirements text."""
    requirements_lower = requirements.lower()
    
    if any(word in requirements_lower for word in ["plush", "stuffed", "toy", "teddy", "cuddly"]):
        return "plushie"
    elif any(word in requirements_lower for word in ["cloth", "fashion", "dress", "shirt", "apparel"]):
        return "clothing"
    elif any(word in requirements_lower for word in ["jewel", "ring", "necklace", "bracelet", "earring"]):
        return "jewelry"
    elif any(word in requirements_lower for word in ["makeup", "cosmetic", "beauty", "skincare", "lipstick"]):
        return "cosmetics"
    elif any(word in requirements_lower for word in ["electronic", "gadget", "tech", "phone", "headphone"]):
        return "electronics"
    
    return "default"


def detect_aesthetic(requirements: str) -> str:
    """Detect the aesthetic from requirements text."""
    requirements_lower = requirements.lower()
    
    if any(word in requirements_lower for word in ["women", "feminine", "girl", "pink", "cute", "soft"]):
        return "feminine"
    elif any(word in requirements_lower for word in ["men", "masculine", "guy", "bold", "strong"]):
        return "masculine"
    elif any(word in requirements_lower for word in ["luxury", "premium", "gold", "elegant", "high-end"]):
        return "luxury"
    elif any(word in requirements_lower for word in ["nature", "eco", "green", "organic", "sustainable"]):
        return "nature"
    elif any(word in requirements_lower for word in ["modern", "minimal", "clean", "sleek"]):
        return "modern"
    
    return "default"


def extract_store_name(requirements: str) -> str:
    """Extract store name from requirements."""
    import re
    
    # Look for patterns like "called X", "named X", "store X"
    patterns = [
        r"called\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)?)",
        r"named\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)?)",
        r"store\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)?)",
        r"([A-Z][a-zA-Z]+(?:World|Shop|Store|Co|Hub|Place|Boutique|Market))",
    ]
    
    for pattern in patterns:
        match = re.search(pattern, requirements)
        if match:
            return match.group(1).strip()
    
    # Default name based on niche
    niche = detect_niche(requirements)
    defaults = {
        "plushie": "CuddleCo",
        "clothing": "StyleHouse",
        "jewelry": "Luminance",
        "cosmetics": "GlowUp",
        "electronics": "TechNova",
        "default": "ShopNow",
    }
    return defaults.get(niche, "MyStore")


def generate_products_json(niche: str, images: list, count: int = 8) -> str:
    """Generate products JSON array."""
    names = PRODUCT_NAMES.get(niche, PRODUCT_NAMES["default"])
    
    products = []
    for i in range(min(count, len(names))):
        name, category = names[i]
        price = round(19.99 + (i * 10) + (i % 3 * 5.5), 2)
        original_price = round(price * 1.3, 2) if i % 3 == 0 else None
        
        product = {
            "id": i + 1,
            "name": name,
            "category": category,
            "price": price,
            "originalPrice": original_price,
            "image": images[i % len(images)],
            "rating": 4 + (i % 2),
            "reviews": 50 + (i * 23),
            "badge": "Sale" if original_price else ("New" if i < 2 else None),
        }
        products.append(product)
    
    return json.dumps(products, indent=2)


def generate_reviews_json() -> str:
    """Generate reviews JSON array."""
    reviews = [
        {
            "id": 1,
            "name": "Sarah M.",
            "avatar": "https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=100&h=100&fit=crop",
            "rating": 5,
            "text": "Absolutely love my purchase! The quality exceeded my expectations and shipping was super fast. Will definitely be ordering again!",
            "date": "2 days ago"
        },
        {
            "id": 2,
            "name": "Michael R.",
            "avatar": "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=100&h=100&fit=crop",
            "rating": 5,
            "text": "Best online shopping experience I've had. Customer service was amazing when I had questions about sizing. Highly recommend!",
            "date": "1 week ago"
        },
        {
            "id": 3,
            "name": "Emily L.",
            "avatar": "https://images.unsplash.com/photo-1438761681033-6461ffad8d80?w=100&h=100&fit=crop",
            "rating": 4,
            "text": "Great products at fair prices. The packaging was beautiful too - felt like opening a gift! Can't wait for my next order.",
            "date": "2 weeks ago"
        }
    ]
    return json.dumps(reviews, indent=2)


def generate_blog_json(niche: str) -> str:
    """Generate blog posts JSON array."""
    blog_images = {
        "plushie": [
            "https://images.unsplash.com/photo-1585366119957-e9730b6d0f60?w=600&h=400&fit=crop",
            "https://images.unsplash.com/photo-1566576912321-d58ddd7a6088?w=600&h=400&fit=crop",
            "https://images.unsplash.com/photo-1558679908-541bcf1249ff?w=600&h=400&fit=crop",
        ],
        "default": [
            "https://images.unsplash.com/photo-1556742049-0cfed4f6a45d?w=600&h=400&fit=crop",
            "https://images.unsplash.com/photo-1472851294608-062f824d29cc?w=600&h=400&fit=crop",
            "https://images.unsplash.com/photo-1441986300917-64674bd600d8?w=600&h=400&fit=crop",
        ],
    }
    
    images = blog_images.get(niche, blog_images["default"])
    
    posts = [
        {
            "id": 1,
            "title": "How to Choose the Perfect Gift",
            "category": "Gift Guide",
            "excerpt": "Finding the right gift can be challenging. Here's our guide to selecting something they'll truly love...",
            "image": images[0]
        },
        {
            "id": 2,
            "title": "Behind the Scenes: Our Story",
            "category": "About Us",
            "excerpt": "Learn about our journey from a small idea to the brand you know and love today...",
            "image": images[1]
        },
        {
            "id": 3,
            "title": "Top 10 Trending Products This Season",
            "category": "Trends",
            "excerpt": "Discover what everyone's loving right now and why these products are flying off our shelves...",
            "image": images[2]
        }
    ]
    return json.dumps(posts, indent=2)


def detect_project_type(requirements: str) -> str:
    """Detect if this is e-commerce, landing page, or other."""
    requirements_lower = requirements.lower()
    
    # E-commerce indicators
    ecommerce_words = ["shop", "store", "ecommerce", "e-commerce", "sell", "products", "buy", 
                       "cart", "checkout", "plushie", "clothing", "jewelry", "cosmetics", 
                       "fashion", "boutique", "marketplace"]
    
    # Landing page / SaaS indicators
    landing_words = ["landing", "saas", "startup", "app", "platform", "service", "tool",
                     "software", "pricing", "features", "beta", "waitlist", "signup", "subscribe"]
    
    ecommerce_score = sum(1 for word in ecommerce_words if word in requirements_lower)
    landing_score = sum(1 for word in landing_words if word in requirements_lower)
    
    if ecommerce_score > landing_score:
        return "ecommerce"
    elif landing_score > 0:
        return "landing"
    else:
        return "ecommerce"  # Default to e-commerce as it's more versatile


def generate_features_json() -> str:
    """Generate features JSON for landing page."""
    features = [
        {"id": 1, "icon": "fas fa-bolt", "title": "Lightning Fast", "description": "Experience blazing fast performance with our optimized infrastructure. No more waiting."},
        {"id": 2, "icon": "fas fa-shield-alt", "title": "Enterprise Security", "description": "Bank-level encryption and security protocols keep your data safe at all times."},
        {"id": 3, "icon": "fas fa-sync", "title": "Real-time Sync", "description": "Changes sync instantly across all devices. Always stay up to date."},
        {"id": 4, "icon": "fas fa-chart-line", "title": "Advanced Analytics", "description": "Deep insights into your data with beautiful, actionable dashboards."},
        {"id": 5, "icon": "fas fa-plug", "title": "Easy Integrations", "description": "Connect with 100+ tools you already use. Setup takes just minutes."},
        {"id": 6, "icon": "fas fa-headset", "title": "24/7 Support", "description": "Our dedicated support team is here to help you succeed, anytime."},
    ]
    return json.dumps(features, indent=2)


def generate_steps_json() -> str:
    """Generate how it works steps JSON."""
    steps = [
        {"id": 1, "title": "Create Account", "description": "Sign up in seconds with just your email. No credit card required to start."},
        {"id": 2, "title": "Connect Your Data", "description": "Import your existing data or start fresh. We support all major formats."},
        {"id": 3, "title": "See Results", "description": "Watch your productivity soar as our platform works its magic."},
    ]
    return json.dumps(steps, indent=2)


def generate_pricing_json() -> str:
    """Generate pricing plans JSON."""
    plans = [
        {
            "id": 1, 
            "name": "Starter", 
            "description": "Perfect for individuals",
            "price": 0,
            "featured": False,
            "features": ["Up to 3 projects", "Basic analytics", "Email support", "1GB storage"]
        },
        {
            "id": 2, 
            "name": "Pro", 
            "description": "Best for growing teams",
            "price": 29,
            "featured": True,
            "features": ["Unlimited projects", "Advanced analytics", "Priority support", "100GB storage", "API access"]
        },
        {
            "id": 3, 
            "name": "Enterprise", 
            "description": "For large organizations",
            "price": 99,
            "featured": False,
            "features": ["Everything in Pro", "Custom integrations", "Dedicated manager", "Unlimited storage", "SLA guarantee"]
        },
    ]
    return json.dumps(plans, indent=2)


def generate_testimonials_json() -> str:
    """Generate testimonials JSON."""
    testimonials = [
        {
            "id": 1,
            "name": "Sarah Johnson",
            "role": "CEO, TechStart",
            "avatar": "https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=100&h=100&fit=crop",
            "quote": "This platform transformed how we work. Our team productivity increased by 40% in just the first month."
        },
        {
            "id": 2,
            "name": "Michael Chen",
            "role": "Product Manager, Innovate Inc",
            "avatar": "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=100&h=100&fit=crop",
            "quote": "The best investment we made this year. The ROI was visible within weeks. Highly recommend!"
        },
        {
            "id": 3,
            "name": "Emily Rodriguez",
            "role": "Founder, DesignCo",
            "avatar": "https://images.unsplash.com/photo-1438761681033-6461ffad8d80?w=100&h=100&fit=crop",
            "quote": "Finally, a tool that actually delivers on its promises. The support team is incredible too."
        },
    ]
    return json.dumps(testimonials, indent=2)


def extract_brand_name(requirements: str) -> str:
    """Extract brand name from requirements."""
    import re
    
    patterns = [
        r"called\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)?)",
        r"named\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)?)",
        r"for\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)?)",
        r"([A-Z][a-zA-Z]+(?:ly|ify|io|ai|app|hub|flow|sync|base))",
    ]
    
    for pattern in patterns:
        match = re.search(pattern, requirements)
        if match:
            return match.group(1).strip()
    
    return "Launchpad"


def build_landing_page(requirements: str) -> str:
    """Build a complete landing page from the template."""
    
    aesthetic = detect_aesthetic(requirements)
    colors = COLOR_SCHEMES.get(aesthetic, COLOR_SCHEMES["default"])
    brand_name = extract_brand_name(requirements)
    images = NICHE_IMAGES.get("saas", NICHE_IMAGES["default"])
    
    template = load_template("landing_template")
    if not template:
        return ""
    
    replacements = {
        "{{PAGE_TITLE}}": f"{brand_name} - Transform Your Business",
        "{{PRIMARY_COLOR}}": colors["primary"],
        "{{SECONDARY_COLOR}}": colors["secondary"],
        "{{BRAND_NAME}}": brand_name,
        "{{LOGO_ICON}}": "fas fa-rocket",
        "{{HERO_BADGE}}": "New: Now with AI-powered features",
        "{{HERO_TITLE}}": f"Transform Your Workflow with {brand_name}",
        "{{HERO_SUBTITLE}}": "The all-in-one platform that helps teams work smarter, not harder. Join thousands of companies already saving hours every week.",
        "{{CTA_BUTTON}}": "Start Free Trial",
        "{{HERO_IMAGE}}": images[0],
        "{{SOCIAL_PROOF_NUMBER}}": "10,000+",
        "{{SOCIAL_PROOF_TEXT}}": "teams already using our platform",
        "{{FLOATING_CARD_TITLE}}": "Setup Complete",
        "{{FLOATING_CARD_TEXT}}": "Takes only 2 minutes",
        "{{FEATURES_TITLE}}": "Everything You Need",
        "{{FEATURES_SUBTITLE}}": "Powerful features designed to help your team succeed from day one.",
        "{{FEATURES_JSON}}": generate_features_json(),
        "{{STEPS_TITLE}}": "Get Started in Minutes",
        "{{STEPS_SUBTITLE}}": "Three simple steps to transform your workflow forever.",
        "{{STEPS_JSON}}": generate_steps_json(),
        "{{PRICING_TITLE}}": "Simple, Transparent Pricing",
        "{{PRICING_SUBTITLE}}": "Choose the plan that fits your needs. Scale up anytime.",
        "{{PRICING_JSON}}": generate_pricing_json(),
        "{{TESTIMONIALS_TITLE}}": "Loved by Teams Everywhere",
        "{{TESTIMONIALS_SUBTITLE}}": "See what our customers have to say about their experience.",
        "{{TESTIMONIALS_JSON}}": generate_testimonials_json(),
        "{{CTA_TITLE}}": "Ready to Get Started?",
        "{{CTA_SUBTITLE}}": "Join thousands of teams already transforming their workflow.",
        "{{FOOTER_DESCRIPTION}}": f"Empowering teams to work smarter since 2024.",
    }
    
    html = template
    for placeholder, value in replacements.items():
        html = html.replace(placeholder, value)
    
    return html


def build_from_template(requirements: str) -> str:
    """Build a complete site from the appropriate template."""
    
    project_type = detect_project_type(requirements)
    
    if project_type == "landing":
        return build_landing_page(requirements)
    else:
        return build_ecommerce_page(requirements)


def build_ecommerce_page(requirements: str) -> str:
    """Build a complete e-commerce site from the template."""
    
    # Detect niche and aesthetic
    niche = detect_niche(requirements)
    aesthetic = detect_aesthetic(requirements)
    
    # Get images and colors
    images = NICHE_IMAGES.get(niche, NICHE_IMAGES["default"])
    colors = COLOR_SCHEMES.get(aesthetic, COLOR_SCHEMES["default"])
    
    # Extract store name
    store_name = extract_store_name(requirements)
    
    # Load template
    template = load_template("ecommerce_template")
    if not template:
        return ""
    
    # Build replacements
    replacements = {
        "{{STORE_NAME}}": store_name,
        "{{PRIMARY_COLOR}}": colors["primary"],
        "{{SECONDARY_COLOR}}": colors["secondary"],
        "{{ACCENT_COLOR}}": colors["accent"],
        "{{LOGO_ICON}}": "fas fa-heart" if niche == "plushie" else "fas fa-store",
        "{{ANNOUNCEMENT}}": f"✨ Free shipping on orders over $50! Shop our new arrivals →",
        "{{HERO_TITLE}}": f"Welcome to {store_name}",
        "{{HERO_SUBTITLE}}": "Discover our curated collection of premium products. Quality you can trust, style you'll love.",
        "{{HERO_IMAGE}}": images[0].replace("400x400", "800x600"),
        "{{STAT_1_NUMBER}}": "10K+",
        "{{STAT_1_LABEL}}": "Happy Customers",
        "{{STAT_2_NUMBER}}": "500+",
        "{{STAT_2_LABEL}}": "Products",
        "{{STAT_3_NUMBER}}": "4.9",
        "{{STAT_3_LABEL}}": "Star Rating",
        "{{PRODUCTS_TITLE}}": "Featured Products",
        "{{PRODUCTS_SUBTITLE}}": "Hand-picked favorites our customers love most",
        "{{PRODUCTS_JSON}}": generate_products_json(niche, images),
        "{{REVIEWS_JSON}}": generate_reviews_json(),
        "{{BLOG_JSON}}": generate_blog_json(niche),
        "{{FOOTER_DESCRIPTION}}": f"Your destination for quality {niche if niche != 'default' else 'products'}. We're passionate about bringing you the best.",
        "{{STORE_DOMAIN}}": f"{store_name.lower().replace(' ', '')}.com",
        "{{PHONE}}": "(555) 123-4567",
        "{{ADDRESS}}": "123 Shop Street, City, ST 12345",
    }
    
    # Apply replacements
    html = template
    for placeholder, value in replacements.items():
        html = html.replace(placeholder, value)
    
    return html
