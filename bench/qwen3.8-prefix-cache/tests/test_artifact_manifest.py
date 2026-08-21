import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from artifact_manifest import artifact_records


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


if __name__ == "__main__":
    unittest.main()
