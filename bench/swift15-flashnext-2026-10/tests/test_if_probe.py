import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import if_probe  # noqa: E402

C = if_probe.CHECKERS


@pytest.mark.parametrize("name,args,good,bad", [
    ("all_lowercase", (), "soft rain falls.", "Soft rain falls."),
    ("all_uppercase", (), "GO FOR IT!", "Go for it!"),
    ("no_commas", (), "a b c", "a, b"),
    ("word_count_max", (5,), "one two three four", "one two three four five"),
    ("word_count_min", (3,), "one two three", "one two"),
    ("bullet_count", (2,), "- a\n- b", "- a\n- b\n- c"),
    ("json_keys", (["name", "age"],), '```json\n{"name": "A", "age": 3}\n```', '{"name": "A"}'),
    ("json_array_len", (3,), "[2, 3, 5]", "[2, 3]"),
    ("ends_with", ("Bye.",), "Hello. Bye.", "Bye. Hello."),
    ("starts_with", ("Absolutely",), "Absolutely, yes.", "Yes, absolutely."),
    ("includes", (["sunrise", "ritual"],), "A Sunrise ritual.", "A sunrise."),
    ("excludes", (["tree"],), "Tall pines.", "A tree."),
    ("paragraphs_by_divider", (2,), "One.\n***\nTwo.", "One.\n\nTwo."),
    ("has_title", (), "<<The Sea>>\nwaves", "The Sea\nwaves"),
    ("placeholder_min", (2,), "Dear [name], at [company]", "Dear [name]"),
    ("wrapped_in_quotes", (), '"Mars is red."', "Mars is red."),
    ("section_count", (2,), "SECTION 1\na\nSECTION 2\nb", "SECTION 1\na"),
    ("has_postscript", ("P.S.",), "Poem.\nP.S. bye", "Poem. bye"),
])
def test_checker(name, args, good, bad):
    assert C[name](good, *args) is True
    assert C[name](bad, *args) is False


def test_cases_use_known_checkers_and_unique_ids():
    assert len(if_probe.CASES) == 20
    assert len({c["id"] for c in if_probe.CASES}) == 20
    for case in if_probe.CASES:
        for name, *_ in case["checks"]:
            assert name in C, (case["id"], name)


def test_grade_reports_each_check():
    case = {"id": "x", "prompt": "", "checks": [("no_commas",), ("word_count_max", 3)]}
    assert if_probe.grade(case, "a b") == {"no_commas": True, "word_count_max": True}
    assert if_probe.grade(case, "a, b c d") == {"no_commas": False, "word_count_max": False}


def test_split_reasoning_inline_think():
    assert if_probe.split_reasoning({"content": "<think>ab</think> ok"}) == ("ok", "ab")


def test_build_body_vendor_sampling():
    body = if_probe.build_body("m", "p", "xhigh", 100, 1.0, {"top_p": 0.95, "top_k": 20})
    assert body == {"model": "m", "messages": [{"role": "user", "content": "p"}], "temperature": 1.0,
                    "max_tokens": 100, "top_p": 0.95, "top_k": 20, "reasoning_effort": "xhigh"}


def test_build_body_t0_has_no_extras():
    body = if_probe.build_body("m", "p", None, 100, 0.0, {})
    assert set(body) == {"model", "messages", "temperature", "max_tokens"}


def test_select_cases():
    assert [c["id"] for c in if_probe.select_cases("if07,if01")] == ["if01", "if07"]
    assert len(if_probe.select_cases(None)) == 20
    with pytest.raises(SystemExit):
        if_probe.select_cases("if99")
