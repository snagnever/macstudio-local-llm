import sys
import unittest
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from sse_client import iter_sse_json


class SseTests(unittest.TestCase):
    def test_parser_yields_json_chunks_and_stops_at_done(self):
        lines = [
            b'data: {"choices":[{"delta":{"content":"A"}}]}\n',
            b"\n",
            b'data: {"choices":[{"delta":{"content":"B"}}]}\n',
            b"data: [DONE]\n",
            b'data: {"choices":[{"delta":{"content":"ignored"}}]}\n',
        ]

        chunks = list(iter_sse_json(lines))

        self.assertEqual(len(chunks), 2)
        self.assertEqual(chunks[0]["choices"][0]["delta"]["content"], "A")
        self.assertEqual(chunks[1]["choices"][0]["delta"]["content"], "B")

    def test_parser_ignores_comments_and_non_data_lines(self):
        lines = [
            b": ping\n",
            b"event: message\n",
            b'data: {"usage":{"prompt_tokens":8}}\n',
        ]

        chunks = list(iter_sse_json(lines))

        self.assertEqual(chunks, [{"usage": {"prompt_tokens": 8}}])


if __name__ == "__main__":
    unittest.main()
