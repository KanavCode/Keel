import pytest

from keel import ExtractError, extract_json, iter_json


def test_plain_json():
    assert extract_json('{"a": 1}') == {"a": 1}


def test_markdown_fence():
    assert extract_json('Sure!\n```json\n{"a": 1}\n```\nHope that helps.') == {"a": 1}


def test_prose_around_object():
    assert extract_json('Here you go: {"city": "Vadodara", "n": [1, 2]} - done') == {
        "city": "Vadodara",
        "n": [1, 2],
    }


def test_braces_inside_strings_do_not_break_scanning():
    assert extract_json('Result: {"note": "use } carefully", "ok": true}') == {
        "note": "use } carefully",
        "ok": True,
    }


def test_trailing_comma_repaired():
    assert extract_json('{"a": 1, "b": [1, 2,],}') == {"a": 1, "b": [1, 2]}


def test_python_literals_repaired():
    assert extract_json("{'a': True, 'b': None}") == {"a": True, "b": None}


def test_smart_quotes_repaired():
    assert extract_json("{“a”: 1}") == {"a": 1}


def test_think_block_is_ignored():
    text = '<think>maybe {"wrong": true}</think>{"right": true}'
    assert extract_json(text) == {"right": True}


def test_multiple_candidates_are_all_yielded():
    assert list(iter_json('first {"a": 1} then {"b": 2}')) == [{"a": 1}, {"b": 2}]


def test_scalars_are_not_returned():
    with pytest.raises(ExtractError):
        extract_json("42")


def test_no_json_raises():
    with pytest.raises(ExtractError):
        extract_json("I could not do that.")
