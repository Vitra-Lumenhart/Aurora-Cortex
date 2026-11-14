"""Contract tests for VNN state projection. Run: python3 -m unittest discover -s tests -p 'test_vnn_*.py'"""
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from vnn.presence import ContractError, project, safe_media_path, write_public_json

FIXED = datetime(2026, 11, 11, 21, 0, tzinfo=timezone.utc)


def fixture(state="cue_pending"):
    if state in {"standby", "emergency"}:
        cue = None
    else:
        cue = {
            "cue_id": "cue:example",
            "state": state,
            "started_at": "2026-11-11T20:59:59Z" if state == "presenting" else None,
            "segment": {
                "segment_id": "seg:one", "kind": "daily", "title": "A working witness",
                "script": "SECRET BROADCAST SCRIPT - MUST NOT LEAK",
                "source_refs": ["PRIVATE_SOURCE"],
                "stance": "commentary", "sigma": 0.2,
                "origin_node": "secret_peer",
            },
        }
    return {"kind": "broadcast_cue_surface", "version": "0.1.0",
            "state": state, "cue": cue, "public_name": "vitra.ams",
            "chat_name": "news.vitra.ams"}


class PresenceTests(unittest.TestCase):
    def test_pending_not_presenting(self):
        p = project(fixture(), now=FIXED)
        self.assertEqual(p["state"], "cue_pending")
        self.assertEqual(p["state_verified_by"], "scheduler_intent")

    def test_presenting_requires_renderer_ack(self):
        f = fixture("presenting")
        f["cue"]["started_at"] = None
        with self.assertRaises(ContractError):
            project(f, now=FIXED)

    def test_presenting_ack_is_not_viewer_delivery(self):
        p = project(fixture("presenting"), now=FIXED)
        self.assertEqual(p["state_verified_by"], "renderer_started_ack")
        self.assertIn("not proof of viewer delivery", p["limitations"])

    def test_secrets_never_in_projection(self):
        p = project(fixture(), now=FIXED)
        dump = json.dumps(p)
        for private in ("SECRET BROADCAST SCRIPT", "PRIVATE_SOURCE", "secret_peer", "cue:example"):
            self.assertNotIn(private, dump)

    def test_no_video_without_explicit_review(self):
        items = {"seg:one": {"approved": False, "video": "/news/media/a.mp4"}}
        p = project(fixture("presenting"), media_map=items, now=FIXED)
        self.assertIsNone(p["media"]["video"])

    def test_reviewed_media_is_referenced_not_republished(self):
        items = {"seg:one": {"approved": True, "video": "/news/media/story-01/cut.mp4",
                             "poster": "/news/media/story-01/poster.webp"}}
        p = project(fixture("presenting"), media_map=items, now=FIXED)
        self.assertEqual(p["media"]["video"], "/news/media/story-01/cut.mp4")
        self.assertEqual(p["media"]["visibility"], "ams_only")

    def test_reject_external_or_traversal(self):
        for path in ("https://youtube.com/watch?v=123", "//elsewhere/a.mp4",
                     "/news/media/../private", "/news/media/x%2fsecret.mp4",
                     "/news/media/a.mp4?token=private"):
            with self.subTest(path=path), self.assertRaises(ContractError):
                safe_media_path(path)

    def test_audition_presets_and_controls(self):
        entry = {"seg:one": {"gesture": "listening_lantern", "amplitude": .72,
                             "tempo": .85, "restraint": .60}}
        p = project(fixture(), expression_map=entry, now=FIXED)
        self.assertEqual(p["face"]["gesture"], "listening_lantern")
        self.assertEqual(p["face"]["restraint"], .6)

    def test_unreviewed_pose_not_inferred(self):
        self.assertEqual(project(fixture(), now=FIXED)["face"]["gesture"], "still_point")

    def test_emergency_has_no_program(self):
        p = project(fixture("emergency"), now=FIXED)
        self.assertEqual(p["state"], "emergency")
        self.assertIsNone(p["program"])

    def test_refuse_inconsistent_states(self):
        packet = fixture()
        packet["cue"]["state"] = "presenting"
        with self.assertRaises(ContractError):
            project(packet, now=FIXED)

    def test_atomic_write(self):
        with tempfile.TemporaryDirectory() as root:
            output = Path(root) / "news" / "state.json"
            p = project(fixture(), now=FIXED)
            write_public_json(output, p)
            self.assertEqual(json.loads(output.read_text())["schema"], "aurora.broadcast/1")


if __name__ == "__main__":
    unittest.main()
