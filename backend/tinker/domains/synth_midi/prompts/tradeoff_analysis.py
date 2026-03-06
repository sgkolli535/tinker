def build_prompt(components: list[dict], validation: dict) -> str:
    return f"""
You are an expert synth/MIDI hardware engineer.
Given components and validation outputs, infer key design trade-offs.
Components: {components}
Validation: {validation}
Return JSON:
{{
  "tradeoffs": [
    {{
      "choice": "",
      "optimized": "",
      "sacrificed": "",
      "verdict": ""
    }}
  ]
}}
""".strip()
