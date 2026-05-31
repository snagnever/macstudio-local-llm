#!/usr/bin/env python3
"""Reproducer: mlx-lm tool-call detection misses calls when the tokenizer merges
the marker's trailing '>' with the following character.

mlx-lm detects tool calls with an Aho-Corasick SequenceStateMachine over exact
token-id sequences. The json_tools parser's start marker "<tool_call>" is encoded
in isolation -> tokens ending in a standalone '>' (e.g. id 32). But a model emitting
the standard Hermes shape "<tool_call>\n{...}" produces ">\n" as ONE merged token,
so the precomputed marker is never a contiguous subsequence of the generated stream
and the state machine never enters the "tool" capture state -> the call is returned
as assistant text, tool_calls stays null.

Usage:  python repro_marker_merge.py <model_path_with_<tool_call>_NOT_a_special_token>
        (e.g. mlx-community/DeepSeek-V4-Flash-2bit-DQ; tokenizer only, no GPU)
"""
import sys
from pathlib import Path
from mlx_lm.tokenizer_utils import load as load_tokenizer
from mlx_lm.generate import SequenceStateMachine

tok = load_tokenizer(Path(sys.argv[1]))
enc = lambda s: tuple(tok.encode(s, add_special_tokens=False))

print("tokenizer: '>' stays a standalone token only at end-of-string")
for s in ("<tool_call>", "<tool_call>\n", "<tool_call>{"):
    print(f"  encode({s!r})[-2:] = {enc(s)[-2:]}  last piece = {tok.decode([enc(s)[-1]])!r}")

STOCK  = enc("<tool_call>")   # what mlx-lm precomputes for tool_parser_type=json_tools
PREFIX = enc("<tool_call")    # proposed robust start marker
END    = enc("</tool_call>")
emitted = enc('<tool_call>\n{"name": "get_weather", "arguments": {"city": "Paris"}}\n</tool_call>')

def enters_tool(start_marker):
    sm = SequenceStateMachine(
        {"normal": [(start_marker, "tool")], "tool": [(END, "normal")]}, initial="normal")
    st = sm.make_state(); seen = set()
    for x in emitted:
        st, _, s = SequenceStateMachine.match(st, x); seen.add(s)
    return "tool" in seen

print(f"\nstock  marker <tool_call> = {STOCK}  -> enters 'tool': {enters_tool(STOCK)}")
print(f"prefix marker <tool_call  = {PREFIX}  -> enters 'tool': {enters_tool(PREFIX)}")
assert enters_tool(STOCK) is False and enters_tool(PREFIX) is True, "repro did not reproduce"
print("\nBUG REPRODUCED: stock marker misses; prefix marker catches it.")
