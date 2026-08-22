import sys
import unittest
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from fixtures import build_fixture, build_suffix, mutate_middle, sha256_tokens


class FixtureTests(unittest.TestCase):
    def test_suffix_reaches_1024_token_target_and_keeps_trailer(self):
        suffix, token_ids = build_suffix(
            1024, str.split, "Return the verified key."
        )

        self.assertEqual(len(token_ids), 1024)
        self.assertTrue(suffix.endswith("Return the verified key."))

    def test_fixture_reaches_target_and_places_three_needles(self):
        fixture = build_fixture(8192, str.split)

        self.assertGreaterEqual(len(fixture.token_ids), 8192)
        self.assertEqual(
            fixture.needles,
            (
                "XENON-7592-FALCON",
                "ARGON-1844-EMBER",
                "NEON-6301-ORBIT",
            ),
        )
        for needle in fixture.needles:
            self.assertIn(needle, fixture.text)

    def test_middle_mutation_changes_requested_span_after_stable_prefix(self):
        original = " ".join(f"w{i}" for i in range(1000))

        changed, boundary = mutate_middle(original, 64)

        self.assertEqual(original.split()[:boundary], changed.split()[:boundary])
        self.assertEqual(len(original.split()), len(changed.split()))
        self.assertNotEqual(
            original.split()[boundary : boundary + 64],
            changed.split()[boundary : boundary + 64],
        )
        self.assertEqual(
            original.split()[boundary + 64 :],
            changed.split()[boundary + 64 :],
        )

    def test_token_hash_changes_when_one_token_changes(self):
        first = sha256_tokens([1, 2, 3])

        self.assertEqual(first, sha256_tokens([1, 2, 3]))
        self.assertNotEqual(first, sha256_tokens([1, 2, 4]))


if __name__ == "__main__":
    unittest.main()
