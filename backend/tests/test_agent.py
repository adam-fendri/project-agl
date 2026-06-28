from __future__ import annotations

from agl.agent import extract_json


def testextract_json_from_a_plain_object() -> None:
    assert extract_json('{"account": "4300"}') == '{"account": "4300"}'


def testextract_json_strips_a_markdown_fence() -> None:
    text = 'here:\n```json\n{"account": "4300", "match": []}\n```\ndone'
    assert extract_json(text) == '{"account": "4300", "match": []}'


def testextract_json_finds_the_object_in_surrounding_prose() -> None:
    assert extract_json('The answer is {"account": "4300"} given the evidence.') == '{"account": "4300"}'


def testextract_json_returns_the_text_when_there_is_no_object() -> None:
    assert extract_json("no json here") == "no json here"
