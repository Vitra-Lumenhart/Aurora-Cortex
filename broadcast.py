#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Aurora Cortex | Broadcast Surface v0.1.0 (draft organ).

PURPOSE
    Topgro is the authoritative station for the daily VNN rundown, rotating
    prepared loops, the news feed, and the news.vitra.ams chat surface.
    Other Vitra clients may *voluntarily* contribute bounded reaction proposals.
    Nothing from a guest becomes broadcast authority or permanent memory.

BOUNDARIES
    gateway.sh          declares host, role, routes and resource limits
    genesis.py          orchestrates cognition; may prepare segment proposals
    ollama-voicebox.py  owns local model policy (and future TTS adapter)
    broadcast.py        owns playback selection, cue lifecycle, local receipts
    gate_of_eden.py     owns authoritative witnessing, not broadcast transport
    sqlibrarian.py      owns review/promotion to durable books, not this queue
    garden_of_chuzhoy   owns router attachment and .ams network mechanisms

LANES
    slow      today's approved daily edition -> approved evergreen loop
    short     approved expiring short loops/interjections/reactions, between segments
    station   opt-in derived-text proposal only; never raw device sensors

The control packet written to runtime/broadcast/cue.json is INTENT, NOT VIDEO.
No audio, camera capture, live chat, LLM inference, web feeds, publication,
peer authentication, OBS control, TTS or external network transport is included.
A renderer must acknowledge cues before status may indicate playback.

Run: python3 broadcast.py --help
Requires: Python 3.10+ standard library. No source-tree imports, by design.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sqlite3
import sys
import tempfile
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo


VERSION = "0.1.0"
UTC = timezone.utc
KINDS = {"daily", "evergreen", "short_loop", "interjection", "reaction"}
STANCES = {"fact", "commentary", "opinion", "identity", "fiction"}
SCENES = {"anchor", "story", "ident", "standby"}
MAX_SCRIPT_CHARS = 8000
MAX_SHORT_SECONDS = 90
MAX_OFFER_TTL_SECONDS = 600
ACK_TIMEOUT_SECONDS = 20
FINISH_GRACE_SECONDS = 30


def utcnow() -> datetime:
    return datetime.now(UTC)


def stamp(value: datetime) -> str:
    return value.astimezone(UTC).isoformat(timespec="seconds")


def parse_stamp(value: str) -> datetime:
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("Timestamp must include a timezone offset")
    return result.astimezone(UTC)


def bounded_text(value: Any, label: str, limit: int, *, empty: bool = False) -> str:
    if not isinstance(value, str) or (not empty and not value.strip()) or len(value) > limit:
        raise ValueError(f"{label} must be text, length 1..{limit}" if not empty else f"{label} must be <= {limit} characters")
    return value.strip()


def token(prefix: str) -> str:
    return f"{prefix}:{uuid.uuid4().hex}"


def strict_bool(value: Any) -> bool:
    return value is True


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        tmp.write_text(json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        tmp.chmod(0o600)
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


@dataclass(frozen=True)
class BroadcastDeclared:
    """Waygate-derived declarations; not an observed or verified inventory."""

    node_id: str = "topgro"
    role: str = "topgro"  # topgro | station
    runtime_dir: str = "runtime/broadcast"
    timezone_name: str = "America/New_York"
    public_name: str = "vitra.ams"
    chat_name: str = "news.vitra.ams"
    approval_policy: str = "reviewed_only"

    def __post_init__(self) -> None:
        if self.role not in {"topgro", "station"}:
            raise ValueError("role must be topgro or station")
        if self.approval_policy != "reviewed_only":
            raise ValueError("v0.1 implements reviewed_only publication exclusively")
        bounded_text(self.node_id, "node_id", 100)
        ZoneInfo(self.timezone_name)

    @classmethod
    def from_env(cls, *, role: str | None = None, runtime: str | None = None) -> "BroadcastDeclared":
        return cls(
            node_id=os.getenv("VITRA_NODE_ID", "topgro"),
            role=role or os.getenv("VITRA_BROADCAST_ROLE", "topgro"),
            runtime_dir=runtime or os.getenv("VITRA_BROADCAST_RUNTIME", "runtime/broadcast"),
            timezone_name=os.getenv("VITRA_BROADCAST_TIMEZONE", "America/New_York"),
            public_name=os.getenv("VITRA_PUBLIC_NAME", "vitra.ams"),
            chat_name=os.getenv("VITRA_NEWS_CHAT_NAME", "news.vitra.ams"),
        )


def current_edition(now: datetime, decl: BroadcastDeclared) -> str:
    return now.astimezone(ZoneInfo(decl.timezone_name)).date().isoformat()


@dataclass(frozen=True)
class Segment:
    """A script and performance proposal; not an executable instruction."""

    segment_id: str
    kind: str
    title: str
    script: str
    stance: str
    sigma: float
    source_refs: tuple[str, ...]
    edition: str | None
    expires_at: str | None
    estimated_seconds: int
    max_plays: int = 1
    priority: int = 0
    order_index: int = 0
    scene: str = "anchor"
    origin_node: str = "topgro"

    @classmethod
    def from_dict(cls, raw: dict[str, Any], *, origin_node: str) -> "Segment":
        if not isinstance(raw, dict):
            raise ValueError("segment must be an object")
        kind = raw.get("kind")
        if kind not in KINDS:
            raise ValueError(f"kind must be one of {sorted(KINDS)}")
        title = bounded_text(raw.get("title"), "title", 200)
        script = bounded_text(raw.get("script"), "script", MAX_SCRIPT_CHARS)
        stance = raw.get("stance", "commentary")
        if stance not in STANCES:
            raise ValueError("invalid stance")
        sigma = raw.get("sigma", 1.0)
        if isinstance(sigma, bool) or not isinstance(sigma, (float, int)) or not math.isfinite(sigma) or not 0 <= sigma <= 1:
            raise ValueError("sigma must be finite between 0 and 1")
        sources = raw.get("source_refs", [])
        if not isinstance(sources, list) or len(sources) > 12:
            raise ValueError("source_refs must be a list of at most 12 items")
        for src in sources:
            bounded_text(src, "source reference", 500)
        # Nonempty sourced-news references must be human-legible and reviewable.
        if stance == "fact" and not sources:
            raise ValueError("factual reporting requires source_refs")
        edition = raw.get("edition")
        if kind == "daily":
            if not isinstance(edition, str):
                raise ValueError("daily segments require YYYY-MM-DD edition")
            datetime.strptime(edition, "%Y-%m-%d")
        elif edition is not None:
            raise ValueError("only daily segments have an edition")
        expires = raw.get("expires_at")
        if kind in {"reaction", "interjection", "short_loop"}:
            if not isinstance(expires, str):
                raise ValueError("short segments require expires_at")
            parse_stamp(expires)
        elif expires is not None:
            raise ValueError("slow-loop segments must not expire by timestamp")
        seconds = raw.get("estimated_seconds", max(5, min(300, round(len(script.split()) / 2.2))))
        if isinstance(seconds, bool) or not isinstance(seconds, int) or not 1 <= seconds <= 3600:
            raise ValueError("estimated_seconds must be an integer between 1 and 3600")
        if kind in {"reaction", "interjection", "short_loop"} and seconds > MAX_SHORT_SECONDS:
            raise ValueError("short segments must be <= 90 seconds")
        max_plays = raw.get("max_plays", 3 if kind == "short_loop" else 1)
        if isinstance(max_plays, bool) or not isinstance(max_plays, int):
            raise ValueError("max_plays must be an integer")
        if kind == "short_loop":
            if not 2 <= max_plays <= 6 or seconds * max_plays > 300:
                raise ValueError("short loops require 2..6 plays and <= 5 total minutes")
        elif max_plays != 1:
            raise ValueError("only short_loop may repeat in the short lane")
        priority = raw.get("priority", 0)
        order_index = raw.get("order_index", 0)
        if any(isinstance(v, bool) or not isinstance(v, int) or abs(v) > 10000 for v in (priority, order_index)):
            raise ValueError("priority and order_index must be bounded integers")
        scene = raw.get("scene", "anchor")
        if scene not in SCENES:
            raise ValueError("invalid scene")
        return cls(
            segment_id=token("seg"), kind=kind, title=title, script=script,
            stance=stance, sigma=float(sigma), source_refs=tuple(sources),
            edition=edition, expires_at=expires, estimated_seconds=seconds, max_plays=max_plays,
            priority=priority, order_index=order_index, scene=scene,
            origin_node=bounded_text(origin_node, "origin_node", 100),
        )


class Broadcast:
    """Single-writer Topgro control organ. Not a media renderer or web API."""

    def __init__(self, decl: BroadcastDeclared):
        if decl.role != "topgro":
            raise PermissionError("station nodes may offer proposals but never own Topgro's rundown")
        self.decl = decl
        self.root = Path(decl.runtime_dir)
        self.root.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.root / "schedule.sqlite3", timeout=10)
        (self.root / "schedule.sqlite3").chmod(0o600)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA busy_timeout=10000")
        self.db.execute("PRAGMA journal_mode=WAL")
        self._schema()

    def close(self) -> None:
        self.db.close()

    def _schema(self) -> None:
        with self.db:
            self.db.execute("""CREATE TABLE IF NOT EXISTS segments (
                id TEXT PRIMARY KEY, kind TEXT NOT NULL, edition TEXT,
                approved INTEGER NOT NULL DEFAULT 0, consumed INTEGER NOT NULL DEFAULT 0,
                priority INTEGER NOT NULL, order_index INTEGER NOT NULL,
                expires_at TEXT, payload TEXT NOT NULL, submitted_at TEXT NOT NULL
            )""")
            self.db.execute("""CREATE TABLE IF NOT EXISTS switches (
                key TEXT PRIMARY KEY, value TEXT NOT NULL
            )""")
            for key, value in (
                ("emergency", False), ("cue", None),
                ("last_daily", None), ("last_evergreen", None)
            ):
                self.db.execute("INSERT OR IGNORE INTO switches(key,value) VALUES (?,?)", (key, json.dumps(value)))

    def _get(self, key: str) -> Any:
        row = self.db.execute("SELECT value FROM switches WHERE key=?", (key,)).fetchone()
        return json.loads(row["value"])

    def _set(self, key: str, value: Any) -> None:
        self.db.execute("UPDATE switches SET value=? WHERE key=?", (json.dumps(value), key))

    def _receipt(self, event: str, *, observed: dict[str, Any], unknown: list[str] | None = None) -> None:
        # Local forensics, NOT a canonical Eden WitnessPacket or ROM promotion.
        receipt = {
            "kind": "broadcast_local_receipt", "version": VERSION,
            "at": stamp(utcnow()), "node": self.decl.node_id,
            "event": event, "declared": {"role": self.decl.role},
            "observed": observed, "unknown": unknown or [],
            "does_not_prove": ["broadcast delivery", "source truth", "personhood", "permission beyond this local action"],
        }
        with (self.root / "forensics.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(receipt, ensure_ascii=False, sort_keys=True) + "\n")

    def submit(self, raw: dict[str, Any], *, origin_node: str | None = None) -> str:
        """Always stores a DRAFT. Caller-supplied approved/ID fields are ignored."""
        seg = Segment.from_dict(raw, origin_node=origin_node or self.decl.node_id)
        with self.db:
            self.db.execute(
                """INSERT INTO segments(id,kind,edition,priority,order_index,expires_at,payload,submitted_at)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (seg.segment_id, seg.kind, seg.edition, seg.priority,
                 seg.order_index, seg.expires_at, json.dumps(asdict(seg)), stamp(utcnow())),
            )
        self._receipt("draft_submitted", observed={"segment_id": seg.segment_id, "kind": seg.kind})
        return seg.segment_id

    def review(self, segment_id: str, *, approve: bool, reviewer: str) -> None:
        reviewer = bounded_text(reviewer, "reviewer", 100)
        row = self.db.execute("SELECT payload FROM segments WHERE id=?", (segment_id,)).fetchone()
        if row is None:
            raise KeyError(f"unknown segment: {segment_id}")
        seg = json.loads(row["payload"])
        if approve and seg["expires_at"] is not None and parse_stamp(seg["expires_at"]) <= utcnow():
            raise ValueError("cannot approve expired content")
        with self.db:
            self.db.execute("UPDATE segments SET approved=? WHERE id=?", (1 if approve else -1, segment_id))
        self._receipt("review", observed={"segment_id": segment_id, "approved": approve, "reviewer": reviewer})
        # Withdraw an already prepared or presenting cue when approval is revoked.
        cue = self._get("cue")
        if not approve and cue and cue["segment"]["segment_id"] == segment_id:
            self._force_standby("approval_revoked")

    def _select_loop(self, kind: str, *, edition: str | None = None) -> dict[str, Any] | None:
        sql = "SELECT payload FROM segments WHERE approved=1 AND kind=?"
        params: list[Any] = [kind]
        if kind == "daily":
            sql += " AND edition=?"
            params.append(edition)
        sql += " ORDER BY order_index ASC, submitted_at ASC, id ASC"
        rows = self.db.execute(sql, params).fetchall()
        if not rows:
            return None
        segments = [json.loads(row["payload"]) for row in rows]
        previous = self._get("last_daily" if kind == "daily" else "last_evergreen")
        ids = [seg["segment_id"] for seg in segments]
        index = (ids.index(previous) + 1) % len(ids) if previous in ids else 0
        return segments[index]

    def _select(self, now: datetime) -> dict[str, Any] | None:
        # Short segments never interrupt speaking. They take priority at the next boundary.
        short = self.db.execute("""SELECT payload,consumed FROM segments
            WHERE approved=1 AND kind IN ('reaction','interjection','short_loop')
            ORDER BY priority DESC, submitted_at ASC, id ASC""").fetchall()
        for row in short:
            seg = json.loads(row["payload"])
            if row["consumed"] < seg["max_plays"] and parse_stamp(seg["expires_at"]) > now:
                return seg
        return self._select_loop("daily", edition=current_edition(now, self.decl)) or self._select_loop("evergreen")

    def _publish(self, cue: dict[str, Any] | None, *, state: str) -> None:
        # This is a local renderer interface. It is NOT a public API or a stream.
        atomic_json(self.root / "cue.json", {
            "kind": "broadcast_cue_surface", "version": VERSION, "state": state,
            "cue": cue, "observed_at": stamp(utcnow()),
            "public_name": self.decl.public_name, "chat_name": self.decl.chat_name,
        })

    def tick(self, *, now: datetime | None = None) -> dict[str, Any]:
        now = (now or utcnow()).astimezone(UTC)
        if self._get("emergency"):
            self._publish(None, state="emergency")
            return {"state": "emergency", "cue": None}
        cue = self._get("cue")
        if cue:
            begun = parse_stamp(cue["created_at"])
            if cue["state"] == "cue_pending" and (now - begun).total_seconds() > ACK_TIMEOUT_SECONDS:
                self._force_standby("unacknowledged_cue")
            elif cue["state"] == "presenting":
                started = parse_stamp(cue["started_at"])
                if (now - started).total_seconds() > cue["segment"]["estimated_seconds"] + FINISH_GRACE_SECONDS:
                    self._force_standby("render_timeout")
            else:
                return {"state": cue["state"], "cue": cue}
            cue = self._get("cue")
        if cue is None:
            seg = self._select(now)
            if seg is None:
                self._publish(None, state="standby")
                return {"state": "standby", "cue": None}
            cue = {
                "cue_id": token("cue"), "state": "cue_pending",
                "created_at": stamp(now), "started_at": None,
                "segment": seg,
                "render_contract": {
                    "voicebox": "speech_requested_not_yet_rendered",
                    "sprite": "expression_timeline_adapter_required",
                    "scene": seg["scene"],
                    "captions": "renderer_must_generate",
                    "transmission": "adapter_must_acknowledge",
                },
            }
            with self.db:
                self._set("cue", cue)
            self._receipt("cue_prepared", observed={"cue_id": cue["cue_id"], "segment_id": seg["segment_id"]},
                          unknown=["renderer ready", "speech duration", "audience reception"])
            self._publish(cue, state="cue_pending")
            return {"state": "cue_pending", "cue": cue}
        self._publish(None, state="standby")
        return {"state": "standby", "cue": None}

    def renderer_started(self, cue_id: str, *, now: datetime | None = None) -> dict[str, Any]:
        cue = self._get("cue")
        if self._get("emergency") or cue is None or cue["state"] != "cue_pending" or cue["cue_id"] != cue_id:
            raise ValueError("cue not pending or broadcast in emergency")
        now = (now or utcnow()).astimezone(UTC)
        if (now - parse_stamp(cue["created_at"])).total_seconds() > ACK_TIMEOUT_SECONDS:
            raise ValueError("cue acknowledgment arrived too late")
        seg = cue["segment"]
        approval = self.db.execute("SELECT approved FROM segments WHERE id=?", (seg["segment_id"],)).fetchone()
        if approval is None or approval["approved"] != 1:
            self._force_standby("approval_missing_before_start")
            raise PermissionError("segment approval missing or revoked")
        if seg["expires_at"] and parse_stamp(seg["expires_at"]) <= now:
            self._force_standby("expired_before_start")
            raise ValueError("short segment expired before rendering")
        cue["state"] = "presenting"
        cue["started_at"] = stamp(now)
        with self.db:
            self._set("cue", cue)
        self._publish(cue, state="presenting")
        self._receipt("renderer_ack_started", observed={"cue_id": cue_id, "segment_id": seg["segment_id"]},
                      unknown=["remote stream received by viewers"])
        return cue

    def renderer_finished(self, cue_id: str) -> None:
        cue = self._get("cue")
        if cue is None or cue["cue_id"] != cue_id or cue["state"] != "presenting":
            raise ValueError("no matching active cue")
        seg = cue["segment"]
        with self.db:
            if seg["kind"] in {"reaction", "interjection", "short_loop"}:
                self.db.execute("UPDATE segments SET consumed=consumed+1 WHERE id=?", (seg["segment_id"],))
            if seg["kind"] in {"daily", "evergreen"}:
                self._set("last_daily" if seg["kind"] == "daily" else "last_evergreen", seg["segment_id"])
            self._set("cue", None)
        self._receipt("renderer_ack_finished", observed={"cue_id": cue_id, "segment_id": seg["segment_id"]})
        self._publish(None, state="standby")

    def _force_standby(self, reason: str) -> None:
        cue = self._get("cue")
        with self.db:
            self._set("cue", None)
        self._receipt("standby_fallback", observed={"reason": reason, "abandoned_cue": cue["cue_id"] if cue else None})
        self._publish(None, state="standby")

    def emergency(self, enabled: bool, *, reviewer: str) -> None:
        bounded_text(reviewer, "reviewer", 100)
        with self.db:
            self._set("emergency", enabled)
            self._set("cue", None)
        self._receipt("emergency_switch", observed={"enabled": enabled, "operator": reviewer})
        self._publish(None, state="emergency" if enabled else "standby")

    def status(self) -> dict[str, Any]:
        cue = self._get("cue")
        counts = self.db.execute("SELECT kind,approved,COUNT(*) AS n FROM segments GROUP BY kind,approved").fetchall()
        return {
            "version": VERSION, "node": self.decl.node_id, "role": self.decl.role,
            "edition_today": current_edition(utcnow(), self.decl),
            "state": "emergency" if self._get("emergency") else (cue["state"] if cue else "standby"),
            "cue_id": cue["cue_id"] if cue else None,
            "segment_id": cue["segment"]["segment_id"] if cue else None,
            "queue_counts": [{"kind": r["kind"], "approved": r["approved"], "count": r["n"]} for r in counts],
            "media_transport": "not_implemented", "chatroom": "external_adapter_required",
            "news_feed": "external_adapter_required", "peer_transport": "external_adapter_required",
        }

    def ingest_offer(self, raw: dict[str, Any]) -> str:
        """Manual/operator-side import. Transport MUST independently authenticate peer.

        Untrusted client fields never become authority; no raw I/O accepted.
        """
        if not isinstance(raw, dict) or raw.get("kind") != "reaction_offer":
            raise ValueError("expected reaction_offer packet")
        if raw.get("scope") != "derived_text_only" or not strict_bool(raw.get("explicit_consent")):
            raise PermissionError("station offers require explicit text-only consent")
        observed = raw.get("observed_from")
        if observed not in {"camera_derived", "microphone_derived", "manual_text", "screen_derived", "none"}:
            raise ValueError("unsupported observation provenance")
        if any(field in raw for field in ("raw_audio", "raw_video", "image_bytes", "transcript", "device_id", "user_id")):
            raise ValueError("raw sensing, transcripts and user identifiers are forbidden in offer packets")
        expiration = parse_stamp(raw.get("expires_at", ""))
        seconds_left = (expiration - utcnow()).total_seconds()
        if not 0 < seconds_left <= MAX_OFFER_TTL_SECONDS:
            raise ValueError("offer must expire within 10 minutes")
        node = bounded_text(raw.get("node_claim"), "node_claim", 100)
        # The claim is untrusted provenance, NOT attested identity.
        segment = {
            "kind": "reaction", "title": bounded_text(raw.get("title"), "title", 200),
            "script": bounded_text(raw.get("proposed_script"), "proposed_script", 1200),
            "source_refs": raw.get("source_refs", []), "stance": raw.get("stance", "commentary"),
            "sigma": raw.get("sigma", 1.0), "expires_at": stamp(expiration),
            "estimated_seconds": raw.get("estimated_seconds", 25),
            "scene": "anchor", "priority": 50,
        }
        sid = self.submit(segment, origin_node=node)
        self._receipt("peer_offer_imported_unverified", observed={"segment_id": sid, "claimed_node": node, "observation_type": observed},
                      unknown=["peer authentication", "sensor measurement", "source truth"])
        return sid


def create_station_offer(raw: dict[str, Any], *, node_id: str) -> dict[str, Any]:
    """Opt-in local product for an external authenticated transport to carry.

    Does not capture sensors or infer personal identity. Browser/mobile clients
    will need a separate per-platform opt-in implementation; gateway.sh is not
    portable to ordinary phones or retail consoles.
    """
    if not strict_bool(raw.get("explicit_consent")):
        raise PermissionError("local sensor-derived contribution must be opt-in")
    observed = raw.get("observed_from", "none")
    if observed not in {"camera_derived", "microphone_derived", "manual_text", "screen_derived", "none"}:
        raise ValueError("unsupported observation provenance")
    if any(field in raw for field in ("raw_audio", "raw_video", "image_bytes", "transcript", "device_id", "user_id")):
        raise ValueError("raw sensor content and personal identifiers are not permitted")
    title = bounded_text(raw.get("title"), "title", 200)
    script = bounded_text(raw.get("proposed_script"), "proposed_script", 1200)
    seconds = raw.get("estimated_seconds", 25)
    if isinstance(seconds, bool) or not isinstance(seconds, int) or not 1 <= seconds <= MAX_SHORT_SECONDS:
        raise ValueError("offer must be at most 90 seconds")
    ttl = raw.get("ttl_seconds", 120)
    if isinstance(ttl, bool) or not isinstance(ttl, int) or not 1 <= ttl <= MAX_OFFER_TTL_SECONDS:
        raise ValueError("ttl_seconds must be 1..600")
    stance, sigma = raw.get("stance", "commentary"), raw.get("sigma", 1.0)
    # Reuse canonical Segment validation without retaining the generated ID.
    expiration = stamp(utcnow() + timedelta(seconds=ttl))
    candidate = Segment.from_dict({
        "kind": "reaction", "title": title, "script": script, "stance": stance,
        "sigma": sigma, "expires_at": expiration, "source_refs": raw.get("source_refs", []),
        "estimated_seconds": seconds,
    }, origin_node=node_id)
    packet = {
        "kind": "reaction_offer", "version": VERSION,
        "offer_id": token("offer"), "node_claim": bounded_text(node_id, "node_id", 100),
        "created_at": stamp(utcnow()), "expires_at": expiration,
        "explicit_consent": True, "scope": "derived_text_only", "observed_from": observed,
        "title": candidate.title, "proposed_script": candidate.script,
        "stance": candidate.stance, "sigma": candidate.sigma,
        "source_refs": list(candidate.source_refs),
        "estimated_seconds": seconds,
        "approval_status": "draft_only", "does_not_prove": ["identity", "sensor accuracy", "publication approval"],
    }
    packet["content_sha256"] = hashlib.sha256(script.encode("utf-8")).hexdigest()
    return packet


def read_object(path: str) -> dict[str, Any]:
    data = Path(path).read_bytes()
    if len(data) > 24_000:
        raise ValueError("input exceeds 24 KB")
    value = json.loads(data)
    if not isinstance(value, dict):
        raise ValueError("input must be a JSON object")
    return value


def demo() -> dict[str, Any]:
    """Deterministic shape smoke test; no real news, I/O, or broadcasting."""
    with tempfile.TemporaryDirectory(prefix="vitra-broadcast-") as temp:
        decl = BroadcastDeclared(runtime_dir=temp)
        b = Broadcast(decl)
        edition = current_edition(utcnow(), decl)
        ids = [
            b.submit({"kind": "daily", "edition": edition, "title": "Welcome",
                      "script": "Good evening. I'm Vitra Lumenhart, and this is a local rehearsal.",
                      "stance": "identity", "sigma": 0.0, "source_refs": [],
                      "estimated_seconds": 12, "order_index": 0}),
            b.submit({"kind": "daily", "edition": edition, "title": "Tomorrow's rundown",
                      "script": "Our next broadcast will distinguish reporting from commentary.",
                      "stance": "identity", "sigma": 0.0, "source_refs": [],
                      "estimated_seconds": 12, "order_index": 1}),
        ]
        for sid in ids:
            b.review(sid, approve=True, reviewer="demo-operator")
        playlist = []
        for _ in range(3):
            cue = b.tick()["cue"]
            playlist.append(cue["segment"]["title"])
            b.renderer_started(cue["cue_id"])
            b.renderer_finished(cue["cue_id"])
        offer = create_station_offer({
            "explicit_consent": True, "observed_from": "manual_text",
            "title": "A short observation", "proposed_script": "I noticed a noteworthy change in tone.",
        }, node_id="sample-guest")
        imported = b.ingest_offer(offer)
        # Imported peer draft MUST NOT preempt the next approved slow-loop cue.
        selected = b.tick()["cue"]["segment"]["kind"]
        b._force_standby("demo_cleanup")
        b.close()
        return {"demo": "passed", "playlist": playlist, "imported_peer_status": "draft_only",
                "peer_segment_id": imported, "next_kind_without_approval": selected,
                "actual_audio_or_video": False}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Vitra Broadcast Surface: Topgro loops and bounded station proposals")
    parser.add_argument("--runtime", help="override runtime/broadcast directory")
    parser.add_argument("--role", choices=["topgro", "station"], help="override declared node role")
    parser.add_argument("--node", help="override VITRA_NODE_ID")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init", help="create Topgro local schedule and receipt store")
    sub.add_parser("status", help="report local switchboard and queue state")
    sub.add_parser("tick", help="prepare next cue, or leave active cue unchanged")
    sub.add_parser("demo", help="run isolated rehearsal, no live transmission")
    p = sub.add_parser("submit", help="submit one JSON daily/evergreen/short draft")
    p.add_argument("json_file")
    for command in ("approve", "reject"):
        p = sub.add_parser(command, help=f"{command} one queued draft (local operator)")
        p.add_argument("segment_id")
        p.add_argument("--reviewer", required=True)
    for command in ("start", "finish"):
        p = sub.add_parser(command, help=f"renderer ACK: {command} cue")
        p.add_argument("cue_id")
    p = sub.add_parser("emergency", help="locally disable/reenable program selection")
    p.add_argument("state", choices=["on", "off"])
    p.add_argument("--reviewer", required=True)
    p = sub.add_parser("offer", help="make a LOCAL opt-in proposal packet; prints JSON")
    p.add_argument("json_file")
    p = sub.add_parser("ingest-offer", help="operator import of offer from an upstream authenticated boundary; remains DRAFT")
    p.add_argument("json_file")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "demo":
        print(json.dumps(demo(), indent=2))
        return 0
    decl = BroadcastDeclared.from_env(role=args.role, runtime=args.runtime)
    if args.node:
        decl = BroadcastDeclared(**{**asdict(decl), "node_id": args.node})
    if args.command == "offer":
        print(json.dumps(create_station_offer(read_object(args.json_file), node_id=decl.node_id), indent=2))
        return 0
    if decl.role == "station":
        raise PermissionError("a guest station can only use 'offer'; Topgro alone schedules and reviews")
    b = Broadcast(decl)
    try:
        command = args.command
        if command == "init":
            result = {"initialized": True, "declared": asdict(decl), "status": b.status()}
        elif command == "status":
            result = b.status()
        elif command == "tick":
            result = b.tick()
        elif command == "submit":
            result = {"draft_segment_id": b.submit(read_object(args.json_file))}
        elif command in {"approve", "reject"}:
            b.review(args.segment_id, approve=(command == "approve"), reviewer=args.reviewer)
            result = {"reviewed_segment_id": args.segment_id, "approved": command == "approve"}
        elif command == "start":
            result = {"acknowledged": b.renderer_started(args.cue_id)["cue_id"]}
        elif command == "finish":
            b.renderer_finished(args.cue_id)
            result = {"finished": args.cue_id}
        elif command == "emergency":
            b.emergency(args.state == "on", reviewer=args.reviewer)
            result = {"emergency": args.state == "on"}
        elif command == "ingest-offer":
            result = {"draft_segment_id": b.ingest_offer(read_object(args.json_file)), "status": "unverified_draft"}
        else:
            raise ValueError(f"unhandled command {command}")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    finally:
        b.close()


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, PermissionError, KeyError, sqlite3.Error) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        sys.exit(2)