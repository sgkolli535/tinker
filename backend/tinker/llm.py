from __future__ import annotations

import base64
import json
import logging
import mimetypes
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 1.5  # seconds


def _extract_json(text: str) -> dict[str, Any]:
    """Parse JSON from LLM output, tolerating markdown fences."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Try to extract a top-level JSON object from the response.
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            return json.loads(text[start : end + 1])
        raise


class AnthropicJSONClient:
    """Thin wrapper around Anthropic text/vision prompts with JSON output."""

    def __init__(self, api_key: str, model: str = "claude-3-5-sonnet-latest") -> None:
        from anthropic import Anthropic

        self._client = Anthropic(api_key=api_key)
        self._model = model

    def _encode_image(self, image_path: str) -> dict[str, Any] | None:
        path = Path(image_path)
        if not path.is_file():
            logger.warning("Image file not found, skipping: %s", image_path)
            return None
        try:
            image_bytes = path.read_bytes()
        except OSError as exc:
            logger.warning("Failed to read image %s: %s", image_path, exc)
            return None
        media_type = mimetypes.guess_type(image_path)[0] or "image/jpeg"
        return {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": media_type,
                "data": base64.b64encode(image_bytes).decode("utf-8"),
            },
        }

    def generate_json(self, prompt: str, images: list[str] | None = None) -> dict[str, Any]:
        content: list[dict[str, Any]] = []
        if images:
            for image_path in images:
                block = self._encode_image(image_path)
                if block:
                    content.append(block)
        content.append({"type": "text", "text": f"Return strict JSON only.\n{prompt}"})

        last_exc: Exception | None = None
        for attempt in range(MAX_RETRIES):
            try:
                message = self._client.messages.create(
                    model=self._model,
                    max_tokens=1200,
                    temperature=0,
                    messages=[{"role": "user", "content": content}],
                )
                text = "".join(block.text for block in message.content if hasattr(block, "text"))
                return _extract_json(text)
            except json.JSONDecodeError:
                logger.warning("LLM returned non-JSON on attempt %d, retrying", attempt + 1)
                last_exc = last_exc  # keep original
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                if attempt < MAX_RETRIES - 1:
                    wait = RETRY_BACKOFF_BASE * (2 ** attempt)
                    logger.warning("Anthropic API error (attempt %d/%d): %s — retrying in %.1fs", attempt + 1, MAX_RETRIES, exc, wait)
                    time.sleep(wait)
                    continue
                break

        logger.error("All %d LLM attempts failed", MAX_RETRIES)
        if last_exc:
            raise last_exc
        raise RuntimeError("LLM call failed with no captured exception")


class HeuristicLLMClient:
    """Deterministic fallback so local runs work without external API keys."""

    def generate_json(self, prompt: str, images: list[str] | None = None) -> dict[str, Any]:
        prompt_l = prompt.lower()
        if "classify" in prompt_l:
            return {
                "category": "midi_controller",
                "form_factor": "desktop",
                "power_input": "usb_bus_power",
                "io_visible": ["usb", "din_midi", "audio_out"],
                "apparent_use_case": "performance",
                "confidence": 0.72,
            }
        if "identify" in prompt_l:
            return {
                "components": [
                    {"name": "rotary encoder", "count": 8, "visible_details": "24 detent, push switch"},
                    {"name": "fader", "count": 4, "visible_details": "60mm travel"},
                    {"name": "pads", "count": 16, "visible_details": "backlit"},
                    {"name": "usb-c", "count": 1, "visible_details": "rear panel"},
                ],
                "io": [
                    {"name": "USB-C", "count": 1, "notes": "rear"},
                    {"name": "DIN-5 MIDI", "count": 2, "notes": "in/out"},
                    {"name": "6.35mm audio out", "count": 2, "notes": "L/R"},
                ],
            }
        if "dimensions" in prompt_l or "scale" in prompt_l:
            return {
                "panel_width_mm": 290,
                "panel_depth_mm": 160,
                "panel_height_mm": 40,
                "control_spacing_mm": 22,
                "jack_spacing_mm": 16,
                "overall_weight_estimate_g": 920,
                "scale_reference_used": "USB-C receptacle width",
            }
        if "trade-offs" in prompt_l or "tradeoffs" in prompt_l:
            return {
                "tradeoffs": [
                    {
                        "choice": "USB bus power",
                        "optimized": "portability",
                        "sacrificed": "power headroom",
                        "verdict": "Reasonable for compact controllers",
                    },
                    {
                        "choice": "Dense controls",
                        "optimized": "expressive control surface",
                        "sacrificed": "scan complexity",
                        "verdict": "Good if firmware keeps latency below 15ms",
                    },
                ]
            }
        if "alternative" in prompt_l or "suggest" in prompt_l:
            return {
                "suggestions": [
                    {
                        "change": "Switch to RP2040 MCU",
                        "improves": "cost and USB native support",
                        "improvement": "~$0.50 savings, native USB-MIDI",
                        "cost": "Different toolchain, less community MIDI firmware",
                    },
                ]
            }
        return {"suggestions": []}
