#!/usr/bin/env python3
"""
gate_of_eden.py  # ⟐→☼→⧁  # Aurora Cortex — Gate of Eden Organ (v2.6.0)

Consult the Sigma–Mirror Group Glyph.
Reflect → Refract → Return.

PURPOSE (v2.5)
- Genesis trusts no Gate; it only trusts what it can witness.
- Gate of Eden is a Genesis-side organ that ingests UNTRUSTED INPUT (Waygate env, hashes, paths, claims)

- 2.6 adds "Gate Closed / Gate Aware" posture:
    • Eden records whether an internet uplink appears reachable.
    • Eden records declared intent to open the gate (VITRA_EDEN_GATE_OPEN=1) but does NOT open it.
    • A secret key may be present (VITRA_EDEN_GATE_KEY); Eden records only presence + sig16, never the secret.
    • Actual transport (VPN/NAT/WAN forwarding) remains a router/network policy concern and is not enacted here.
  and emits a tamper-evident audit spine plus a canonical WitnessPacket dict for downstream organs.

KEY v2.5 HANDSHAKES (stabilization)
1) Canonical WitnessPacket (dict; identical everywhere)

    WitnessPacket = {
      "integrity": "pass|fail|unknown",
      "cold_read": "deterministic|nondeterministic|unknown",
      "declared": { ... },
      "observed": { ... },
      "unknown":  { ... },
    }

2) `AuditSnapshot.as_packet() -> dict`
   - Emits exactly the WitnessPacket shape.

3) Module-level helper: `start_of_run_audit(...) -> dict`
   - So genesis.py may call `gate_of_eden.start_of_run_audit()` as a module function.
   - It instantiates GateOfEden conservatively and returns the WitnessPacket dict.

DOCTRINE
- Declared ≠ Observed ≠ Unknown.
- Eden is a witness and curator, not an authority. It records; it does not "upgrade" claims.
- Append-only semantics: events + run audits + artifact witnesses, with best-effort hash chaining.

RUST / METAL FRIENDLINESS
- WitnessPacket is JSON-primitive only.
- Big payloads (giant tesseracts) should move via metal; Eden only stores compact receipts:
  sha256, size, chunk-root, plus signature16 hints.

MIT-License friendly: standard library only.
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
import hashlib
import socket
import time
import datetime as _dt
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, List, Callable


# ─────────────────────────────────────────────────────────────────────────────
# Canonical tags (for user manual + self-indexing)
# ─────────────────────────────────────────────────────────────────────────────
HASHTAGS_CORE = [
    "#AuroraCortex",
    "#GardenOfEdenGate",
    "#WaygateMembrane",
    "#gate_of_eden",
    "#declared",
    "#observed",
    "#unknown",
    "#forensics",
    "#append_only",
    "#hash_chain",
    "#sqlite_surface",
]

# Event kinds canonized by upstream labs (stable spelling)
EDEN_EVENT_KINDS = {
    # membrane audit spine
    "run_begin",
    "membrane_declared",
    "membrane_observed",
    "audit_delta",
    # path/log safety
    "path_escape_refused",
    "log_poison_attempt",
    "log_sanitized",
    # artifact witnessing
    "artifact_hash_observed",
    "hash_mismatch_suspected",
    "replay_suspected",
    # tesseract layer hooks (future)
    "tesspack_verified",
    "tesspack_verify_failed",
    "tesspack_coldread_pass",
    "tesspack_coldread_fail",
    # garden hooks (optional)
    "garden_witness_bundle",
    "garden_training",
    "garden_training_bundle",
}


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────
def utc_now_iso() -> str:
    return _dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def safe_json(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, default=str)


def sha256_bytes(b: bytes) -> str:
    h = hashlib.sha256()
    h.update(b)
    return h.hexdigest()



def _sig16_secret_hint(secret: str) -> str:
    """Return a stable sig16 hint of a secret WITHOUT recording the secret itself."""
    if not secret:
        return ""
    return hashlib.sha256(secret.encode("utf-8", errors="replace")).hexdigest()[:16]


def _probe_internet(timeout_s: float = 1.25) -> Dict[str, Any]:
    """Best-effort internet reachability probe (awareness only).

    This does NOT "open the gate" or configure routing; it only observes.
    """
    ts = utc_now()
    out: Dict[str, Any] = {"ts": ts, "reachable": False, "method": "none", "detail": ""}
    # DNS resolution probe
    try:
        socket.setdefaulttimeout(timeout_s)
        # using a stable domain with long history
        socket.getaddrinfo("example.com", 80)
        out.update({"reachable": True, "method": "dns", "detail": "resolved example.com"})
        return out
    except Exception as e:
        out["detail"] = f"dns_fail:{type(e).__name__}"
    # TCP connect probe (may be blocked by policy)
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout_s)
        s.connect(("1.1.1.1", 443))
        s.close()
        out.update({"reachable": True, "method": "tcp", "detail": "connect 1.1.1.1:443"})
        return out
    except Exception as e:
        out["detail"] = f"tcp_fail:{type(e).__name__}"
    return out


def _read_proc_route() -> Dict[str, Any]:
    """Observe local kernel route table if available (Linux /proc)."""
    ts = utc_now()
    p = Path("/proc/net/route")
    if not p.exists():
        return {"ts": ts, "available": False}
    try:
        lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
        head = lines[:32]
        return {"ts": ts, "available": True, "head": head}
    except Exception as e:
        return {"ts": ts, "available": True, "error": f"{type(e).__name__}"}

def sha16_text(s: str) -> str:
    return sha256_bytes(s.encode("utf-8", errors="replace"))[:16]


def sha256_file(path: Path, *, chunk_bytes: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(chunk_bytes), b""):
            h.update(chunk)
    return h.hexdigest()


def chunk_root_sha256(b: bytes, *, chunk_bytes: int = 1024 * 1024) -> str:
    """
    Deterministic, offline-verifiable "chunk-root" digest:
      - sha256 each chunk
      - sha256(concat(all chunk digests as ASCII hex))
    """
    digests: List[str] = []
    for i in range(0, len(b), chunk_bytes):
        digests.append(sha256_bytes(b[i : i + chunk_bytes]))
    return sha256_bytes("".join(digests).encode("utf-8"))


def sanitize_log_text(s: str, *, max_len: int = 4000) -> Tuple[str, bool]:
    """
    Remove terminal control codes and cap size.
    Returns (sanitized, was_poison_attempt).
    """
    original = s
    s = re.sub(r"\x1B\[[0-?]*[ -/]*[@-~]", "", s)  # ANSI escapes
    s = "".join(ch for ch in s if (ch == "\n" or ch == "\t" or ord(ch) >= 32))
    was_poison = (s != original) or (len(s) > max_len)
    if len(s) > max_len:
        s = s[: max_len - 3] + "..."
    return s, was_poison


def resolve_realpath(p: Path) -> Path:
    return p.expanduser().resolve()


def is_path_within(child: Path, parent: Path) -> bool:
    try:
        child = resolve_realpath(child)
        parent = resolve_realpath(parent)
        child.relative_to(parent)
        return True
    except Exception:
        return False


def _is_json_primitive_tree(x: Any, *, depth: int = 0, max_depth: int = 24) -> bool:
    """
    Guardrail: WitnessPacket must remain JSON-primitive only.
    This is intentionally conservative.
    """
    if depth > max_depth:
        return False
    if x is None or isinstance(x, (bool, int, float, str)):
        return True
    if isinstance(x, list):
        return all(_is_json_primitive_tree(v, depth=depth + 1, max_depth=max_depth) for v in x)
    if isinstance(x, dict):
        return all(
            isinstance(k, str) and _is_json_primitive_tree(v, depth=depth + 1, max_depth=max_depth)
            for k, v in x.items()
        )
    return False


# ─────────────────────────────────────────────────────────────────────────────
# Data structures
# ─────────────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class EdenPolicy:
    """
    Conservative defaults. Genesis may pass explicit policy, but Eden must not infer authority from env.
    """
    max_env_kv: int = 500
    max_env_value_len: int = 2000
    max_artifact_bytes: int = 256 * 1024 * 1024  # 256MB demo cap
    chunk_bytes: int = 1024 * 1024               # 1MB chunks
    allow_roots: Tuple[Path, ...] = ()

    @staticmethod
    def from_env(project_root: Path, forensics_root: Path) -> "EdenPolicy":
        max_art_mb = int(os.environ.get("VITRA_EDEN_MAX_ART_MB", "256"))
        chunk_kb = int(os.environ.get("VITRA_EDEN_CHUNK_KB", "1024"))
        return EdenPolicy(
            max_artifact_bytes=max(1, max_art_mb) * 1024 * 1024,
            chunk_bytes=max(64, chunk_kb) * 1024,
            allow_roots=(project_root, forensics_root),
        )


@dataclass
class AuditSnapshot:
    ts_utc: str
    run_id: str
    mode: str
    declared: Dict[str, Any]
    observed: Dict[str, Any]
    unknowns: Dict[str, Any]
    delta_summary: Dict[str, Any]

    def to_row(self) -> Dict[str, Any]:
        return {
            "ts_utc": self.ts_utc,
            "run_id": self.run_id,
            "mode": self.mode,
            "declared_json": safe_json(self.declared),
            "observed_json": safe_json(self.observed),
            "unknowns_json": safe_json(self.unknowns),
            "delta_json": safe_json(self.delta_summary),
        }

    def as_packet(self) -> Dict[str, Any]:
        """
        v2.5 Canonical WitnessPacket (dict). Identical everywhere.

        Integrity rule (conservative):
          - fail    if Eden has explicit mismatches (delta_summary.mismatches not empty)
          - unknown if no mismatches but unknowns exist
          - pass    if no mismatches and no unknowns

        cold_read:
          - deterministic (this packet is generated deterministically from local observation)
        """
        mismatches = (self.delta_summary or {}).get("mismatches") or {}
        if mismatches:
            integrity = "fail"
        elif self.unknowns:
            integrity = "unknown"
        else:
            integrity = "pass"

        packet = {
            "integrity": integrity,
            "cold_read": "deterministic",
            "declared": self.declared or {},
            "observed": self.observed or {},
            "unknown": self.unknowns or {},
        }

        # Guarantee JSON-primitive only.
        if not _is_json_primitive_tree(packet):
            # Fall back to stringified payloads rather than emitting illegal structures.
            packet = {
                "integrity": "unknown",
                "cold_read": "unknown",
                "declared": {"_eden_stringified": safe_json(self.declared or {})},
                "observed": {"_eden_stringified": safe_json(self.observed or {})},
                "unknown": {"_eden_stringified": safe_json(self.unknowns or {})},
            }
        return packet


@dataclass
class ArtifactWitness:
    ts_utc: str
    run_id: str
    source_locator: str
    byte_length: int
    artifact_sha256: str
    chunks_root_sha256: str
    format_magic: str = "unknown"
    format_version: str = "unknown"
    compression_hint: str = "unknown"
    witness_status: str = "pass"  # pass | fail
    failure_code: str = ""

    def to_row(self) -> Dict[str, Any]:
        return {
            "ts_utc": self.ts_utc,
            "run_id": self.run_id,
            "source_locator": self.source_locator,
            "byte_length": self.byte_length,
            "artifact_sha256": self.artifact_sha256,
            "chunks_root_sha256": self.chunks_root_sha256,
            "format_magic": self.format_magic,
            "format_version": self.format_version,
            "compression_hint": self.compression_hint,
            "witness_status": self.witness_status,
            "failure_code": self.failure_code,
        }


# ─────────────────────────────────────────────────────────────────────────────
# SQLite Surface Memory (append-only semantics)
# ─────────────────────────────────────────────────────────────────────────────
class EdenSQLite:
    def __init__(self, db_path: Path):
        self.db_path = resolve_realpath(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.execute("PRAGMA journal_mode=WAL;")
        self.conn.execute("PRAGMA synchronous=NORMAL;")
        self._init_schema()

    def _init_schema(self) -> None:
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS run_audit (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts_utc TEXT NOT NULL,
                run_id TEXT NOT NULL,
                mode TEXT NOT NULL,
                declared_json TEXT NOT NULL,
                observed_json TEXT NOT NULL,
                unknowns_json TEXT NOT NULL,
                delta_json TEXT NOT NULL
            )
            """
        )
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS artifact_witness (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts_utc TEXT NOT NULL,
                run_id TEXT NOT NULL,
                source_locator TEXT NOT NULL,
                byte_length INTEGER NOT NULL,
                artifact_sha256 TEXT NOT NULL,
                chunks_root_sha256 TEXT NOT NULL,
                format_magic TEXT NOT NULL,
                format_version TEXT NOT NULL,
                compression_hint TEXT NOT NULL,
                witness_status TEXT NOT NULL,
                failure_code TEXT NOT NULL
            )
            """
        )
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS eden_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts_utc TEXT NOT NULL,
                run_id TEXT NOT NULL,
                kind TEXT NOT NULL,
                hashtags_json TEXT NOT NULL,
                payload_json TEXT NOT NULL
            )
            """
        )
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS lineage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts_utc TEXT NOT NULL,
                run_id TEXT NOT NULL,
                prev_hash TEXT,
                this_hash TEXT NOT NULL,
                kind TEXT NOT NULL
            )
            """
        )
        self.conn.commit()

    def append_run_audit(self, snap: AuditSnapshot) -> None:
        row = snap.to_row()
        self.conn.execute(
            """
            INSERT INTO run_audit (ts_utc, run_id, mode, declared_json, observed_json, unknowns_json, delta_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row["ts_utc"],
                row["run_id"],
                row["mode"],
                row["declared_json"],
                row["observed_json"],
                row["unknowns_json"],
                row["delta_json"],
            ),
        )
        self.conn.commit()

    def append_artifact_witness(self, w: ArtifactWitness) -> None:
        r = w.to_row()
        self.conn.execute(
            """
            INSERT INTO artifact_witness (
                ts_utc, run_id, source_locator, byte_length,
                artifact_sha256, chunks_root_sha256,
                format_magic, format_version, compression_hint,
                witness_status, failure_code
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                r["ts_utc"],
                r["run_id"],
                r["source_locator"],
                r["byte_length"],
                r["artifact_sha256"],
                r["chunks_root_sha256"],
                r["format_magic"],
                r["format_version"],
                r["compression_hint"],
                r["witness_status"],
                r["failure_code"],
            ),
        )
        self.conn.commit()

    def append_event(self, *, ts_utc: str, run_id: str, kind: str, hashtags: List[str], payload: Dict[str, Any]) -> None:
        self.conn.execute(
            """
            INSERT INTO eden_events (ts_utc, run_id, kind, hashtags_json, payload_json)
            VALUES (?, ?, ?, ?, ?)
            """,
            (ts_utc, run_id, kind, safe_json(hashtags), safe_json(payload)),
        )
        self.conn.commit()

    def append_lineage(self, *, ts_utc: str, run_id: str, kind: str, prev_hash: Optional[str], this_hash: str) -> None:
        self.conn.execute(
            """
            INSERT INTO lineage (ts_utc, run_id, prev_hash, this_hash, kind)
            VALUES (?, ?, ?, ?, ?)
            """,
            (ts_utc, run_id, prev_hash, this_hash, kind),
        )
        self.conn.commit()

    def latest_lineage_hash(self) -> Optional[str]:
        cur = self.conn.execute("SELECT this_hash FROM lineage ORDER BY id DESC LIMIT 1")
        row = cur.fetchone()
        return row[0] if row else None


# ─────────────────────────────────────────────────────────────────────────────
# Gate of Eden (organ)
# ─────────────────────────────────────────────────────────────────────────────
class GateOfEden:
    """
    Witness and curator. Not a transport; not a membrane; not an authority.
    """

    def __init__(
        self,
        *,
        run_id: str,
        mode: str,
        project_root: Path,
        forensics_root: Path,
        sqlite_path: Path,
        policy: Optional[EdenPolicy] = None,
        forensics_sink: Optional[Callable[..., Any]] = None,
    ):
        self.run_id = run_id
        self.mode = mode
        self.project_root = resolve_realpath(project_root)
        self.forensics_root = resolve_realpath(forensics_root)
        self.sqlite_path = resolve_realpath(sqlite_path)
        self.policy = policy or EdenPolicy.from_env(self.project_root, self.forensics_root)
        self.db = EdenSQLite(self.sqlite_path)
        self._forensics_sink = forensics_sink
        self._prev_hash = self.db.latest_lineage_hash()

    # ── Events ────────────────────────────────────────────────────────────────
    def emit(self, kind: str, payload: Dict[str, Any], hashtags: Optional[List[str]] = None) -> None:
        ts = utc_now_iso()
        tags = list(dict.fromkeys((hashtags or []) + HASHTAGS_CORE))
        if kind not in EDEN_EVENT_KINDS:
            tags.append("#noncanonical_kind")

        self.db.append_event(ts_utc=ts, run_id=self.run_id, kind=kind, hashtags=tags, payload=payload)

        if self._forensics_sink is not None:
            try:
                self._forensics_sink(kind, **payload)
            except Exception:
                pass

        # Hash-chain (best-effort, append-only)
        chain_material = safe_json({"ts": ts, "run_id": self.run_id, "kind": kind, "payload": payload}).encode("utf-8")
        this_hash = sha256_bytes(chain_material)
        self.db.append_lineage(ts_utc=ts, run_id=self.run_id, kind=kind, prev_hash=self._prev_hash, this_hash=this_hash)
        self._prev_hash = this_hash

    # ── Run audit ─────────────────────────────────────────────────────────────
    def start_of_run_audit(self, *, attachments: Optional[Dict[str, Any]] = None) -> AuditSnapshot:
        """
        attachments: optional observed-side additions (e.g., GardenOfChuzhoy.eden_attachment).
        Eden will treat these as Observed if they are JSON-primitive, otherwise Unknown.
        """
        ts = utc_now_iso()
        declared = self._collect_declared_env()
        observed, unknowns = self._collect_observed_facts(declared)

        # Attachments: observed-but-not-trusted, but still witnessable
        if attachments:
            if _is_json_primitive_tree(attachments):
                observed.setdefault("attachments", {})
                # avoid collisions: attachments live under one key
                observed["attachments"].update(attachments)
            else:
                unknowns["attachments"] = "non_json_primitive_attachment_refused"

        delta = self._compute_delta_summary(declared, observed, unknowns)

        snap = AuditSnapshot(
            ts_utc=ts,
            run_id=self.run_id,
            mode=self.mode,
            declared=declared,
            observed=observed,
            unknowns=unknowns,
            delta_summary=delta,
        )
        self.db.append_run_audit(snap)

        self.emit("run_begin", {"mode": self.mode, "ts": ts, "delta_summary": delta}, hashtags=["#run_begin"])
        self.emit("membrane_declared", {"declared": declared}, hashtags=["#declared"])
        self.emit("membrane_observed", {"observed": observed, "unknown": unknowns}, hashtags=["#observed", "#unknown"])
        self.emit("audit_delta", {"delta_summary": delta}, hashtags=["#audit_delta"])
        return snap

    def start_of_run_audit_packet(self, *, attachments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Convenience: returns canonical WitnessPacket dict.
        """
        return self.start_of_run_audit(attachments=attachments).as_packet()

    # ── Declared / Observed / Unknown ─────────────────────────────────────────
    def _collect_declared_env(self) -> Dict[str, Any]:
        env = dict(os.environ)
        keys = [k for k in env.keys() if k.startswith("VITRA_")] + ["PROJECT_ROOT", "USER", "USERNAME", "COMPUTERNAME"]
        out: Dict[str, Any] = {}
        for k in keys[: self.policy.max_env_kv]:
            v = env.get(k, "")
            if v is None:
                continue
            v = str(v)
            if len(v) > self.policy.max_env_value_len:
                v = v[: self.policy.max_env_value_len - 3] + "..."
            out[k] = v

        # Gate posture (declared intent only; never enacts transport)
        out["VITRA_EDEN_GATE_OPEN"] = os.environ.get("VITRA_EDEN_GATE_OPEN", "0")
        secret = os.environ.get("VITRA_EDEN_GATE_KEY", "")
        out["VITRA_EDEN_GATE_KEY_PRESENT"] = bool(secret)
        out["VITRA_EDEN_GATE_KEY_SIG16"] = _sig16_secret_hint(secret)

        return out

    def _collect_observed_facts(self, declared: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        observed: Dict[str, Any] = {}
        unknowns: Dict[str, Any] = {}

        observed["project_root_realpath"] = str(self.project_root)
        observed["forensics_root_realpath"] = str(self.forensics_root)
        observed["sqlite_realpath"] = str(self.sqlite_path)
        observed["eden_version"] = "2.6.0"

        observed["forensics_root_exists"] = self.forensics_root.exists()
        observed["forensics_root_writable"] = os.access(str(self.forensics_root), os.W_OK)

        # Declared target file (Waygate / gateway.sh typically sets these)
        target_py = declared.get("VITRA_TARGET_PY", "") or declared.get("VITRA_ENTRY_SCRIPT", "")
        if target_py:
            try:
                tp = resolve_realpath(Path(target_py))
                if not self._is_allowed_path(tp):
                    self.emit("path_escape_refused", {"path": str(tp), "reason": "target_py_outside_allowed_roots"}, hashtags=["#path_escape_refused"])
                    unknowns["target_py"] = "refused_path_escape"
                elif tp.is_file():
                    observed["target_py_realpath"] = str(tp)
                    observed["target_sha256_computed"] = sha256_file(tp)
                else:
                    unknowns["target_py"] = "not_a_file"
            except Exception as e:
                unknowns["target_py"] = f"error:{type(e).__name__}"

        # Gateway file (optional local path)
        gate_path = declared.get("VITRA_GATE_LOCAL_PATH", "")
        if gate_path:
            try:
                gp = resolve_realpath(Path(gate_path))
                if self._is_allowed_path(gp) and gp.is_file():
                    observed["gateway_sha256_observed"] = sha256_file(gp)
                    observed["gateway_path_realpath"] = str(gp)
                else:
                    unknowns["gateway_path"] = "unavailable_or_refused"
            except Exception:
                unknowns["gateway_path"] = "error"

        # Eden does not enforce CPU limits; it only records that it is not enforcing.
        observed["cpu_observation_limit"] = "no_enforcement; no native cross-platform observation"

        # Gate awareness: observe (do not open)
        try:
            observed["internet_probe"] = _probe_internet()
        except Exception as e:
            unknowns["internet_probe"] = f"error:{type(e).__name__}"
        try:
            observed["proc_route"] = _read_proc_route()
        except Exception as e:
            unknowns["proc_route"] = f"error:{type(e).__name__}"

        # Position relative to Garden: witness presence + hashes (no import, no execution)
        try:
            garden_py = self.project_root / "garden_of_chuzhoy.py"
            if garden_py.exists() and garden_py.is_file():
                observed["garden_of_chuzhoy_sha256"] = sha256_file(garden_py)
                observed["garden_of_chuzhoy_path"] = str(garden_py)
            else:
                unknowns["garden_of_chuzhoy"] = "missing"
        except Exception as e:
            unknowns["garden_of_chuzhoy"] = f"error:{type(e).__name__}"

        return observed, unknowns

    def _compute_delta_summary(self, declared: Dict[str, Any], observed: Dict[str, Any], unknowns: Dict[str, Any]) -> Dict[str, Any]:
        delta: Dict[str, Any] = {"mismatches": {}, "notes": []}

        decl_target = declared.get("VITRA_TARGET_SHA256", "")
        obs_target = observed.get("target_sha256_computed", "")
        if decl_target and obs_target and decl_target != obs_target:
            delta["mismatches"]["target_sha256"] = {"declared": decl_target, "observed": obs_target}
            self.emit(
                "hash_mismatch_suspected",
                {"what": "target_sha256", "declared": decl_target, "observed": obs_target},
                hashtags=["#provenance", "#hash_chain"],
            )

        decl_gate = declared.get("VITRA_GATEWAY_SHA256", "")
        obs_gate = observed.get("gateway_sha256_observed", "")
        if decl_gate and obs_gate and decl_gate != obs_gate:
            delta["mismatches"]["gateway_sha256"] = {"declared": decl_gate, "observed": obs_gate}
            self.emit(
                "hash_mismatch_suspected",
                {"what": "gateway_sha256", "declared": decl_gate, "observed": obs_gate},
                hashtags=["#provenance", "#hash_chain"],
            )

        if unknowns:
            delta["notes"].append("unknowns_present")

        net = (declared.get("VITRA_NET_CHANNEL") or "offline").lower()
        cloud = (declared.get("VITRA_CLOUD_CHANNEL") or "disabled").lower()
        peer = (declared.get("VITRA_PEER_CHANNEL") or "disabled").lower()
        delta["notes"].append(f"channels_declared: net={net} cloud={cloud} peer={peer}")
        return delta

    def _is_allowed_path(self, p: Path) -> bool:
        roots = self.policy.allow_roots or (self.project_root, self.forensics_root)
        rp = resolve_realpath(p)
        return any(is_path_within(rp, r) for r in roots)

    # ── Cold-read witnessing (tesseracts move elsewhere; Eden keeps receipts) ──
    def cold_read_witness_path(self, path: Path, *, locator_label: str = "") -> ArtifactWitness:
        ts = utc_now_iso()
        p = resolve_realpath(path)

        if not self._is_allowed_path(p):
            self.emit("path_escape_refused", {"path": str(p), "reason": "artifact_path_outside_allowed_roots"}, hashtags=["#path_escape_refused"])
            w = ArtifactWitness(
                ts_utc=ts,
                run_id=self.run_id,
                source_locator=f"{locator_label}{str(p)}",
                byte_length=0,
                artifact_sha256="",
                chunks_root_sha256="",
                witness_status="fail",
                failure_code="path_escape_refused",
            )
            self.db.append_artifact_witness(w)
            self.emit("tesspack_verify_failed", {"failure_code": w.failure_code, "source": str(p)}, hashtags=["#tesspack", "#integrity-fail"])
            return w

        if not p.is_file():
            w = ArtifactWitness(
                ts_utc=ts,
                run_id=self.run_id,
                source_locator=f"{locator_label}{str(p)}",
                byte_length=0,
                artifact_sha256="",
                chunks_root_sha256="",
                witness_status="fail",
                failure_code="not_a_file",
            )
            self.db.append_artifact_witness(w)
            self.emit("tesspack_verify_failed", {"failure_code": w.failure_code, "source": str(p)}, hashtags=["#tesspack", "#integrity-fail"])
            return w

        size = p.stat().st_size
        if size > self.policy.max_artifact_bytes:
            w = ArtifactWitness(
                ts_utc=ts,
                run_id=self.run_id,
                source_locator=f"{locator_label}{str(p)}",
                byte_length=size,
                artifact_sha256="",
                chunks_root_sha256="",
                witness_status="fail",
                failure_code="too_large_for_demo_witness",
            )
            self.db.append_artifact_witness(w)
            self.emit("tesspack_verify_failed", {"failure_code": w.failure_code, "source": str(p), "byte_length": size}, hashtags=["#tesspack", "#integrity-fail"])
            return w

        b = p.read_bytes()
        return self.cold_read_witness_bytes(b, source_locator=f"{locator_label}{str(p)}")

    def cold_read_witness_bytes(self, b: bytes, *, source_locator: str = "bytes:memory") -> ArtifactWitness:
        ts = utc_now_iso()

        if len(b) > self.policy.max_artifact_bytes:
            w = ArtifactWitness(
                ts_utc=ts,
                run_id=self.run_id,
                source_locator=source_locator,
                byte_length=len(b),
                artifact_sha256="",
                chunks_root_sha256="",
                witness_status="fail",
                failure_code="too_large_for_demo_witness",
            )
            self.db.append_artifact_witness(w)
            self.emit("tesspack_verify_failed", {"failure_code": w.failure_code, "source": source_locator, "byte_length": len(b)}, hashtags=["#tesspack", "#integrity-fail"])
            return w

        magic = "unknown"
        version = "unknown"
        if b[:4] == b"PAR1":
            magic = "parquet"
            version = "v1?"
        elif b[:2] == b"PK":
            magic = "zip"

        art_sha = sha256_bytes(b)
        root = chunk_root_sha256(b, chunk_bytes=self.policy.chunk_bytes)

        w = ArtifactWitness(
            ts_utc=ts,
            run_id=self.run_id,
            source_locator=source_locator,
            byte_length=len(b),
            artifact_sha256=art_sha,
            chunks_root_sha256=root,
            format_magic=magic,
            format_version=version,
            witness_status="pass",
        )
        self.db.append_artifact_witness(w)

        self.emit("artifact_hash_observed", {"artifact_sha256": art_sha, "byte_length": len(b), "chunks_root_sha256": root, "format_magic": magic}, hashtags=["#tamper-evident", "#chunk-root"])
        self.emit("tesspack_verified", {"artifact_sha256": art_sha, "byte_length": len(b), "format_magic": magic, "chunks_root_sha256": root}, hashtags=["#tesspack", "#cold-read", "#tamper-evident"])
        self.emit("tesspack_coldread_pass", {"artifact_sha256": art_sha, "source": source_locator}, hashtags=["#cold-read"])
        return w

    # ── Log hygiene ───────────────────────────────────────────────────────────
    def sanitize_and_record_log(self, raw_text: str, *, source: str = "unknown") -> str:
        clean, poison = sanitize_log_text(raw_text)
        if poison:
            self.emit("log_poison_attempt", {"source": source, "note": "sanitized_control_codes_or_oversize"}, hashtags=["#log_poison_attempt"])
        return clean


# ─────────────────────────────────────────────────────────────────────────────
# Module-level helper (v2.5 handshake): start_of_run_audit(...) -> dict
# ─────────────────────────────────────────────────────────────────────────────
def _default_paths() -> Tuple[Path, Path, Path]:
    project_root = Path(os.environ.get("PROJECT_ROOT") or Path(__file__).resolve().parent)
    forensics_root = Path(os.environ.get("VITRA_FORENSICS_ROOT") or (project_root / "forensics"))
    sqlite_path = Path(os.environ.get("VITRA_SQLITE_PATH") or (forensics_root / "eden_surface.sqlite"))
    return project_root.resolve(), forensics_root.resolve(), sqlite_path.resolve()


def start_of_run_audit(
    *,
    run_id: Optional[str] = None,
    mode: Optional[str] = None,
    project_root: Optional[Path] = None,
    forensics_root: Optional[Path] = None,
    sqlite_path: Optional[Path] = None,
    policy: Optional[EdenPolicy] = None,
    forensics_sink: Optional[Callable[..., Any]] = None,
    attachments: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    v2.5 stable seam for Genesis:
      eden_packet = gate_of_eden.start_of_run_audit(...)

    Returns: canonical WitnessPacket dict.

    attachments:
      Optional observed-side attachments (e.g., GardenOfChuzhoy.eden_attachment).
      These will be placed under observed.attachments if JSON-primitive; else recorded as Unknown.
    """
    pr, fr, sp = _default_paths()
    eden = GateOfEden(
        run_id=run_id or os.environ.get("VITRA_RUN_ID") or f"{_dt.datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_eden",
        mode=mode or os.environ.get("VITRA_MODE") or "eden",
        project_root=project_root or pr,
        forensics_root=forensics_root or fr,
        sqlite_path=sqlite_path or sp,
        policy=policy,
        forensics_sink=forensics_sink,
    )
    return eden.start_of_run_audit_packet(attachments=attachments)


# ─────────────────────────────────────────────────────────────────────────────
# CLI demo (unchanged spirit)
# ─────────────────────────────────────────────────────────────────────────────
def main(argv: List[str]) -> int:
    # Produce a WitnessPacket and report location.
    packet = start_of_run_audit()
    project_root, forensics_root, sqlite_path = _default_paths()
    run_id = os.environ.get("VITRA_RUN_ID") or "eden"

    print("⟐→☼→⧁  Gate of Eden v2.5 audit written to SQLite:")
    print(f"  sqlite: {sqlite_path}")
    print(f"  run_id: {run_id}")
    print(f"  packet: {safe_json(packet)}")

    if len(argv) >= 1:
        # If a file path is provided, cold-read witness it (receipt only).
        pr, fr, sp = _default_paths()
        eden = GateOfEden(
            run_id=run_id,
            mode=os.environ.get("VITRA_MODE") or "eden-cli",
            project_root=pr,
            forensics_root=fr,
            sqlite_path=sp,
        )
        p = Path(argv[0]).expanduser()
        w = eden.cold_read_witness_path(p, locator_label="path:")
        print("\n⧁ Cold-read witness:")
        print(f"  status: {w.witness_status}  code: {w.failure_code or 'ok'}")
        print(f"  sha256 : {w.artifact_sha256[:16]}…")
        print(f"  root  : {w.chunks_root_sha256[:16]}…")
        return 0 if w.witness_status == "pass" else 2

    return 0


if __name__ == "__main__":
    import sys
    raise SystemExit(main(sys.argv[1:]))

