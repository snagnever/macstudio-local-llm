import sys
import unittest
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from sse_client import iter_sse_json, stream_delta_fields


class SseTests(unittest.TestCase):
    def test_stream_fields_keep_reasoning_separate_from_visible_content(self):
        chunks = [
            {
                "choices": [
                    {"delta": {"reasoning_content": "hidden key"}, "finish_reason": None}
                ]
            },
            {
                "choices": [
                    {"delta": {"content": "visible answer"}, "finish_reason": "stop"}
                ],
                "usage": {"completion_tokens": 7},
            },
        ]

        fields = stream_delta_fields(chunks)

        self.assertEqual(fields["content"], "visible answer")
        self.assertEqual(fields["reasoning"], "hidden key")
        self.assertEqual(fields["finish_reason"], "stop")
        self.assertEqual(fields["usage"], {"completion_tokens": 7})

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

    def test_stream_fields_keep_top_level_omlx_extension(self):
        fields = stream_delta_fields(
            [{"usage": {"prompt_tokens": 8}, "x_omlx": {"prompt_work_mode": "sparse"}}]
        )

        self.assertEqual(fields["usage"]["x_omlx"]["prompt_work_mode"], "sparse")

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
