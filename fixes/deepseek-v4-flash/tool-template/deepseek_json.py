# Custom mlx-lm tool parser for DeepSeek-V4-Flash (+ the tool template).
# Deploy into venv: mlx_lm/tool_parsers/deepseek_json.py, and set
# tokenizer_config.json "tool_parser_type": "deepseek_json".
#
# Why not the stock json_tools parser: its start marker "<tool_call>" encodes to
# tokens (<, tool, _call, >). When the model emits "<tool_call>\n", BPE greedily
# merges ">" with the following "\n" into a single ">\n" token, so the precomputed
# 4-token marker is never a subsequence of the generated stream and mlx-lm's state
# machine never enters tool-capture mode. Dropping the ">" from the start marker
# ("<tool_call") matches the stable (<, tool, _call) prefix regardless of what
# follows, and a brace-balanced JSON extractor tolerates the leftover ">" / newline
# and the trailing "</tool_call>".
import json

tool_call_start = "<tool_call"
tool_call_end = "</tool_call>"


def parse_tool_call(text, tools=None):
    """Extract the first balanced {...} JSON object from the captured segment."""
    start = text.find("{")
    if start == -1:
        raise ValueError("no JSON object in tool call segment")
    depth = 0
    in_str = False
    esc = False
    for i in range(start, len(text)):
        c = text[i]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
            continue
        if c == '"':
            in_str = True
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return json.loads(text[start : i + 1])
    raise ValueError("unbalanced JSON in tool call segment")
