"""Model listing API - returns available generation models and their capabilities."""

from fastapi import APIRouter

router = APIRouter()


@router.get("")
async def list_models():
    """List all available generation models with pricing and capabilities."""
    # Pre-configured model registry - populated from DB or config
    return [
        {
            "name": "flux-pro",
            "provider": "black-forest-labs",
            "provider_type": "image",
            "description": "Flux Pro - highest quality photorealistic image generation",
            "max_resolution": "1024x1024",
            "supported_sizes": ["1024x1024", "1024x576", "576x1024"],
            "cost_per_image": 0.05,
            "is_enabled": True,
            "best_for": ["lifestyle", "photorealistic", "complex scenes"],
        },
        {
            "name": "dall-e-3",
            "provider": "openai",
            "provider_type": "image",
            "description": "DALL·E 3 - OpenAI's latest image generation model",
            "max_resolution": "1024x1024",
            "supported_sizes": ["1024x1024", "1024x1792", "1792x1024"],
            "cost_per_image": 0.04,
            "is_enabled": False,
            "best_for": ["conceptual", "creative", "illustrated style"],
        },
        {
            "name": "stable-diffusion-xl",
            "provider": "stability-ai",
            "provider_type": "image",
            "description": "Stable Diffusion XL - fast and affordable",
            "max_resolution": "1024x1024",
            "supported_sizes": ["1024x1024", "896x1152", "1152x896"],
            "cost_per_image": 0.002,
            "is_enabled": False,
            "best_for": ["draft", "quick iterations", "high volume"],
        },
        {
            "name": "tongyi-wanxiang",
            "provider": "alibaba",
            "provider_type": "image",
            "description": "通义万象 - optimized for Chinese e-commerce content",
            "max_resolution": "1024x1024",
            "supported_sizes": ["1024x1024", "720x1280"],
            "cost_per_image": 0.02,
            "is_enabled": False,
            "best_for": ["chinese-market", "taobao", "jd"],
        },
        {
            "name": "runway-gen3",
            "provider": "runway",
            "provider_type": "video",
            "description": "Runway Gen-3 - state of the art video generation",
            "max_resolution": "1280x720",
            "supported_sizes": ["1280x720", "1080x1920"],
            "cost_per_second": 0.25,
            "is_enabled": False,
            "best_for": ["cinematic", "creative", "high quality"],
        },
        {
            "name": "kling",
            "provider": "kuaishou",
            "provider_type": "video",
            "description": "可灵 (Kling) - best for Chinese e-commerce short videos",
            "max_resolution": "1080x1920",
            "supported_sizes": ["1080x1920", "720x1280"],
            "cost_per_second": 0.10,
            "is_enabled": False,
            "best_for": ["chinese-market", "short-video", "douyin"],
        },
    ]
