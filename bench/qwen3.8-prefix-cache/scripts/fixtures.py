from dataclasses import dataclass
from hashlib import sha256
from struct import pack
from typing import Callable


@dataclass(frozen=True)
class PromptFixture:
    text: str
    token_ids: list[int]
    needles: tuple[str, str, str]


NEEDLES = (
    "XENON-7592-FALCON",
    "ARGON-1844-EMBER",
    "NEON-6301-ORBIT",
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
    return PromptFixture(text=text, token_ids=encode(text), needles=NEEDLES)


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


def sha256_tokens(token_ids: list[int]) -> str:
    digest = sha256()
    for token_id in token_ids:
        digest.update(pack(">I", token_id))
    return digest.hexdigest()
