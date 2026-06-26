"""Post-processing utilities for generated images."""

import io
import logging

from PIL import Image

logger = logging.getLogger(__name__)


class PostProcessService:
    """Post-processing operations: resize, watermark, format conversion."""

    # E-commerce platform specifications
    PLATFORM_SPECS = {
        "amazon": {
            "main_image": {"width": 2000, "height": 2000, "bg": "white", "product_fill": 0.85},
        },
        "taobao": {
            "main_image": {"width": 800, "height": 800},
            "detail_image": {"width": 750, "height": 999999},  # variable height
        },
        "shopify": {
            "main_image": {"width": 2048, "height": 2048},
        },
        "tiktok_shop": {
            "main_image": {"width": 1080, "height": 1080},
        },
        "generic": {
            "main_image": {"width": 1024, "height": 1024},
        },
    }

    def resize(
        self,
        image_data: bytes,
        width: int,
        height: int,
        keep_aspect: bool = True,
    ) -> bytes:
        """Resize an image to target dimensions."""
        try:
            img = Image.open(io.BytesIO(image_data))
            if keep_aspect:
                img.thumbnail((width, height), Image.LANCZOS)
            else:
                img = img.resize((width, height), Image.LANCZOS)

            output = io.BytesIO()
            img.save(output, format="PNG")
            return output.getvalue()
        except Exception as e:
            logger.error("Resize failed: %s", e)
            return image_data

    def add_watermark(
        self,
        image_data: bytes,
        watermark_text: str = "",
        opacity: float = 0.3,
    ) -> bytes:
        """Add a subtle text watermark to the image."""
        if not watermark_text:
            return image_data
        try:
            from PIL import ImageDraw, ImageFont

            img = Image.open(io.BytesIO(image_data)).convert("RGBA")
            overlay = Image.new("RGBA", img.size, (255, 255, 255, 0))
            draw = ImageDraw.Draw(overlay)

            # Use default font
            font_size = max(img.width // 40, 12)
            try:
                font = ImageFont.truetype("arial.ttf", font_size)
            except Exception:
                font = ImageFont.load_default()

            # Position: bottom-right corner
            bbox = draw.textbbox((0, 0), watermark_text, font=font)
            text_w = bbox[2] - bbox[0]
            text_h = bbox[3] - bbox[1]
            pos = (img.width - text_w - 20, img.height - text_h - 20)

            draw.text(pos, watermark_text, font=font, fill=(255, 255, 255, int(255 * opacity)))

            result = Image.alpha_composite(img, overlay)
            output = io.BytesIO()
            result.save(output, format="PNG")
            return output.getvalue()
        except Exception as e:
            logger.error("Watermark failed: %s", e)
            return image_data

    def to_platform_format(
        self,
        image_data: bytes,
        platform: str,
    ) -> bytes:
        """Convert image to match platform specifications."""
        specs = self.PLATFORM_SPECS.get(platform, self.PLATFORM_SPECS["generic"])
        main = specs["main_image"]
        return self.resize(
            image_data,
            main["width"],
            main["height"],
            keep_aspect=platform != "amazon",  # Amazon requires exact square
        )


post_process_service = PostProcessService()
