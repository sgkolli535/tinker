from __future__ import annotations

import base64
import json
import mimetypes
from typing import Any


class AnthropicJSONClient:
    """Thin wrapper around Anthropic text/vision prompts with JSON output."""

    def __init__(self, api_key: str, model: str = "claude-3-5-sonnet-latest") -> None:
        from anthropic import Anthropic

        self._client = Anthropic(api_key=api_key)
        self._model = model

    def generate_json(self, prompt: str, images: list[str] | None = None) -> dict[str, Any]:
        content: list[dict[str, Any]] = []
        if images:
            for image_path in images:
                with open(image_path, "rb") as f:
                    image_bytes = f.read()
                media_type = mimetypes.guess_type(image_path)[0] or "image/jpeg"
                content.append(
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": base64.b64encode(image_bytes).decode("utf-8"),
                        },
                    }
                )
        content.append({"type": "text", "text": f"Return strict JSON only.\n{prompt}"})
        message = self._client.messages.create(
            model=self._model,
            max_tokens=1200,
            temperature=0,
            messages=[{"role": "user", "content": content}],
        )
        text = "".join(block.text for block in message.content if hasattr(block, "text"))
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            start = text.find("{")
            end = text.rfind("}")
            if start >= 0 and end > start:
                return json.loads(text[start : end + 1])
            raise


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
