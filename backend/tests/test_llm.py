"""Tests for LLM client error handling and JSON extraction."""

import json

import pytest

from tinker.llm import HeuristicLLMClient, _extract_json


def test_extract_json_clean():
    assert _extract_json('{"key": "value"}') == {"key": "value"}


def test_extract_json_with_markdown_fence():
    text = '```json\n{"key": "value"}\n```'
    assert _extract_json(text) == {"key": "value"}


def test_extract_json_with_preamble():
    text = 'Here is the result:\n{"key": "value"}\nDone.'
    assert _extract_json(text) == {"key": "value"}


def test_extract_json_raises_on_no_json():
    with pytest.raises(json.JSONDecodeError):
        _extract_json("no json here at all")


def test_extract_json_raises_on_malformed():
    with pytest.raises(json.JSONDecodeError):
        _extract_json("{bad json")


def test_heuristic_client_classification():
    client = HeuristicLLMClient()
    result = client.generate_json("Please classify this device")
    assert result["category"] == "midi_controller"


def test_heuristic_client_identify():
    client = HeuristicLLMClient()
    result = client.generate_json("Identify the components")
    assert "components" in result
    assert len(result["components"]) > 0


def test_heuristic_client_spatial():
    client = HeuristicLLMClient()
    result = client.generate_json("Estimate dimensions and scale")
    assert "panel_width_mm" in result


def test_heuristic_client_tradeoffs():
    client = HeuristicLLMClient()
    result = client.generate_json("Analyze the trade-offs")
    assert "tradeoffs" in result


def test_heuristic_client_alternatives():
    client = HeuristicLLMClient()
    result = client.generate_json("Suggest alternative components")
    assert "suggestions" in result


def test_heuristic_client_unknown_prompt():
    client = HeuristicLLMClient()
    result = client.generate_json("something completely unrecognized")
    assert result == {"suggestions": []}
