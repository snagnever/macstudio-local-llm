from dataclasses import dataclass
from hashlib import sha256
import re
from struct import pack
from typing import Callable


@dataclass(frozen=True)
class PromptFixture:
    text: str
    token_ids: list[int]
    needles: tuple[str, ...]
    question: str = ""


NEEDLES = (
    "XENON-7592-FALCON",
    "ARGON-1844-EMBER",
    "NEON-6301-ORBIT",
)
CODE_RESULT = "CODE-RESULT-32896"
CODE_QUESTION = (
    "Review the deterministic Python program and return only its asserted result: "
    f"{CODE_RESULT}."
)


def _record(index: int) -> str:
    return (
        f"Record {index:06d} stores audit value {index * 7919 % 104729:06d}. "
        f"Its owner is unit-{index % 97:02d} and its revision is r{index % 31:02d}."
    )


def build_fixture(
    target_tokens: int, encode: Callable[[str], list[int]]
) -> PromptFixture:
    if target_tokens <= 0:
        raise ValueError("target_tokens must be positive")

    records: list[str] = []
    index = 0
    token_ids: list[int] = []
    while len(token_ids) < target_tokens:
        records.append(_record(index))
        index += 1
        token_ids = encode("\n".join(records))

    for fraction, needle in zip((0.1, 0.5, 0.9), NEEDLES):
        position = min(len(records) - 1, int(len(records) * fraction))
        records[position] += f" Verified key: {needle}."

    text = "\n".join(records)
    return PromptFixture(
        text=text,
        token_ids=encode(text),
        needles=NEEDLES,
        question=(
            "Return only the three verified keys stored closest to 10%, 50%, and 90% "
            "of the audit records, in that order."
        ),
    )


def build_code_fixture(
    target_tokens: int, encode: Callable[[str], list[int]]
) -> PromptFixture:
    """Build a deterministic, verifiable Python workload for the MTP gate."""
    if target_tokens <= 0:
        raise ValueError("target_tokens must be positive")
    code = [
        "def rolling_checksum(values):",
        "    total = 0",
        "    for value in values:",
        "        total = (total + value) % 65537",
        "    return total",
        "",
        "INPUT = list(range(1, 257))",
        "EXPECTED = 32896",
        "assert rolling_checksum(INPUT) == EXPECTED",
        f"# Required response marker: {CODE_RESULT}",
    ]
    index = 0
    token_ids = encode("\n".join(code))
    while len(token_ids) < target_tokens:
        code.append(
            f"# Deterministic code review note {index:06d}: preserve the loop invariant."
        )
        index += 1
        token_ids = encode("\n".join(code))
    text = "\n".join(code)
    return PromptFixture(
        text=text,
        token_ids=encode(text),
        needles=(CODE_RESULT,),
        question=CODE_QUESTION,
    )


def build_suffix(
    target_tokens: int, encode: Callable[[str], list[int]], trailer: str
) -> tuple[str, list[int]]:
    if target_tokens <= 0:
        raise ValueError("target_tokens must be positive")

    def render(count: int) -> str:
        filler = [f"append-record-{index:06d}" for index in range(count)]
        return " ".join([*filler, trailer])

    low = 0
    high = 1
    while len(encode(render(high))) < target_tokens:
        low = high
        high *= 2

    while low + 1 < high:
        middle = (low + high) // 2
        if len(encode(render(middle))) < target_tokens:
            low = middle
        else:
            high = middle

    text = render(high)
    return text, encode(text)


def mutate_middle(text: str, count: int) -> tuple[str, int]:
    words = text.split()
    if count <= 0:
        raise ValueError("count must be positive")
    if count > len(words):
        raise ValueError("count cannot exceed the number of words")

    boundary = max(0, len(words) // 2 - count // 2)
    end = boundary + count
    mutations = [f"mutation-{index:03d}" for index in range(count)]
    changed = words[:boundary] + mutations + words[end:]
    return " ".join(changed), boundary


def _token_difference_span(
    original: list[int], changed: list[int]
) -> tuple[int, int]:
    prefix = 0
    limit = min(len(original), len(changed))
    while prefix < limit and original[prefix] == changed[prefix]:
        prefix += 1

    suffix = 0
    remaining = limit - prefix
    while (
        suffix < remaining
        and original[len(original) - 1 - suffix]
        == changed[len(changed) - 1 - suffix]
    ):
        suffix += 1
    span = max(
        len(original) - prefix - suffix,
        len(changed) - prefix - suffix,
    )
    return prefix, span


def mutate_middle_tokens(
    text: str, target_tokens: int, encode: Callable[[str], list[int]]
) -> tuple[str, int, int]:
    if target_tokens <= 0:
        raise ValueError("target_tokens must be positive")
    words = text.split()
    if not words:
        raise ValueError("text must contain words")
    original_tokens = encode(text)
    word_matches = list(re.finditer(r"\S+", text))

    def candidate(word_count: int) -> tuple[str, int, int]:
        boundary = max(0, len(words) // 2 - word_count // 2)
        end = min(len(words), boundary + word_count)
        pieces: list[str] = []
        cursor = 0
        for replacement_index, match in enumerate(
            word_matches[boundary:end]
        ):
            pieces.append(text[cursor : match.start()])
            pieces.append(f"mutation-{replacement_index:03d}")
            cursor = match.end()
        pieces.append(text[cursor:])
        changed = "".join(pieces)
        prefix, span = _token_difference_span(original_tokens, encode(changed))
        return changed, prefix, span

    low = 1
    high = 1
    high_result = candidate(high)
    while high_result[2] < target_tokens and high < len(words):
        low = high
        high = min(len(words), high * 2)
        high_result = candidate(high)

    while low + 1 < high:
        middle = (low + high) // 2
        result = candidate(middle)
        if result[2] < target_tokens:
            low = middle
        else:
            high = middle

    choices = [
        candidate(count)
        for count in range(max(1, low - 4), min(len(words), high + 4) + 1)
    ]
    return min(choices, key=lambda value: abs(value[2] - target_tokens))


def sha256_tokens(token_ids: list[int]) -> str:
    digest = sha256()
    for token_id in token_ids:
        digest.update(pack(">I", token_id))
    return digest.hexdigest()
