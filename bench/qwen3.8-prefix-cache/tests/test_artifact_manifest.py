import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from artifact_manifest import artifact_records, model_records


class ArtifactManifestTests(unittest.TestCase):
    def test_records_files_with_relative_path_size_and_sha256(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "nested").mkdir()
            artifact = root / "nested" / "weights.gguf"
            artifact.write_bytes(b"pinned-weights")

            records = artifact_records(root)

        self.assertEqual(
            records,
            [
                {
                    "path": "nested/weights.gguf",
                    "size_bytes": 14,
                    "sha256": hashlib.sha256(b"pinned-weights").hexdigest(),
                }
            ],
        )

    def test_builds_repeatable_model_records_and_rejects_missing_weights(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = root / "first"
            second = root / "second"
            first.mkdir()
            second.mkdir()
            (first / "model.safetensors").write_bytes(b"first")
            (second / "model.gguf").write_bytes(b"second")

            records = model_records(
                [("vendor/first", "rev-a", first), ("vendor/second", "rev-b", second)]
            )

            self.assertEqual(
                [(record["model_id"], record["revision"]) for record in records],
                [("vendor/first", "rev-a"), ("vendor/second", "rev-b")],
            )
            self.assertEqual(records[0]["files"][0]["path"], "model.safetensors")

            cache = second / ".cache" / "huggingface" / "download"
            cache.mkdir(parents=True)
            (cache / "model.gguf.incomplete").write_bytes(b"partial")
            # A completed local-dir may retain stale cache fragments from an
            # interrupted parallel attempt; only final artifact files count.
            self.assertEqual(
                model_records([("vendor/second", "rev-b", second)])[0]["model_id"],
                "vendor/second",
            )

            partial = root / "partial"
            partial.mkdir()
            (partial / "config.json").write_text("{}", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "no model weights"):
                model_records([("vendor/partial", "rev-c", partial)])

            indexed = root / "indexed"
            indexed.mkdir()
            (indexed / "model-00001-of-00002.safetensors").write_bytes(b"one")
            (indexed / "model.safetensors.index.json").write_text(
                json.dumps(
                    {
                        "weight_map": {
                            "layer.0": "model-00001-of-00002.safetensors",
                            "layer.1": "model-00002-of-00002.safetensors",
                        }
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "missing indexed weight files"):
                model_records([("vendor/indexed", "rev-d", indexed)])


if __name__ == "__main__":
    unittest.main()
