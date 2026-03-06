def build_prompt(classification: dict) -> str:
    return f"""
Given this classification: {classification}
Identify visible synth/MIDI components and return JSON:
{{
  "components": [
    {{"name": "rotary encoder|potentiometer|fader|pads|display|usb-c|din-midi|audio-jack", "count": 0, "visible_details": ""}}
  ],
  "io": [
    {{"name": "", "count": 0, "notes": ""}}
  ]
}}
""".strip()
