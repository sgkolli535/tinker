def build_prompt(components: list[dict]) -> str:
    return f"""
Using known component dimensions as anchors, estimate physical dimensions for this synth/MIDI device.
Components: {components}
Return JSON:
{{
  "panel_width_mm": 0,
  "panel_depth_mm": 0,
  "panel_height_mm": 0,
  "control_spacing_mm": 0.0,
  "jack_spacing_mm": 0.0,
  "overall_weight_estimate_g": 0,
  "scale_reference_used": ""
}}
""".strip()
