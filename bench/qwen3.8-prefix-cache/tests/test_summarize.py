import sys
import unittest
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from summarize import (
    evaluate_ane,
    evaluate_arms,
    evaluate_specprefill,
    gate_record,
    omlx_mtp_gate,
    specprefill_selection,
)


def passing_record(arm="C", scenario="append"):
    return {
        "runtime": "mlx-serve",
        "model_id": "ddalcu/Qwen3.8-27B-MLX-Serve-8bit",
        "arm": arm,
        "context_target": 32768,
        "scenario": scenario,
        "cache_enabled": True,
        "cache_hit_ratio": 0.96,
        "swap_delta_gb": 0.1,
        "ram_peak_gb": 55.0,
        "correct": True,
        "error": None,
    }


def pair_record(arm, context, ttft_ms, **overrides):
    record = passing_record(arm=arm, scenario="cold")
    record.update(
        {
            "context_target": context,
            "session_id": f"session-{arm}-{context}",
            "model_revision": "target-revision",
            "runtime_revision": "v0.6.3rc2",
            "quant": "awq5",
            "temperature": 0,
            "top_p": 0.95,
            "top_k": 20,
            "min_p": 0.0,
            "presence_penalty": 0.0,
            "frequency_penalty": 0.0,
            "repetition_penalty": 1.0,
            "reasoning_effort": "xhigh",
            "max_tokens": 1024,
            "prompt_tokens": 16000,
            "content_class": "audit_retrieval",
            "prompt_identity": f"audit-{context}",
            "fixture_token_hash": "fixture-v1",
            "concurrency": 1,
            "warmup_id": "warmup-v1",
            "repeat": 1,
            "ttft_ms": ttft_ms,
            "e2e_ms": ttft_ms + 20,
            "needle_verdicts": {"10": True, "50": True, "90": True},
            "static_prefix_correct": True,
            "static_prefix_prior_match": True,
            "static_prefix_cached_tokens": 8,
            "static_prefix_boundary_tokens": 8,
            "specprefill_enabled": arm in {"M", "N"},
            "specprefill_keep_pct": 0.40 if arm == "M" else (0.50 if arm == "N" else None),
            "specprefill_threshold": 8192 if arm in {"M", "N"} else None,
            "specprefill_draft_model": "Qwen/Qwen3.5-2B" if arm == "M" else ("Qwen/Qwen3.5-0.8B" if arm == "N" else None),
            "specprefill_draft_revision": "15852e8c16360a2fea060d615a32b45270f8a8fc" if arm == "M" else ("2fc06364715b967f1860aea9cf38778875588b17" if arm == "N" else None),
            "prompt_work_mode": "sparse" if arm in {"M", "N"} else "full",
            "ane_prefill_enabled": arm == "O",
            "ane_compiled_mlp_layers": 2 if arm == "O" else None,
            "ane_compiled_gdn_layers": 1 if arm == "O" else None,
            "ane_executed_operations": 3 if arm == "O" else None,
            "ane_runtime_log_arm": "O" if arm == "O" else None,
            "ane_runtime_log_session_id": f"session-{arm}-{context}" if arm == "O" else None,
            "ane_runtime_log_context": context if arm == "O" else None,
            "ane_runtime_log_compiled_programs": 3 if arm == "O" else None,
            "ane_runtime_log_executed_operations": 3 if arm == "O" else None,
        }
    )
    record.update(overrides)
    return record


def trio(arm, context, ttft_ms, **overrides):
    return [
        pair_record(arm, context, ttft_ms, repeat=repeat, **overrides)
        for repeat in (1, 2, 3)
    ]


def specprefill_fixture(arm="M", candidate_ttft=70):
    records = []
    for context in (16384, 32768):
        records.extend(trio("L", context, 100, scenario="cold", static_prefix_correct=False))
        records.extend(trio(arm, context, candidate_ttft, scenario="cold", static_prefix_correct=False, prompt_work_mode="sparse"))
        records.extend(trio("L", context, 100, scenario="identical", prompt_identity=f"warm-{context}"))
        records.extend(trio(arm, context, candidate_ttft, scenario="identical", prompt_identity=f"warm-{context}", prompt_work_mode="cached"))
    records.append({**pair_record(arm, 32768, 1), "record_type": "verdict", "turns_requested": 20})
    return records


class SummaryTests(unittest.TestCase):
    def test_specprefill_passes_only_after_twenty_percent_ttft_gain_at_both_contexts(self):
        """Relaxing the 20% pairwise TTFT gate must fail this fixture."""
        records = specprefill_fixture("M", 70)

        result = evaluate_specprefill(records)

        self.assertEqual(result["M"]["status"], "PASS")
        self.assertEqual(result["M"]["advance_to_65k"], True)

    def test_specprefill_rejects_mismatched_or_missing_pairing_controls(self):
        """Different builds, prompts, or absent controls must never form a pair."""
        for field, value in (
            ("runtime_revision", "v0.6.4"),
            ("model_id", "other-model"),
            ("scenario", "append"),
            ("max_tokens", 512),
            ("prompt_identity", "other-prompt"),
            ("warmup_id", None),
        ):
            with self.subTest(field=field):
                records = [
                    pair_record("L", 16384, 100), pair_record("M", 16384, 70, **{field: value}),
                    pair_record("L", 32768, 100), pair_record("M", 32768, 70),
                    {**pair_record("M", 65536, 1), "record_type": "verdict", "turns_requested": 20},
                ]
                result = evaluate_specprefill(records)
                self.assertEqual(result["M"]["status"], "FAIL")

    def test_specprefill_rejects_unpaired_or_duplicate_repetitions(self):
        """Medians require the same unique repetition set on both sides."""
        base = [
            pair_record("L", 16384, 100, repeat=1),
            pair_record("L", 16384, 100, repeat=2),
            pair_record("M", 16384, 70, repeat=1),
            pair_record("L", 32768, 100, repeat=1),
            pair_record("L", 32768, 100, repeat=2),
            pair_record("M", 32768, 70, repeat=1),
            {**pair_record("M", 32768, 1), "record_type": "verdict", "turns_requested": 20},
        ]
        self.assertEqual(evaluate_specprefill(base)["M"]["status"], "FAIL")
        duplicate = [dict(record) for record in base]
        duplicate.append(pair_record("M", 16384, 70, repeat=1))
        self.assertEqual(evaluate_specprefill(duplicate)["M"]["status"], "FAIL")

    def test_specprefill_rejects_equally_incomplete_repetition_sets(self):
        """Matching partial runs are not the campaign's three-measurement median."""
        for repeats in ((1,), (1, 2)):
            records = [
                *[pair_record("L", 16384, 100, repeat=repeat) for repeat in repeats],
                *[pair_record("M", 16384, 70, repeat=repeat) for repeat in repeats],
                *[pair_record("L", 32768, 100, repeat=repeat) for repeat in repeats],
                *[pair_record("M", 32768, 70, repeat=repeat) for repeat in repeats],
                {**pair_record("M", 32768, 1), "record_type": "verdict", "turns_requested": 20},
            ]
            self.assertEqual(evaluate_specprefill(records)["M"]["status"], "FAIL")

    def test_specprefill_accepts_sparse_cold_and_cached_warm_evidence(self):
        """A real cache hit must remain cached while the uncached cold work is sparse."""
        records = specprefill_fixture("M", 70)

        result = evaluate_specprefill(records)

        self.assertEqual(result["M"]["status"], "PASS")

    def test_specprefill_requires_the_declared_profile_and_sparse_execution(self):
        """A disabled or wrong M/N profile cannot self-certify its own verdict."""
        records = specprefill_fixture("M", 70)
        for record in records:
            if record.get("arm") == "M" and record.get("scenario") == "cold":
                record["specprefill_enabled"] = False
                record["prompt_work_mode"] = "cached"

        result = evaluate_specprefill(records)

        self.assertEqual(result["M"]["status"], "FAIL")
        self.assertIn("profile", result["M"]["failures"])
        self.assertIn("prompt_work_mode", result["M"]["failures"])

    def test_static_prefix_needs_a_prior_full_boundary_hit_at_each_context(self):
        """A first request or a partial cache hit is not static-prefix evidence."""
        records = [
            pair_record("L", 16384, 100),
            pair_record("M", 16384, 70, static_prefix_prior_match=False, static_prefix_cached_tokens=4, static_prefix_boundary_tokens=8),
            pair_record("L", 32768, 100),
            pair_record("M", 32768, 70, static_prefix_prior_match=True, static_prefix_cached_tokens=8, static_prefix_boundary_tokens=8),
            {**pair_record("M", 32768, 1), "record_type": "verdict", "turns_requested": 20},
        ]

        self.assertIn("static_prefix", evaluate_specprefill(records)["M"]["failures"])

    def test_specprefill_requires_all_needles_static_prefix_and_real_tool_verdict(self):
        """Missing Gate 6 evidence is not a passing substitute for measurement."""
        records = specprefill_fixture("M", 70)
        records = [record for record in records if record.get("record_type") != "verdict"]
        for record in records:
            if record["arm"] == "M":
                record.pop("needle_verdicts")
                record.pop("static_prefix_correct")

        result = evaluate_specprefill(records)

        self.assertEqual(result["M"]["status"], "FAIL")
        self.assertIn("needle_evidence", result["M"]["failures"])
        self.assertIn("static_prefix", result["M"]["failures"])
        self.assertIn("tool_loop", result["M"]["failures"])

    def test_only_one_machine_readable_specprefill_winner_can_advance(self):
        """65K orchestration must consume one selected profile, never an implicit tie."""
        records = specprefill_fixture("M", 70)
        records.extend(
            record for record in specprefill_fixture("N", 75)
            if record.get("arm") == "N"
        )

        selection = specprefill_selection(evaluate_specprefill(records))

        self.assertEqual(selection["winner"]["arm"], "M")
        self.assertEqual(sum(profile["advance_to_65k"] for profile in selection["profiles"].values()), 1)

    def test_specprefill_selection_does_not_promote_a_profile_without_both_contexts(self):
        """A 16K-only improvement cannot leak into the 65K selection file."""
        records = [
            pair_record("L", 16384, 100), pair_record("M", 16384, 70),
            {**pair_record("M", 65536, 1), "record_type": "verdict", "turns_requested": 20},
        ]

        selection = specprefill_selection(evaluate_specprefill(records))

        self.assertIsNone(selection["winner"])

    def test_mtp_gate_requires_isolated_l_evidence(self):
        """SpecPrefill must not run before the L MTP profile records a clean gate."""
        self.assertFalse(omlx_mtp_gate([])["passed"])
        k = trio("K", 32768, 100, content_class="code", prompt_identity="code-32768", fixture_token_hash="code-fixture", mtp_enabled=False, cache_hit_ratio=0.96)
        l = trio("L", 32768, 90, content_class="code", prompt_identity="code-32768", fixture_token_hash="code-fixture", mtp_enabled=True, mtp_acceptance=0.5, cache_hit_ratio=0.96)
        verdict = {**pair_record("L", 32768, 1), "record_type": "verdict", "turns_requested": 20, "specprefill_enabled": False, "mtp_enabled": True}
        self.assertTrue(omlx_mtp_gate([*k, *l, verdict])["passed"])

    def test_specprefill_fails_when_needle_or_tool_loop_fails(self):
        """Ignoring functional failures would incorrectly promote SpecPrefill."""
        records = specprefill_fixture("M", 70)
        for record in records:
            if record.get("arm") == "M" and record.get("scenario") == "cold":
                record["needle_verdicts"] = {"10": False, "50": True, "90": True}
            if record.get("arm") == "M" and record.get("record_type") == "verdict":
                record["correct"] = False

        result = evaluate_specprefill(records)

        self.assertEqual(result["M"]["status"], "FAIL")
        self.assertIn("needle_evidence", result["M"]["failures"])
        self.assertIn("tool_loop", result["M"]["failures"])

    def test_null_stability_telemetry_fails_closed_without_raising(self):
        """Absent macmon data must be a verdict failure, never a TypeError or zero."""
        record = pair_record("M", 16384, 70, ram_peak_gb=None, swap_delta_gb=None)

        self.assertIn("ram_peak_gb_unavailable", gate_record(record))
        self.assertIn("swap_delta_gb_unavailable", gate_record(record))

    def test_ane_passes_at_five_percent_ttft_gain_with_confirmed_operations(self):
        """ANE must be both faster and observed executing operations."""
        records = [*trio("J", 16384, 100), *trio("O", 16384, 95), *trio("J", 32768, 100), *trio("O", 32768, 90)]

        result = evaluate_ane(records)

        self.assertEqual(result["O"]["status"], "PASS")

    def test_ane_accepts_one_context_gain_but_scopes_execution_to_that_context(self):
        """Gate 7 needs one compatible 5% gain, not two, with local O evidence."""
        records = [*trio("J", 16384, 100, specprefill_enabled=False), *trio("O", 16384, 95, specprefill_enabled=False), *trio("J", 32768, 100, specprefill_enabled=False), *trio("O", 32768, 105, specprefill_enabled=False, ane_executed_operations=0)]

        result = evaluate_ane(records)

        self.assertEqual(result["O"]["status"], "PASS")

    def test_ane_requires_enabled_o_and_disabled_specprefill_on_both_arms(self):
        """Activation evidence outside the valid J/O comparison cannot prove ANE."""
        records = [*trio("J", 16384, 100, specprefill_enabled=True), *trio("O", 16384, 90, ane_prefill_enabled=False), *trio("J", 32768, 100), *trio("O", 32768, 90)]

        result = evaluate_ane(records)

        self.assertEqual(result["O"]["status"], "FAIL")
        self.assertIn("confounded_specprefill", result["O"]["failures"])
        self.assertIn("ane_not_enabled", result["O"]["failures"])

    def test_ane_is_inconclusive_without_executed_operations(self):
        """Compiled but unused ANE paths cannot establish an acceleration result."""
        records = [
            pair_record("J", 16384, 100),
            pair_record("O", 16384, 90, ane_compiled_mlp_layers=0, ane_compiled_gdn_layers=0, ane_executed_operations=0),
            pair_record("J", 32768, 100),
            pair_record("O", 32768, 90, ane_compiled_mlp_layers=0, ane_compiled_gdn_layers=0, ane_executed_operations=0),
        ]

        result = evaluate_ane(records)

        self.assertEqual(result["O"]["status"], "INCONCLUSIVE")

    def test_ane_is_inconclusive_when_layers_compile_but_execute_zero_operations(self):
        """Compilation without observed execution cannot satisfy the ANE gate."""
        records = [
            pair_record("J", 16384, 100),
            pair_record("O", 16384, 90, ane_executed_operations=0),
            pair_record("J", 32768, 100),
            pair_record("O", 32768, 90, ane_executed_operations=0),
        ]

        result = evaluate_ane(records)

        self.assertEqual(result["O"]["status"], "INCONCLUSIVE")

    def test_ane_rejects_runtime_log_evidence_from_a_different_session(self):
        """A compiled warmup log cannot be bound to a later measured request."""
        records = [
            pair_record("J", 16384, 100),
            pair_record("O", 16384, 90, ane_runtime_log_session_id="warmup-o"),
            pair_record("J", 32768, 100),
            pair_record("O", 32768, 90),
        ]

        result = evaluate_ane(records)

        self.assertEqual(result["O"]["status"], "INCONCLUSIVE")
    def test_good_append_record_passes(self):
        self.assertEqual(gate_record(passing_record()), [])

    def test_bad_tool_record_lists_every_independent_failure(self):
        record = passing_record(scenario="tool_turn")
        record.update(
            {
                "cache_hit_ratio": 0.5,
                "swap_delta_gb": 1.0,
                "ram_peak_gb": 90.0,
                "correct": False,
                "error": "HTTP 500",
            }
        )

        failures = gate_record(record)

        self.assertEqual(
            failures,
            [
                "cache_hit_ratio",
                "swap_delta_gb",
                "ram_peak_gb",
                "correct",
                "error",
            ],
        )

    def test_cache_disabled_control_does_not_fail_for_expected_miss(self):
        record = passing_record(arm="A", scenario="identical")
        record.update({"cache_enabled": False, "cache_hit_ratio": 0.0})

        self.assertEqual(gate_record(record), [])

    def test_middle_mutation_rejects_reuse_far_past_halfway_boundary(self):
        record = passing_record(scenario="middle_mutation")
        record["cache_hit_ratio"] = 0.90

        self.assertEqual(gate_record(record), ["middle_mutation_reuse"])

    def test_evaluation_keeps_all_passing_production_arms(self):
        mlx = passing_record(arm="C")
        gguf = passing_record(arm="F")
        gguf.update(
            {
                "runtime": "llama.cpp",
                "model_id": "unsloth/Qwen3.8-27B-GGUF:UD-Q4_K_XL",
            }
        )
        failed = passing_record(arm="G")
        failed.update(
            {
                "runtime": "llama.cpp",
                "model_id": "unsloth/Qwen3.8-27B-GGUF:UD-Q6_K_XL",
                "correct": False,
            }
        )

        evaluations = evaluate_arms([mlx, gguf, failed])

        self.assertTrue(evaluations["C"]["passed"])
        self.assertTrue(evaluations["F"]["passed"])
        self.assertFalse(evaluations["G"]["passed"])
        self.assertEqual(evaluations["G"]["failures"], ["correct"])


if __name__ == "__main__":
    unittest.main()
