import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from campaign_supervisor import DEFAULT_STAGES, ScreenClient, Supervisor


class FakeScreen:
    def __init__(self, sessions=()):
        self.sessions = set(sessions)
        self.launches = []

    def list_sessions(self):
        return set(self.sessions)

    def launch(self, session, stage, log_path, exit_path):
        self.launches.append((session, stage, log_path, exit_path))
        self.sessions.add(session)


class CampaignSupervisorTests(unittest.TestCase):
    def make_supervisor(self, root, screen, stages=("phase-a", "phase-b")):
        return Supervisor(
            state_path=root / "state.json",
            log_dir=root / "logs",
            stages=list(stages),
            screen=screen,
            session_prefix="qwen38-campaign",
            ignored_sessions={"qwen38-supervisor20", "qwen38-monitor20"},
            now=lambda: "2026-08-23T20:00:00Z",
        )

    def read_state(self, root):
        return json.loads((root / "state.json").read_text())

    def test_once_launches_first_pending_stage_and_persists_running_state(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            screen = FakeScreen()
            supervisor = self.make_supervisor(root, screen)

            state = supervisor.once()

            self.assertEqual(state["status"], "running")
            self.assertEqual(state["stage"], "phase-a")
            self.assertEqual(len(screen.launches), 1)
            self.assertEqual(screen.launches[0][1], "phase-a")
            self.assertEqual(self.read_state(root)["stage"], "phase-a")

    def test_once_does_not_duplicate_an_active_stage_and_tracks_progress(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            screen = FakeScreen()
            supervisor = self.make_supervisor(root, screen)
            first = supervisor.once()
            log_path = Path(first["log_path"])
            log_path.write_text("measurement\n")

            state = supervisor.once()

            self.assertEqual(state["status"], "running")
            self.assertEqual(state["log_size"], len("measurement\n"))
            self.assertEqual(state["stalled_checks"], 0)
            self.assertEqual(len(screen.launches), 1)

    def test_success_marker_advances_and_launches_next_stage_immediately(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            screen = FakeScreen()
            supervisor = self.make_supervisor(root, screen)
            first = supervisor.once()
            screen.sessions.clear()
            Path(first["exit_path"]).write_text("0\n")

            state = supervisor.once()

            self.assertEqual(state["status"], "running")
            self.assertEqual(state["stage"], "phase-b")
            self.assertEqual(state["completed_stages"], ["phase-a"])
            self.assertEqual([launch[1] for launch in screen.launches], ["phase-a", "phase-b"])

    def test_failure_marker_requires_agent_review_without_blind_retry(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            screen = FakeScreen()
            supervisor = self.make_supervisor(root, screen)
            first = supervisor.once()
            screen.sessions.clear()
            Path(first["exit_path"]).write_text("1\n")

            state = supervisor.once()

            self.assertEqual(state["status"], "needs_agent_review")
            self.assertEqual(state["stage"], "phase-a")
            self.assertEqual(state["exit_code"], 1)
            self.assertEqual(len(screen.launches), 1)

    def test_external_campaign_session_defers_launch(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            screen = FakeScreen({"qwen38-manual-runtime"})
            supervisor = self.make_supervisor(root, screen)

            state = supervisor.once()

            self.assertEqual(state["status"], "external_busy")
            self.assertEqual(state["external_sessions"], ["qwen38-manual-runtime"])
            self.assertEqual(screen.launches, [])

    def test_default_queue_runs_mtplx_before_the_oq4e_ablation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            screen = FakeScreen()
            supervisor = self.make_supervisor(root, screen, DEFAULT_STAGES[:4])

            state = supervisor.once()
            for _ in range(3):
                screen.sessions.clear()
                Path(state["exit_path"]).write_text("0\n")
                state = supervisor.once()

            self.assertEqual(
                [launch[1] for launch in screen.launches],
                [
                    "omlx-oq8e-smoke",
                    "mtplx-smoke",
                    "mtplx-32k",
                    "omlx-oq4e-dflash-32k",
                ],
            )

    @patch("campaign_supervisor.subprocess.run")
    def test_screen_launch_does_not_inherit_a_parent_screen_session(self, run):
        with patch.dict(os.environ, {"STY": "99598.qwen38-supervisor20"}):
            client = ScreenClient("screen", Path("wrapper.sh"), Path("repo"))

            client.launch(
                "qwen38-campaign-phase",
                "phase-a",
                Path("phase.log"),
                Path("phase.exit"),
            )

        self.assertNotIn("STY", run.call_args.kwargs["env"])


if __name__ == "__main__":
    unittest.main()
