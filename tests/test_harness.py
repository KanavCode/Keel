from keel import structured

PERSON = {
    "type": "object",
    "properties": {"name": {"type": "string"}, "age": {"type": "integer", "minimum": 0}},
    "required": ["name", "age"],
    "additionalProperties": False,
}


def test_first_try_success(scripted):
    backend = scripted(['{"name": "Asha", "age": 30}'])
    result = structured(backend, "Make a person", PERSON)
    assert result.ok and result.value == {"name": "Asha", "age": 30}
    assert result.calls == 1


def test_repairs_schema_violation_and_feeds_back_the_error(scripted):
    backend = scripted(['{"name": "Asha", "age": "thirty"}', '{"name": "Asha", "age": 30}'])
    result = structured(backend, "Make a person", PERSON)
    assert result.ok and result.calls == 2
    assert result.attempts[0].stage == "schema"
    repair_prompt = backend.calls[1][-1]["content"]
    assert "age" in repair_prompt and "not of type 'integer'" in repair_prompt


def test_repairs_unparseable_reply(scripted):
    backend = scripted(["I'd be happy to help!", '{"name": "Asha", "age": 30}'])
    result = structured(backend, "Make a person", PERSON)
    assert result.ok
    assert result.attempts[0].stage == "parse"


def test_semantic_verifier_triggers_repair(scripted):
    backend = scripted(['{"name": "Asha", "age": 200}', '{"name": "Asha", "age": 40}'])

    def plausible(v):
        return None if v["age"] < 120 else f"age {v['age']} is not plausible"

    result = structured(backend, "Make a person", PERSON, verify=plausible)
    assert result.ok and result.value["age"] == 40
    assert result.attempts[0].stage == "verify"
    assert "not plausible" in backend.calls[1][-1]["content"]


def test_gives_up_after_max_attempts(scripted):
    backend = scripted(["nope", "still nope", "never"])
    result = structured(backend, "Make a person", PERSON, max_attempts=3)
    assert not result.ok and result.calls == 3


def test_picks_the_schema_valid_candidate_among_several(scripted):
    backend = scripted(['Draft: {"name": 1} Final: {"name": "Asha", "age": 30}'])
    result = structured(backend, "Make a person", PERSON)
    assert result.ok and result.value["name"] == "Asha" and result.calls == 1
