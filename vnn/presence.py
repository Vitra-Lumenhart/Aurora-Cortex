#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""VNN / Aurora broadcast-state projection v0.1.

Reads the PRIVATE, 0600 broadcast.py cue.json and produces a tiny, explicitly
public *presentation projection*. It does not schedule, approve, render, stream,
speak, authenticate, or manage Vitra's Book 0/1/2 records.

Security invariant: this module is NOT an access control layer. Deploy the
output only behind the .ams VPN's authenticated reverse proxy, never in a
public S3 bucket/GitHub Pages/ordinary public cache.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path, PurePosixPath
from typing import Any

SCHEMA = "aurora.broadcast/1"
EXPECTED_INPUT = "broadcast_cue_surface"
CUE_STATES = frozenset({"cue_pending", "presenting", "standby", "emergency"})
ACTIVE_STATES = frozenset({"cue_pending", "presenting"})
GESTURES = frozenset({
    "listening_lantern", "suppressed_delight", "receipt_check",
    "sudden_connection", "gentle_witness", "behind_the_veil",
    "still_point", "return_to_the_room",
})
MEDIA_PREFIX = "/news/media/"
MEDIA_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,255}$")


class ContractError(ValueError):
    """The submitted surface is not a valid broadcast.py v0.1 cue."""


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def zulu(dt: datetime) -> str:
    if dt.tzinfo is None:
        raise ContractError("timestamp must be timezone-aware")
    return dt.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def safe_media_path(path: Any) -> str | None:
    """No arbitrary URLs, origins, traversal, query strings, or opaque tokens."""
    if path is None:
        return None
    if not isinstance(path, str) or not path.startswith(MEDIA_PREFIX):
        raise ContractError("media paths must be within /news/media/")
    remainder = path[len(MEDIA_PREFIX):]
    if not MEDIA_RE.fullmatch(remainder):
        raise ContractError("invalid media filename")
    parts = PurePosixPath(remainder).parts
    if not parts or any(p in ("", ".", "..") for p in remainder.split("/")):
        raise ContractError("media path traversal/empty component")
    return path


def safe_label(value: Any, max_len: int = 200) -> str:
    if not isinstance(value, str):
        raise ContractError("expected text label")
    text = value.strip()
    if not text or len(text) > max_len or any(ord(c) < 32 for c in text):
        raise ContractError("invalid or oversized text label")
    return text


def clamp_unit(value: Any, label: str, default: float) -> float:
    if value is None:
        return default
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ContractError(label + " must be numeric")
    if not 0 <= value <= 1:
        raise ContractError(label + " must be between 0 and 1")
    return round(float(value), 3)


def expression_for(segment_id: str | None, expressions: dict[str, Any]) -> dict[str, Any]:
    """Explicit editorial choice only; no guessed emotional response to news."""
    data = expressions.get(segment_id, {}) if segment_id else {}
    if not isinstance(data, dict):
        raise ContractError("expression entry must be an object")
    gesture = data.get("gesture", "still_point")
    if gesture not in GESTURES:
        raise ContractError("unknown gesture")
    return {
        "gesture": gesture,
        "amplitude": clamp_unit(data.get("amplitude"), "amplitude", 0.35),
        "tempo": clamp_unit(data.get("tempo"), "tempo", 0.5),
        "restraint": clamp_unit(data.get("restraint"), "restraint", 0.75),
        "source": "reviewed_performance_cue" if data else "neutral_default",
    }


def project(
    packet: dict[str, Any],
    *,
    media_map: dict[str, Any] | None = None,
    expression_map: dict[str, Any] | None = None,
    now: datetime | None = None,
    ttl_seconds: int = 90,
) -> dict[str, Any]:
    """Whitelist the public projection; never copy opaque fields from cue.json."""
    if not isinstance(packet, dict) or packet.get("kind") != EXPECTED_INPUT:
        raise ContractError("expected broadcast_cue_surface")
    if packet.get("version") != "0.1.0":
        raise ContractError("unsupported broadcast.py cue version")
    state = packet.get("state")
    if state not in CUE_STATES:
        raise ContractError("unsupported cue state")
    if not isinstance(ttl_seconds, int) or not 10 <= ttl_seconds <= 3600:
        raise ContractError("ttl_seconds out of range")
    if not isinstance(media_map, (dict, type(None))) or not isinstance(expression_map, (dict, type(None))):
        raise ContractError("media and expression maps must be JSON objects")
    cue = packet.get("cue")
    now = now or utc_now()
    segment_id = None
    program = None
    video = None
    poster = None
    if state in ACTIVE_STATES:
        if not isinstance(cue, dict) or cue.get("state") != state:
            raise ContractError("cue state and surface state disagree")
        if state == "presenting" and (not isinstance(cue.get("started_at"), str) or not cue["started_at"]):
            raise ContractError("presenting without renderer_started acknowledgement")
        segment = cue.get("segment")
        if not isinstance(segment, dict):
            raise ContractError("cue missing segment")
        segment_id = safe_label(segment.get("segment_id"), 120)
        item = (media_map or {}).get(segment_id, {})
        if not isinstance(item, dict):
            raise ContractError("media item must be an object")
        # Media is curated by Topgro; the manifest NEVER self-approves a clip.
        if item.get("approved") is True:
            video = safe_media_path(item.get("video"))
            poster = safe_media_path(item.get("poster"))
        program = {
            "segment_id": segment_id,
            "kind": safe_label(segment.get("kind"), 24),
            "title": safe_label(segment.get("title")),
            "stance": safe_label(segment.get("stance"), 24),
            "sigma": clamp_unit(segment.get("sigma"), "sigma", 1.0),
            "video_available": bool(video),
        }
    elif cue is not None:
        # No retained active cue is allowed in standby/emergency projection.
        raise ContractError("inactive surface still contains a cue")
    return {
        "schema": SCHEMA,
        "identity": "vitra",
        "surface": "news.vitra.ams",
        "generated_at": zulu(now),
        "stale_after": zulu(now + timedelta(seconds=ttl_seconds)),
        "state": state,
        "state_verified_by": (
            "renderer_started_ack" if state == "presenting"
            else "scheduler_intent" if state == "cue_pending"
            else "local_broadcast_state"
        ),
        "program": program,
        "face": expression_for(segment_id, expression_map or {}),
        "media": {"video": video, "poster": poster, "visibility": "ams_only"},
        "distribution": {"backbeat": "separately_reviewed_text_images_only"},
        "limitations": ["not proof of viewer delivery", "not an authentication credential"],
    }


def write_public_json(path: Path, payload: dict[str, Any]) -> None:
    """Atomic replace; output file is intentionally browser-readable on VPN."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".broadcast-state-", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(tmp, 0o644)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def json_object(path: Path) -> dict[str, Any]:
    obj = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise ContractError("expected top-level JSON object")
    return obj


def main() -> None:
    parser = argparse.ArgumentParser(description="Project private broadcast cues into VPN-only VNN state")
    parser.add_argument("--cue", type=Path, default=Path("runtime/broadcast/cue.json"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--media-map", type=Path)
    parser.add_argument("--expression-map", type=Path)
    parser.add_argument("--ttl", type=int, default=90)
    args = parser.parse_args()
    media_map = json_object(args.media_map) if args.media_map else {}
    expression_map = json_object(args.expression_map) if args.expression_map else {}
    output = project(json_object(args.cue), media_map=media_map,
                     expression_map=expression_map, ttl_seconds=args.ttl)
    write_public_json(args.output, output)
    print(f"published {output['schema']} state={output['state']} to {args.output}")


if __name__ == "__main__":
    main()
