PROMPT = """
Classify this product from the provided photos.
Return JSON:
{
  "category": "midi_controller|analog_synth|digital_synth|groovebox|effects_pedal",
  "form_factor": "desktop|keyboard|rack|eurorack_module|pedal",
  "power_input": "usb_bus_power|usb_plus_dc|dc_barrel|eurorack_12v",
  "io_visible": ["usb","din_midi","trs_midi","audio_out","audio_in","headphones","cv_gate"],
  "apparent_use_case": "performance|studio|portable|beginner",
  "confidence": 0.0
}
""".strip()
