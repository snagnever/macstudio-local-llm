import sys
import unittest
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from sse_client import iter_sse_json, normalize_mlx_dspark_metrics, stream_delta_fields


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

    def test_normalizes_only_observed_v0150_dspark_telemetry(self):
        normalized = normalize_mlx_dspark_metrics(
            {
                "mode": "dflash",
                "ttft_seconds": 0.123,
                "prefill_seconds": 0.100,
                "decode_seconds": 1.5,
                "cached_tokens": 4096,
                "accept_len": 3.25,
                "cap": 7,
                "decode_tokens_per_sec": 42.0,
                "ceiling_tokens_per_sec": 51.0,
                "roofline_ratio": 0.824,
                "target_forwards": 160,
            },
            {"verdict": {"decode_tps": 42.0}},
        )

        self.assertEqual(normalized["speculation_mode"], "dflash")
        self.assertEqual(normalized["ttft_ms"], 123.0)
        self.assertEqual(normalized["prefill_ms"], 100.0)
        self.assertEqual(normalized["decode_ms"], 1500.0)
        self.assertEqual(normalized["cached_tokens"], 4096)
        self.assertEqual(normalized["accept_length"], 3.25)
        self.assertEqual(normalized["draft_cap_resolved"], 7)
        self.assertEqual(normalized["decode_tps"], 42.0)
        self.assertEqual(normalized["machine_roofline_tps"], 51.0)
        self.assertEqual(normalized["decode_roofline_ratio"], 0.824)
        self.assertEqual(normalized["verification_steps"], 160)
        self.assertIsNone(normalized["accepted_tokens"])


if __name__ == "__main__":
    unittest.main()
