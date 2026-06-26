"""Background removal service using rembg (ONNX-based, runs locally)."""

import io
import logging
import tempfile
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)


class BackgroundRemovalService:
    """
    Removes background from product images.

    Uses rembg (BRIA RMBG model) which runs locally without GPU.
    Falls back to a no-op passthrough if rembg is not installed.
    """

    def __init__(self):
        self._model = None
        self._available = False
        self._init_attempted = False

    async def _ensure_model(self):
        """Lazy-load the rembg model on first use."""
        if self._init_attempted:
            return
        self._init_attempted = True
        try:
            from rembg import new_session, remove

            self._model = new_session("briaai/RMBG-1.4")
            self._remove_fn = remove
            self._available = True
            logger.info("Background removal model loaded (BRIA RMBG-1.4)")
        except Exception as e:
            logger.warning("Background removal not available: %s. Will use passthrough.", e)

    async def remove_background(
        self,
        image_data: bytes,
        output_format: str = "png",
    ) -> bytes:
        """
        Remove background from an image.

        Args:
            image_data: Raw image bytes (JPEG, PNG, etc.)
            output_format: Desired output format ("png" recommended for transparency)

        Returns:
            Image bytes with background removed (RGBA PNG)
        """
        await self._ensure_model()

        if not self._available:
            # Passthrough: return original image unchanged
            logger.warning("Background removal unavailable, returning original image")
            return image_data

        try:
            result = self._remove_fn(
                image_data,
                session=self._model,
                only_mask=False,
                alpha_matting=True,
                alpha_matting_foreground_threshold=240,
                alpha_matting_background_threshold=10,
                alpha_matting_erode_size=10,
            )
            return result
        except Exception as e:
            logger.error("Background removal failed: %s", e)
            return image_data  # Fallback


# Singleton
bg_removal_service = BackgroundRemovalService()
