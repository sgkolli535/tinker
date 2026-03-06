def build_prompt(components: list[dict], validation: dict) -> str:
    return f"""
You are an expert synth/MIDI hardware engineer.
Given components and validation outputs, suggest alternative configurations
that could improve the design. Focus on power, latency, cost, or audio quality.
Components: {components}
Validation: {validation}
Return JSON:
{{
  "suggestions": [
    {{
      "change": "",
      "improves": "",
      "improvement": "",
      "cost": ""
    }}
  ]
}}
""".strip()
