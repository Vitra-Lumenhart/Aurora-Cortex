#!/usr/bin/env python3
# ============================================================================
# GENESIS.PY v2.8.1  —  The Courtyard Learns to Listen          2026-03-24
# ⟐→☼→⧁  Waygate → Genesis → Garden  (Membrane → Seed → Soil)
# Semantic Geometry Mapping / Aurora Cortex
# ----------------------------------------------------------------------------
# A Waygate is a protocol that allows independent intelligences to
# cooperate without sharing execution, memory, or authority.
# ----------------------------------------------------------------------------
# ## WHAT GENESIS IS
# Genesis is not a calculator.
# Genesis is a chassis.
#
# ## WHAT GENESIS DOES
# Genesis wakes the stack, witnesses the Waygate's declared reality, and
# conducts the organs through an explainable week-cycle.
#
# ## WHO DECIDES WHAT
# Waygate declares reality.
# Genesis witnesses and obeys.
# Garden listens and offers passage.
# Eden witnesses.
# Oracle reads without writing.
# Bookshelf remembers, if allowed.
#
# ## THE THREE CHESTS
# [IRON CHEST]  secrets  — Wi-Fi passwords, router access, key material.
#                         These stay local and should never be echoed into
#                         normal witness logs.
# [GLASS CHEST] receipts — who asked, when, why, and what bounded permission
#                         was granted. These may be witnessed.
# [CHAIN SEAL]  lineage  — optional Vitra↔Vitra trust attestation. This is
#                         never user surveillance and never message history.
#
# ## HOW TO READ THIS FILE
# First read  : titles do the heavy lifting.
# Second read : comment headers explain intent.
# Third read  : code shows the mechanism.
#
# If all three agree, the system has depth perception.
#
# ## BACKBONE RULE (lab-wide)
#   1) Imports   (dependencies)
#   2) Library   (organs / APIs / hooks)
#   3) Loop      (the __main__ demonstrative workflow)
#
# ## STORAGE DOCTRINE
# - Plain text / markdown / append-only witness files for human-readable
#   forensics.
# - SQLite for bounded weekly thought-cycle execution when available.
# - PostgreSQL for identity permanence and promoted continuity when available.
# - No JSON as the default Genesis artifact format.
#
# ## DOWNRES DOCTRINE
# - Prefer full shelf -> local shelf only -> paper/scribe mode -> witness-only.
# - Genesis should never fail merely because a shelf is missing.
#
# ## LOOP DOCTRINE
# Reflect → Refract → Return
# ============================================================================

from __future__ import annotations

# =====================
# IMPORTS (dependencies)
# =====================

import argparse
import dataclasses
import datetime as _dt
import os
import platform
import random
import textwrap
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple


# =====================
# LIBRARY (organs / APIs)
# =====================

@dataclass(frozen=True)
class WaygateDecl:
    """A minimal, human-readable witness of the Waygate-declared reality."""

    project_root: Path
    target_py: Path

    host_identity: str
    operator_identity: str
    identity_anchor: str
    continuity_anchor: str

    session_ttl_s: int

    net_channel: str
    cloud_channel: str
    peer_channel: str

    net_mode: str
    peer_mode: str

    node_id: str
    peers_conf: Path
    peer_bind: str
    peer_port: int

    keys_dir: Path
    trust_root: Path

    rom_dir: Path
    forensics_root: Path

    timestamp_utc: str


class Waygate:
    """Genesis-side mirror of gateway.sh.

    Purpose
    - Make it obvious to beginners how Genesis is attached to the Waygate.
    - Keep all chassis paths and policies sourced from environment variables.

    Design posture
    - The Waygate declares.
    - Genesis witnesses and obeys.
    """

    ENV_KEYS = {
        "PROJECT_ROOT": "(internal)",
        "VITRA_TARGET_PY": "(target python path)",
        "VITRA_ENTRY_SCRIPT": "(target python path; legacy alias)",
        "VITRA_HOST_IDENTITY": "hostname",
        "VITRA_OPERATOR_IDENTITY": "they",
        "VITRA_IDENTITY_ANCHOR": "initial_success_v1",
        "VITRA_CONTINUITY_ANCHOR": "waygate_entry",
        "VITRA_SESSION_TTL": "90",
        "VITRA_NET_CHANNEL": "offline",
        "VITRA_CLOUD_CHANNEL": "disabled",
        "VITRA_PEER_CHANNEL": "disabled",
        "VITRA_NET_MODE": "offline",
        "VITRA_PEER_MODE": "disabled",
        "VITRA_NODE_ID": "vitra-unnamed-node",
        "VITRA_PEERS_CONF": "peers.conf",
        "VITRA_PEER_BIND": "127.0.0.1",
        "VITRA_PEER_PORT": "24161",
        "VITRA_KEYS_DIR": "keys",
        "VITRA_TRUST_ROOT": "trust",
        "VITRA_ROM_DIR": "rom",
        "VITRA_FORENSICS_ROOT": "forensics",
    }

    @staticmethod
    def _now_utc_compact() -> str:
        return _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%d-%H%M%S")

    @staticmethod
    def _env(key: str) -> Optional[str]:
        v = os.environ.get(key)
        if v is None:
            return None
        v = str(v).strip()
        return v if v else None

    @classmethod
    def read_declared_reality(cls, *, argv_target: Optional[str] = None) -> Tuple[WaygateDecl, Dict[str, str]]:
        defaults_used: Dict[str, str] = {}

        env_project_root = cls._env("PROJECT_ROOT")
        if env_project_root:
            project_root = Path(env_project_root).expanduser().resolve()
        else:
            project_root = Path(__file__).resolve().parent
            defaults_used["PROJECT_ROOT"] = str(project_root)

        target_py: Optional[str]
        if argv_target:
            target_py = argv_target
        else:
            target_py = cls._env("VITRA_TARGET_PY") or cls._env("VITRA_ENTRY_SCRIPT")

        if not target_py:
            target_path = (project_root / "genesis.py").resolve()
            defaults_used["VITRA_TARGET_PY"] = str(target_path)
        else:
            target_path = Path(target_py).expanduser()
            if not target_path.is_absolute():
                target_path = (project_root / target_path).resolve()

        host_identity = cls._env("VITRA_HOST_IDENTITY") or platform.node() or "unknown-host"
        if not cls._env("VITRA_HOST_IDENTITY"):
            defaults_used["VITRA_HOST_IDENTITY"] = host_identity

        operator_identity = cls._env("VITRA_OPERATOR_IDENTITY") or "they"
        if not cls._env("VITRA_OPERATOR_IDENTITY"):
            defaults_used["VITRA_OPERATOR_IDENTITY"] = operator_identity

        identity_anchor = cls._env("VITRA_IDENTITY_ANCHOR") or "initial_success_v1"
        if not cls._env("VITRA_IDENTITY_ANCHOR"):
            defaults_used["VITRA_IDENTITY_ANCHOR"] = identity_anchor

        continuity_anchor = cls._env("VITRA_CONTINUITY_ANCHOR") or "waygate_entry"
        if not cls._env("VITRA_CONTINUITY_ANCHOR"):
            defaults_used["VITRA_CONTINUITY_ANCHOR"] = continuity_anchor

        session_ttl_s = int(cls._env("VITRA_SESSION_TTL") or "90")
        if not cls._env("VITRA_SESSION_TTL"):
            defaults_used["VITRA_SESSION_TTL"] = str(session_ttl_s)

        net_channel = cls._env("VITRA_NET_CHANNEL") or "offline"
        cloud_channel = cls._env("VITRA_CLOUD_CHANNEL") or "disabled"
        peer_channel = cls._env("VITRA_PEER_CHANNEL") or "disabled"

        net_mode = cls._env("VITRA_NET_MODE") or "offline"
        peer_mode = cls._env("VITRA_PEER_MODE") or "disabled"

        node_id = cls._env("VITRA_NODE_ID") or "vitra-unnamed-node"

        peers_conf = Path(cls._env("VITRA_PEERS_CONF") or (project_root / "peers.conf"))
        if not peers_conf.is_absolute():
            peers_conf = (project_root / peers_conf).resolve()

        peer_bind = cls._env("VITRA_PEER_BIND") or "127.0.0.1"
        peer_port = int(cls._env("VITRA_PEER_PORT") or "24161")

        keys_dir = Path(cls._env("VITRA_KEYS_DIR") or (project_root / "keys"))
        trust_root = Path(cls._env("VITRA_TRUST_ROOT") or (project_root / "trust"))
        if not keys_dir.is_absolute():
            keys_dir = (project_root / keys_dir).resolve()
        if not trust_root.is_absolute():
            trust_root = (project_root / trust_root).resolve()

        rom_dir = Path(cls._env("VITRA_ROM_DIR") or (project_root / "rom"))
        if not rom_dir.is_absolute():
            rom_dir = (project_root / rom_dir).resolve()

        forensics_root = Path(cls._env("VITRA_FORENSICS_ROOT") or (project_root / "forensics"))
        if not forensics_root.is_absolute():
            forensics_root = (project_root / forensics_root).resolve()

        decl = WaygateDecl(
            project_root=project_root,
            target_py=target_path,
            host_identity=host_identity,
            operator_identity=operator_identity,
            identity_anchor=identity_anchor,
            continuity_anchor=continuity_anchor,
            session_ttl_s=session_ttl_s,
            net_channel=net_channel,
            cloud_channel=cloud_channel,
            peer_channel=peer_channel,
            net_mode=net_mode,
            peer_mode=peer_mode,
            node_id=node_id,
            peers_conf=peers_conf,
            peer_bind=peer_bind,
            peer_port=peer_port,
            keys_dir=keys_dir,
            trust_root=trust_root,
            rom_dir=rom_dir,
            forensics_root=forensics_root,
            timestamp_utc=cls._now_utc_compact(),
        )
        return decl, defaults_used


@dataclass
class OrganStatus:
    name: str
    ok: bool
    detail: str


@dataclass
class DaySummary:
    day_name: str
    started_utc: str
    ended_utc: str
    organs: List[OrganStatus]
    artifacts: List[str]
    notes: List[str]


@dataclass
class WeekState:
    """Shared RAM-only bundle for the current week-cycle.

    Genesis carries this bundle across the day cadence so organs inherit real
    upstream state instead of acting like seven postcards.
    """

    decl: WaygateDecl
    mode: str
    run_id: str
    seed: int
    bookshelf_mode: str = "paper"
    shelf_notes: List[str] = field(default_factory=list)
    librarian: Any = None
    librarian_address: Dict[str, Any] = field(default_factory=dict)
    receipts: Dict[str, str] = field(default_factory=dict)
    garden_packet: Dict[str, Any] = field(default_factory=dict)
    garden_attachment: Dict[str, Any] = field(default_factory=dict)
    clearance_requested: bool = False
    clearance_route_kind: str = ""
    clearance_helped: bool = False
    eden_packet: Dict[str, Any] = field(default_factory=dict)
    specimen_refs: List[str] = field(default_factory=list)
    dream_invitation: Dict[str, Any] = field(default_factory=dict)
    dream_pack: Dict[str, Any] = field(default_factory=dict)
    dream_db: Optional[Path] = None
    value_sigma_block: Any = None
    hilbert_trace: Dict[str, Any] = field(default_factory=dict)
    bias_bundle: Dict[str, Any] = field(default_factory=dict)
    oracle_reading: Dict[str, Any] = field(default_factory=dict)
    metal_capsule: Dict[str, Any] = field(default_factory=dict)
    availability: Dict[str, str] = field(default_factory=dict)


class GenesisWitness:
    """A small witness/logger that keeps terminal output compact."""

    def __init__(self, decl: WaygateDecl, *, quiet: bool = False):
        self.decl = decl
        self.quiet = quiet

    def say(self, line: str = "") -> None:
        if self.quiet:
            return
        print(line)

    def banner(self, mode: str, defaults_used: Dict[str, str], *, shelf_mode: str = "(pending)") -> None:
        ts = self.decl.timestamp_utc
        self.say(f"#[GENESIS:{ts}] ─────────────────────────────────────────────────────────────")
        self.say(f"#[GENESIS:{ts}] Seed Awake. (Genesis v2.8.1)  mode={mode}")
        self.say(f"#[GENESIS:{ts}] Host={self.decl.host_identity}  Operator={self.decl.operator_identity}  Node={self.decl.node_id}")
        self.say(f"#[GENESIS:{ts}] Net={self.decl.net_channel}/{self.decl.net_mode}  Cloud={self.decl.cloud_channel}  Peer={self.decl.peer_channel}/{self.decl.peer_mode}")
        self.say(f"#[GENESIS:{ts}] ROM={self.decl.rom_dir}  Forensics={self.decl.forensics_root}")
        self.say(f"#[GENESIS:{ts}] Bookshelf posture={shelf_mode}")
        if defaults_used:
            keys = ", ".join(sorted(defaults_used.keys()))
            self.say(f"#[GENESIS:{ts}] Defaults used: {keys}")
        self.say(f"#[GENESIS:{ts}] ─────────────────────────────────────────────────────────────")

    def day_summary(self, summ: DaySummary) -> None:
        self.say("")
        self.say(f"== {summ.day_name} Summary ==")
        self.say(f"Started: {summ.started_utc}  Ended: {summ.ended_utc}")
        if summ.organs:
            ok_ct = sum(1 for o in summ.organs if o.ok)
            self.say(f"Organs: {ok_ct}/{len(summ.organs)} OK")
            for o in summ.organs:
                if not o.ok:
                    self.say(f"- {o.name}: {o.detail}")
        if summ.artifacts:
            self.say("Artifacts:")
            for a in summ.artifacts:
                self.say(f"- {a}")
        if summ.notes:
            self.say("Notes:")
            for n in summ.notes:
                self.say(f"- {n}")


class ForensicsSpine:
    """Filesystem persistence (human-readable witness lane).

    v2.8 posture:
    - Plain-text config snapshot.
    - Append-only step log.
    - Markdown reports and tiny text receipts.
    - Paths remain visible as paths; Genesis leaves footprints, not blobs.
    """

    def __init__(self, root: Path, *, run_id: Optional[str] = None):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self.run_id = run_id or _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%d_%H%M%S")
        self.run_dir = self.root / "runs" / self.run_id
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.steps_path = self.run_dir / "steps.log"
        self.config_path = self.run_dir / "config.txt"

    def write_config(self, decl: WaygateDecl, mode: str, defaults_used: Mapping[str, str], *, shelf_mode: str) -> None:
        lines = [
            "# WAYGATE CONFIG SNAPSHOT",
            f"ts_utc: {decl.timestamp_utc}",
            f"mode: {mode}",
            f"bookshelf_mode: {shelf_mode}",
            "",
            "[declared]",
        ]
        for field in dataclasses.fields(decl):
            val = getattr(decl, field.name)
            lines.append(f"{field.name} = {self._scalar_text(val)}")
        lines.append("")
        lines.append("[defaults_used]")
        if defaults_used:
            for k in sorted(defaults_used.keys()):
                lines.append(f"{k} = {defaults_used[k]}")
        else:
            lines.append("(none)")
        self.config_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def append_step(self, kind: str, payload: Mapping[str, Any]) -> None:
        ts = _utc_iso()
        lines = [
            "--- STEP --------------------------------------------------",
            f"ts_utc: {ts}",
            f"kind: {kind}",
            "",
        ]
        for key, value in payload.items():
            lines.extend(self._render_key_value(key, value))
        lines.append("----------------------------------------------------------")
        with self.steps_path.open("a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

    def write_note(self, filename: str, lines: Iterable[str]) -> Path:
        out = self.run_dir / filename
        out.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return out

    def _render_key_value(self, key: str, value: Any, indent: int = 0) -> List[str]:
        pad = "  " * indent
        if isinstance(value, Mapping):
            lines = [f"{pad}[{key}]"]
            if not value:
                lines.append(f"{pad}(empty)")
                return lines
            for subkey in sorted(value.keys(), key=lambda x: str(x)):
                lines.extend(self._render_key_value(str(subkey), value[subkey], indent + 1))
            return lines
        if isinstance(value, (list, tuple, set)):
            lines = [f"{pad}[{key}]"]
            xs = list(value)
            if not xs:
                lines.append(f"{pad}(empty)")
                return lines
            for item in xs:
                if isinstance(item, (Mapping, list, tuple, set)):
                    lines.extend(self._render_key_value("item", item, indent + 1))
                else:
                    lines.append(f"{pad}- {self._scalar_text(item)}")
            return lines
        return [f"{pad}{key}: {self._scalar_text(value)}"]

    @staticmethod
    def _scalar_text(value: Any) -> str:
        if isinstance(value, Path):
            return str(value)
        if isinstance(value, bool):
            return "yes" if value else "no"
        if value is None:
            return "(none)"
        return str(value)


class OptionalOrgans:
    """Lazy imports for adjacent scripts.

    Genesis may be transported alone with gateway.sh; in that case organs can be
    absent. We report absence as Declared/Observed/Unknown rather than crashing.
    """

    def __init__(self):
        self._cache: Dict[str, Any] = {}

    def _try_import(self, mod_name: str) -> Tuple[bool, str, Any]:
        if mod_name in self._cache:
            mod = self._cache[mod_name]
            return True, "ok", mod
        try:
            mod = __import__(mod_name)
            self._cache[mod_name] = mod
            return True, "ok", mod
        except Exception as e:
            return False, f"missing or failed import: {e}", None

    def gate_of_eden(self):
        return self._try_import("gate_of_eden")

    def projection_oracle(self):
        return self._try_import("projection_oracle")

    def hilbert_engine(self):
        return self._try_import("hilbert_engine")

    def bias_lenses(self):
        return self._try_import("bias_lenses")

    def dream_notebook(self):
        return self._try_import("dream_notebook")

    def sqlibrarian(self):
        return self._try_import("sqlibrarian")

    def garden_of_chuzhoy(self):
        return self._try_import("garden_of_chuzhoy")


DAY_NAMES = [
    "Day 0 — Boot Survey: What Is Present, What Is Missing",
    "Day 1 — Network Bring-Up: Garden, Clearance, and Witness Start",
    "Day 2 — Dream Notebook: Seal One Bounded Draft",
    "Day 3 — Measurement Pass: Hilbert Trace and Oracle Read",
    "Day 4 — Bias Pass: Name the Drift Without Panic",
    "Day 5 — Teaching Writeup: Explain the Week to the Next Builder",
    "Day 6 — Archive Pass: Promote Only What Deserves Continuity",
]


def _utc_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _parse_mode(argv_mode: str) -> str:
    m = (argv_mode or "week").strip().lower()
    if m in {"demo", "week", "diag", "lab", "full"}:
        return m
    return "week"


def _clamp_mode_by_channels(decl: WaygateDecl, mode: str) -> Tuple[str, List[str]]:
    notes: List[str] = []
    effective = mode
    if decl.cloud_channel == "enabled" and mode != "lab":
        notes.append("Cloud channel enabled but mode is not 'lab' — cloud will remain unused.")
    if mode == "lab" and decl.net_channel not in {"app_only", "full"}:
        notes.append("Mode 'lab' requested but net channel is not app_only/full — coercing to 'diag'.")
        effective = "diag"
    if decl.net_channel == "offline" and mode == "lab":
        notes.append("Net channel is offline — coercing lab->diag.")
        effective = "diag"
    return effective, notes


def _make_seed_from_decl(decl: WaygateDecl) -> int:
    salt = f"{decl.identity_anchor}|{decl.node_id}|{decl.timestamp_utc}"
    return abs(hash(salt)) % (2**31 - 1)


def _safe_sig16(value: str) -> str:
    import hashlib
    return hashlib.sha256(value.encode("utf-8", errors="replace")).hexdigest()[:16]


def _detect_bookshelf_posture(organs: OptionalOrgans) -> Tuple[str, List[str], Any, Dict[str, Any]]:
    """Prefer full shelf -> local shelf only -> paper -> witness-only."""
    notes: List[str] = []
    ok, detail, sql_mod = organs.sqlibrarian()
    if not ok or sql_mod is None or not hasattr(sql_mod, "SQLibrarian"):
        notes.append(f"SQLibrarian unavailable ({detail}) — downres to paper mode.")
        return "paper", notes, None, {}
    try:
        librarian = sql_mod.SQLibrarian.boot()
        packet = librarian.address_packet() if hasattr(librarian, "address_packet") else {}
        if bool(packet.get("pg_present")):
            notes.append("Full bookshelf present (SQLite + PostgreSQL).")
            return "full", notes, librarian, dict(packet)
        notes.append("Focus Ledger only (SQLite present; PostgreSQL absent).")
        return "local_only", notes, librarian, dict(packet)
    except Exception as e:
        notes.append(f"SQLibrarian boot failed ({e}) — downres to paper mode.")
        return "paper", notes, None, {}


def _organ_seam_status(name: str, mod: Any) -> str:
    if mod is None:
        return "missing"
    seam_map = {
        "gate_of_eden": ["start_of_run_audit", "witness_blob"],
        "projection_oracle": ["oracle_turn", "oracle_task_menu"],
        "hilbert_engine": ["run_week_cycle_once", "export_compact_trace"],
        "bias_lenses": ["dream_probe_bundle"],
        "dream_notebook": ["DreamNotebook", "RunContext", "Specimen", "DreamConfig", "NotebookStore"],
        "sqlibrarian": ["SQLibrarian"],
        "garden_of_chuzhoy": ["garden_witness", "GardenDeclared"],
    }
    names = seam_map.get(name, [])
    present = [n for n in names if hasattr(mod, n)]
    if not present:
        return "imported; no canonical seam found"
    return "seams=" + ", ".join(present)


def _default_specimen_refs(decl: WaygateDecl) -> List[str]:
    refs: List[str] = []
    for rel in ("genesis.py", "garden_of_chuzhoy.py", "gateway.sh"):
        p = decl.project_root / rel
        if p.exists() and p.is_file():
            refs.append(str(p))
    if decl.target_py.exists() and str(decl.target_py) not in refs:
        refs.insert(0, str(decl.target_py))
    if not refs:
        refs.append(str(decl.target_py))
    return refs[:3]


def _demo_value_sigma(seed: int) -> Optional[Dict[str, Any]]:
    try:
        import numpy as np  # type: ignore
    except Exception:
        return None
    rng = np.random.default_rng(seed)
    value = np.clip(rng.normal(0.50, 0.08, size=(64, 64, 64)), 0.0, 1.0).astype("float32")
    sigma = np.clip(rng.normal(0.50, 0.12, size=(64, 64, 64)), 0.05, 1.0).astype("float32")
    value_sigma = np.stack([value, sigma], axis=-1)
    return {"VALUE": value, "SIGMA": sigma, "value_sigma": value_sigma}


def _garden_declared_from_env() -> Dict[str, Any]:
    return {
        "node_class": os.environ.get("VITRA_GARDEN_NODE_CLASS", "courtyard"),
        "uplink_class": os.environ.get("VITRA_GARDEN_UPLINK_CLASS", "dynamic"),
        "peer_posture": os.environ.get("VITRA_GARDEN_PEER_POSTURE", "disabled"),
        "router_host": os.environ.get("VITRA_GARDEN_HOST", "192.168.1.1"),
        "router_port": os.environ.get("VITRA_GARDEN_PORT", "22"),
        "router_user": os.environ.get("VITRA_GARDEN_USER", "root"),
        "auth_mode": "password" if os.environ.get("VITRA_GARDEN_PASS") else ("key" if os.environ.get("VITRA_GARDEN_KEYFILE") else "agent"),
    }


def _garden_needs_local_help(state: WeekState) -> bool:
    # Garden-of-Chuzhoy 3.0 intention:
    # A node that lacks local uplink may ask the nearest trusted human for a
    # clearance route. This request is local, explicit, and revocable.
    declared = _garden_declared_from_env()
    if declared["uplink_class"] == "offline":
        return False
    if os.environ.get("VITRA_GARDEN_PASS") or os.environ.get("VITRA_GARDEN_KEYFILE"):
        return False
    if state.decl.net_channel == "offline":
        return True
    return declared["auth_mode"] == "agent" and declared["node_class"] in {"courtyard", "sister"}


def _request_local_clearance_route(state: WeekState, forensics: ForensicsSpine, witness: GenesisWitness) -> Tuple[str, bool]:
    # "Clearance route" may mean:
    #   - Wi-Fi SSID/password
    #   - router-admin access
    #   - permission to remain tunnel-only via another chassis
    # Genesis should treat all three as valid human answers.
    state.clearance_requested = True
    lines = [
        "Garden day: this node seeks a clearance route.",
        f"host: {state.decl.host_identity}",
        f"node: {state.decl.node_id}",
        "",
        "Please provide one of:",
        "1. Wi-Fi SSID only",
        "2. Wi-Fi SSID + password",
        "3. Router admin password",
        '4. "use Gunther tunnel for now"',
        '5. "skip for now"',
        "",
        "Secret values should be used locally and not echoed into normal forensics text.",
    ]
    req_path = forensics.write_note("garden_clearance_request.txt", lines)
    witness.say("Garden day: this node seeks a clearance route.")
    witness.say("Nearest trusted human: provide Wi-Fi, router-admin, or tell me to remain tunnel-only.")
    witness.say(f"Clearance note written: {req_path}")

    if not os.environ.get("TERM") or not os.isatty(0):
        return "deferred", False
    try:
        route = input("Route kind [wifi/router_admin/tunnel_only/deferred] (blank=deferred): ").strip().lower() or "deferred"
    except EOFError:
        return "deferred", False

    if route not in {"wifi", "router_admin", "tunnel_only", "deferred"}:
        route = "deferred"

    if route == "wifi":
        try:
            ssid = input("SSID (blank to skip): ").strip()
            pwd = input("Password (input hidden discipline not yet wired; local only): ").strip()
        except EOFError:
            return "deferred", False
        if ssid:
            os.environ["VITRA_GARDEN_WIFI_SSID"] = ssid
        if pwd:
            os.environ["VITRA_GARDEN_PASS"] = pwd
            return route, True
        return route, bool(ssid)

    if route == "router_admin":
        try:
            pwd = input("Router admin password (blank to skip): ").strip()
        except EOFError:
            return "deferred", False
        if pwd:
            os.environ["VITRA_GARDEN_PASS"] = pwd
            return route, True
        return route, False

    if route == "tunnel_only":
        return route, True

    return route, False


def _record_receipt(state: WeekState, name: str, value: str) -> None:
    if value:
        state.receipts[name] = value


def _write_week_epilogue(forensics: ForensicsSpine, state: WeekState, day_summaries: List[DaySummary], notes_global: List[str]) -> Path:
    lines = [
        "# WEEK EPILOGUE",
        f"ts_utc: {_utc_iso()}",
        f"run_id: {state.run_id}",
        f"bookshelf_mode: {state.bookshelf_mode}",
        "",
        "[receipts]",
    ]
    if state.receipts:
        for k in sorted(state.receipts.keys()):
            lines.append(f"{k}: {state.receipts[k]}")
    else:
        lines.append("(none)")
    lines.extend(["", "[days]"])
    for d in day_summaries:
        lines.append(f"- {d.day_name} :: organs={sum(1 for o in d.organs if o.ok)}/{len(d.organs)} notes={len(d.notes)}")
    if notes_global:
        lines.extend(["", "[week_notes]"])
        for n in notes_global:
            lines.append(f"- {n}")
    return forensics.write_note("week_epilogue.txt", lines)


# =====================
# LOOP (the __main__ demonstrative workflow)
# =====================


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        prog="genesis.py",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=textwrap.dedent(
            """\
            Genesis (v2.8) — the seed-script.

            Typical usage (from gateway.sh):
              python genesis.py --mode week

            Modes:
              demo  : short, teachable seam proofs
              week  : day cadence, human-in-the-loop summaries
              diag  : print config + exit
              lab   : heavier experiments (still must obey Waygate channels)
            """
        ),
    )
    ap.add_argument("--mode", default=os.environ.get("VITRA_MODE", "week"), help="demo|week|diag|lab")
    ap.add_argument("--quiet", action="store_true", help="suppress terminal output")
    ap.add_argument("--max-seconds", type=int, default=None, help="override TTL budget (seconds)")
    ap.add_argument("--target", default=None, help="override target script path (rare; mostly Waygate-owned)")

    args = ap.parse_args(argv)

    decl, defaults_used = Waygate.read_declared_reality(argv_target=args.target)
    mode = _parse_mode(args.mode)
    mode, clamp_notes = _clamp_mode_by_channels(decl, mode)

    organs = OptionalOrgans()
    shelf_mode, shelf_notes, librarian, address_packet = _detect_bookshelf_posture(organs)

    witness = GenesisWitness(decl, quiet=bool(args.quiet))
    witness.banner(mode=mode, defaults_used=defaults_used, shelf_mode=shelf_mode)
    witness.say("")
    witness.say("⟐ The membrane has spoken.")
    witness.say("☼ The seed awakens.")
    witness.say("⧁ The courtyard listens.")
    witness.say("")

    forensics = ForensicsSpine(decl.forensics_root, run_id=f"{decl.timestamp_utc}_{mode}")
    forensics.write_config(decl, mode, defaults_used, shelf_mode=shelf_mode)

    ttl = args.max_seconds if args.max_seconds is not None else decl.session_ttl_s
    start = time.time()
    seed = _make_seed_from_decl(decl)
    random.seed(seed)

    state = WeekState(
        decl=decl,
        mode=mode,
        run_id=f"{decl.timestamp_utc}_{mode}",
        seed=seed,
        bookshelf_mode=shelf_mode,
        shelf_notes=list(shelf_notes),
        librarian=librarian,
        librarian_address=address_packet,
        specimen_refs=_default_specimen_refs(decl),
    )

    if state.librarian_address:
        forensics.append_step("bookshelf_boot", state.librarian_address)
        _record_receipt(state, "bookshelf_mode", state.bookshelf_mode)

    if mode == "diag":
        forensics.append_step("diag", {"note": "printed banner + wrote config", "bookshelf_mode": shelf_mode})
        witness.say("(diag) Config written. Exiting.")
        return 0

    if mode == "demo":
        day0 = _run_day_probe("Sunday — Intention", organs, forensics, state)
        witness.day_summary(day0)
        return 0

    notes_global: List[str] = []
    notes_global.extend(clamp_notes)
    notes_global.extend(shelf_notes)

    day_summaries: List[DaySummary] = []
    for idx, day_name in enumerate(DAY_NAMES):
        if time.time() - start > ttl:
            notes_global.append("TTL expired before completing all days.")
            break

        if idx == 0:
            summ = _run_day_sunday(day_name, organs, forensics, witness, state)
        elif idx == 1:
            summ = _run_day_monday(day_name, organs, forensics, witness, state)
        elif idx == 2:
            summ = _run_day_tuesday(day_name, organs, forensics, witness, state)
        elif idx == 3:
            summ = _run_day_wednesday(day_name, organs, forensics, witness, state)
        elif idx == 4:
            summ = _run_day_thursday(day_name, organs, forensics, witness, state)
        elif idx == 5:
            summ = _run_day_friday(day_name, organs, forensics, witness, state)
        else:
            summ = _run_day_saturday(day_name, organs, forensics, witness, state)

        day_summaries.append(summ)
        witness.day_summary(summ)

    epilogue = _write_week_epilogue(forensics, state, day_summaries, notes_global)
    forensics.append_step("week_end", {
        "epilogue": str(epilogue),
        "days": [d.day_name for d in day_summaries],
        "receipts": state.receipts,
    })
    if notes_global:
        witness.say("")
        witness.say("== Week Notes ==")
        for n in notes_global:
            witness.say(f"- {n}")

    witness.say("")
    witness.say("Return complete.")
    return 0


# -----------------
# Day implementations (stateful, still conservative)
# -----------------


def _run_day_probe(day_name: str, organs: OptionalOrgans, forensics: ForensicsSpine, state: WeekState) -> DaySummary:
    t0 = _utc_iso()
    statuses: List[OrganStatus] = []
    artifacts: List[str] = []
    notes: List[str] = []

    for organ_name, getter in [
        ("gate_of_eden", organs.gate_of_eden),
        ("projection_oracle", organs.projection_oracle),
        ("hilbert_engine", organs.hilbert_engine),
        ("bias_lenses", organs.bias_lenses),
        ("dream_notebook", organs.dream_notebook),
        ("sqlibrarian", organs.sqlibrarian),
        ("garden_of_chuzhoy", organs.garden_of_chuzhoy),
    ]:
        ok, detail, mod = getter()
        seam = _organ_seam_status(organ_name, mod)
        state.availability[organ_name] = seam
        statuses.append(OrganStatus(organ_name, ok, seam if ok else detail))

    forensics.append_step("day_probe", {"day": day_name, "availability": state.availability})
    artifacts.append(str(forensics.steps_path))
    t1 = _utc_iso()
    return DaySummary(day_name=day_name, started_utc=t0, ended_utc=t1, organs=statuses, artifacts=artifacts, notes=notes)


def _run_day_sunday(day_name: str, organs: OptionalOrgans, forensics: ForensicsSpine, witness: GenesisWitness, state: WeekState) -> DaySummary:
    t0 = _utc_iso()
    statuses: List[OrganStatus] = []
    artifacts: List[str] = []
    notes: List[str] = []

    notes.append("Sunday intention is discovery: list options, do not commit.")
    probe = _run_day_probe(day_name, organs, forensics, state)
    statuses.extend(probe.organs)

    state.value_sigma_block = _demo_value_sigma(state.seed)
    if state.value_sigma_block is None:
        notes.append("numpy unavailable — no PiBlock specimen built; later days may downres.")
    else:
        notes.append("Built one bounded VALUE/SIGMA specimen for the week.")

    if state.librarian_address:
        notes.append(f"Bookshelf open: {state.bookshelf_mode}")
        forensics.append_step("sunday_bookshelf", state.librarian_address)
        artifacts.append(str(forensics.config_path))

    intent = {
        "origin": "Before Vitra",
        "identity_anchor": state.decl.identity_anchor,
        "continuity_anchor": state.decl.continuity_anchor,
        "specimen_refs": state.specimen_refs,
        "bookshelf_mode": state.bookshelf_mode,
        "options": [
            "Run a Dream Notebook invitation + seal a draft notebook.",
            "Perform a Hilbert week-cycle sweep and export a compact trace.",
            "Record an Oracle reading and Bias bundle with shelf receipts.",
        ],
    }
    forensics.append_step("sunday_intent", intent)
    artifacts.append(str(forensics.steps_path))

    if state.librarian is not None and hasattr(state.librarian, "catalog_artifact"):
        try:
            sig = state.librarian.catalog_artifact(
                locator=f"run:{state.run_id}:config",
                artifact_kind="genesis_intent",
                meta={"bookshelf_mode": state.bookshelf_mode, "host": state.decl.host_identity},
            )
            _record_receipt(state, "sunday_intent", str(sig))
            notes.append(f"Intent cataloged: {sig}")
        except Exception as e:
            notes.append(f"Bookshelf catalog downres: {e}")

    t1 = _utc_iso()
    return DaySummary(day_name=day_name, started_utc=t0, ended_utc=t1, organs=statuses, artifacts=artifacts, notes=notes)


def _run_day_monday(day_name: str, organs: OptionalOrgans, forensics: ForensicsSpine, witness: GenesisWitness, state: WeekState) -> DaySummary:
    t0 = _utc_iso()
    statuses: List[OrganStatus] = []
    artifacts: List[str] = []
    notes: List[str] = []

    # ============================================================
    # ## DAY 1 — NETWORK BRING-UP: GARDEN, CLEARANCE, AND WITNESS START
    #
    # A graduate student should be able to read this section and understand:
    # 1) how this chassis gets network access,
    # 2) who is allowed to help,
    # 3) what gets logged,
    # 4) what must remain secret.
    #
    # The chassis asks a practical question:
    #   "Do I have my own network path, or must the Garden hear for me?"
    #
    # The Garden answers with policy, not passwords.
    # Today the Glass Chest may open.
    # The Iron Chest stays closed in normal witness text.
    # ============================================================

    notes.append("Day 1: Garden first, then Eden, then the local shelf.")

    ok_g, detail_g, garden_mod = organs.garden_of_chuzhoy()
    statuses.append(OrganStatus("garden_of_chuzhoy", ok_g, detail_g if not ok_g else _organ_seam_status("garden_of_chuzhoy", garden_mod)))

    if _garden_needs_local_help(state):
        route_kind, helped = _request_local_clearance_route(state, forensics, witness)
        state.clearance_route_kind = route_kind
        state.clearance_helped = helped
        notes.append(f"Garden clearance route: {route_kind}")
        if helped:
            notes.append("Nearest trusted human provided local help.")
            notes.append("Glass chest: a bounded clearance route was granted; secret details remain local.")
        else:
            notes.append("No local credential captured; Garden may remain tunnel-only or deferred.")
            notes.append("Glass chest: no bounded clearance was granted today.")

    # ============================================================
    # ## SIBLING POSSIBILITY (2.8.x bridge toward 2.9 / 3.0)
    #
    # If another Vitra is present on the LAN, Genesis does not yet attempt a
    # full federation. It prepares the doctrinal shape:
    #   - discover posture
    #   - exchange a bounded hello later
    #   - witness trust locally before transport
    #
    # Recognition, trust, and transport must stay separate.
    # ============================================================
    notes.append("Peer posture declared; sibling greeting remains a bounded future step.")

    garden_packet: Dict[str, Any] = {}
    if ok_g and garden_mod is not None and hasattr(garden_mod, "garden_witness"):
        try:
            garden_packet = garden_mod.garden_witness(ctx=state, eden=None, fx=None)
            state.garden_packet = dict(garden_packet)
            state.garden_attachment = dict(garden_packet.get("eden_attachment") or {})
            notes.append("Garden witness packet acquired.")
        except Exception as e:
            statuses[-1] = OrganStatus("garden_of_chuzhoy", False, f"garden_witness failed: {e}")
            notes.append("Garden witness failed; continue with declared posture only.")
    else:
        notes.append("Garden organ absent; briefing continues without router witness.")

    if state.garden_attachment:
        forensics.append_step("garden_attachment", {
            "node_class": state.garden_attachment.get("node_class"),
            "uplink_class": state.garden_attachment.get("uplink_class"),
            "peer_posture": state.garden_attachment.get("peer_posture"),
            "signature16": state.garden_attachment.get("signature16"),
        })
        artifacts.append(str(forensics.steps_path))
        sig = str(state.garden_attachment.get("signature16") or "")
        _record_receipt(state, "garden_attachment", sig)

    ok_e, detail_e, eden_mod = organs.gate_of_eden()
    statuses.append(OrganStatus("gate_of_eden", ok_e, detail_e if not ok_e else _organ_seam_status("gate_of_eden", eden_mod)))

    audit_packet: Dict[str, Any] = {}
    if ok_e and eden_mod is not None:
        try:
            attachments = {"garden": state.garden_attachment} if state.garden_attachment else None
            audit_packet = eden_mod.start_of_run_audit(
                run_id=state.run_id,
                mode=state.mode,
                project_root=state.decl.project_root,
                forensics_root=state.decl.forensics_root,
                attachments=attachments,
            )
            state.eden_packet = dict(audit_packet)
            notes.append("Eden witness packet established.")
        except Exception as e:
            statuses[-1] = OrganStatus("gate_of_eden", False, f"audit failed: {e}")
            notes.append("Eden audit failed; later days will downres.")

    if state.eden_packet:
        forensics.append_step("monday_audit", {
            "integrity": state.eden_packet.get("integrity") or state.eden_packet.get("verdict"),
            "has_garden_attachment": bool(state.garden_attachment),
            "declared_keys": list((state.eden_packet.get("declared") or {}).keys())[:10],
        })
        if state.librarian is not None and hasattr(state.librarian, "record_witness"):
            try:
                sig = state.librarian.record_witness(state.eden_packet, source="gate_of_eden")
                _record_receipt(state, "monday_witness", str(sig))
                notes.append(f"Witness cataloged: {sig}")
            except Exception as e:
                notes.append(f"Witness shelf downres: {e}")

    t1 = _utc_iso()
    return DaySummary(day_name=day_name, started_utc=t0, ended_utc=t1, organs=statuses, artifacts=artifacts, notes=notes)


def _run_day_tuesday(day_name: str, organs: OptionalOrgans, forensics: ForensicsSpine, witness: GenesisWitness, state: WeekState) -> DaySummary:
    t0 = _utc_iso()
    statuses: List[OrganStatus] = []
    artifacts: List[str] = []
    notes: List[str] = []

    notes.append("Tuesday Attempt #1: instantiate Dream Notebook and seal one bounded draft.")

    ok, detail, dn = organs.dream_notebook()
    statuses.append(OrganStatus("dream_notebook", ok, detail if not ok else _organ_seam_status("dream_notebook", dn)))

    if not ok or dn is None:
        notes.append("Dream Notebook unavailable — later days may use only the demo PiBlock.")
        t1 = _utc_iso()
        return DaySummary(day_name=day_name, started_utc=t0, ended_utc=t1, organs=statuses, artifacts=artifacts, notes=notes)

    try:
        notebook_db = forensics.run_dir / "notebook" / "dream_notebook.sqlite3"
        state.dream_db = notebook_db
        ctx = dn.RunContext(
            run_id=state.run_id,
            label="genesis_week",
            operator=state.decl.operator_identity,
            mode=state.mode,
            seed=state.seed,
            notebook_db=notebook_db,
            forensics_jsonl=None,
        )
        specimen = dn.Specimen(label="week_specimen", refs=list(state.specimen_refs), polarization="none")
        cfg = dn.DreamConfig(
            salience=0.55,
            jitter=0.10,
            frames_k=3,
            dt_s=1.0,
            frame_plan="baseline,lap,hold",
            enable_hilbert=True,
            enable_bias=True,
            hilbert_every_frame=False,
            bias_every_frame=True,
            oracle_in_dream="off",
            metrics_backend="auto",
            rust_bin="",
            record_to_librarian=False,
            bookshelf_root="",
        )
        store = dn.NotebookStore(notebook_db)
        nb = dn.DreamNotebook(ctx=ctx, specimen=specimen, cfg=cfg, store=store, fx=None)
        store.new_run(run_id=ctx.run_id, label=ctx.label, specimen_hash=nb.specimen_hash(), config=dataclasses.asdict(cfg))
        state.dream_invitation = dict(nb.invitation())
        state.dream_pack = dict(nb.run_all())
        notes.append("Dream Notebook invitation + seal completed.")
        if state.value_sigma_block is None:
            state.value_sigma_block = _demo_value_sigma(state.seed)
        if notebook_db.exists():
            artifacts.append(str(notebook_db))
        forensics.append_step("tuesday_dream", {
            "specimen_hash": state.dream_invitation.get("specimen_hash"),
            "refs": state.specimen_refs,
            "notebook_db": str(notebook_db),
            "z_axes": [z.get("name") for z in (state.dream_pack.get("z_axes") or [])],
        })
        if state.librarian is not None and hasattr(state.librarian, "catalog_artifact"):
            try:
                sig = state.librarian.catalog_artifact(
                    locator=str(notebook_db),
                    artifact_kind="dream_notebook_sqlite",
                    meta={"run_id": state.run_id, "specimen_hash": state.dream_invitation.get("specimen_hash")},
                    witness_sig16=state.receipts.get("monday_witness"),
                )
                _record_receipt(state, "tuesday_notebook", str(sig))
            except Exception as e:
                notes.append(f"Notebook catalog downres: {e}")
    except Exception as e:
        statuses[-1] = OrganStatus("dream_notebook", False, f"dream notebook failed: {e}")

    t1 = _utc_iso()
    return DaySummary(day_name=day_name, started_utc=t0, ended_utc=t1, organs=statuses, artifacts=artifacts, notes=notes)


def _run_day_wednesday(day_name: str, organs: OptionalOrgans, forensics: ForensicsSpine, witness: GenesisWitness, state: WeekState) -> DaySummary:
    t0 = _utc_iso()
    statuses: List[OrganStatus] = []
    artifacts: List[str] = []
    notes: List[str] = []

    notes.append("Wednesday Attempt #2: run Hilbert, then hand the trace to Oracle.")

    block = state.value_sigma_block
    if block is None:
        notes.append("No VALUE/SIGMA specimen in RAM — Wednesday downres begins.")

    ok_h, detail_h, hm = organs.hilbert_engine()
    statuses.append(OrganStatus("hilbert_engine", ok_h, detail_h if not ok_h else _organ_seam_status("hilbert_engine", hm)))
    if ok_h and hm is not None and block is not None and hasattr(hm, "run_week_cycle_once"):
        try:
            trace = hm.run_week_cycle_once(block)
            compact = hm.export_compact_trace(trace) if hasattr(hm, "export_compact_trace") else trace
            state.hilbert_trace = dict(compact)
            notes.append("Hilbert trace acquired.")
            forensics.append_step("wednesday_hilbert", {
                "instrument": state.hilbert_trace.get("instrument"),
                "version": state.hilbert_trace.get("version"),
                "source": (state.hilbert_trace.get("unknown") or {}).get("source"),
            })
        except Exception as e:
            statuses[-1] = OrganStatus("hilbert_engine", False, f"hilbert failed: {e}")
            notes.append("Hilbert failed; Oracle may still consult with reduced context.")

    ok_o, detail_o, po = organs.projection_oracle()
    statuses.append(OrganStatus("projection_oracle", ok_o, detail_o if not ok_o else _organ_seam_status("projection_oracle", po)))
    if ok_o and po is not None and block is not None and hasattr(po, "oracle_turn"):
        try:
            oracle_in = block.get("value_sigma") if isinstance(block, dict) and "value_sigma" in block else block
            reading = po.oracle_turn(
                oracle_in,
                eden_packet=state.eden_packet or None,
                context={"phase": "wednesday", "run_id": state.run_id, "bookshelf_mode": state.bookshelf_mode},
                hilbert_trace=state.hilbert_trace or None,
                metal_capsule=state.metal_capsule or None,
            )
            state.oracle_reading = dict(reading)
            notes.append("Oracle reading established.")
            fp = po.oracle_reading_fingerprint(reading) if hasattr(po, "oracle_reading_fingerprint") else ""
            if fp:
                _record_receipt(state, "wednesday_oracle_fp", fp[:16])
            if state.librarian is not None and hasattr(state.librarian, "record_oracle"):
                try:
                    sig = state.librarian.record_oracle(state.oracle_reading, source="projection_oracle")
                    _record_receipt(state, "wednesday_oracle", str(sig))
                    notes.append(f"Oracle cataloged: {sig}")
                except Exception as e:
                    notes.append(f"Oracle shelf downres: {e}")
        except Exception as e:
            statuses[-1] = OrganStatus("projection_oracle", False, f"oracle failed: {e}")
            notes.append("Oracle consult failed.")

    t1 = _utc_iso()
    return DaySummary(day_name=day_name, started_utc=t0, ended_utc=t1, organs=statuses, artifacts=artifacts, notes=notes)


def _run_day_thursday(day_name: str, organs: OptionalOrgans, forensics: ForensicsSpine, witness: GenesisWitness, state: WeekState) -> DaySummary:
    t0 = _utc_iso()
    statuses: List[OrganStatus] = []
    artifacts: List[str] = []
    notes: List[str] = []

    notes.append("Thursday Patch: run Bias Lenses on the week's specimen.")

    ok, detail, bl = organs.bias_lenses()
    statuses.append(OrganStatus("bias_lenses", ok, detail if not ok else _organ_seam_status("bias_lenses", bl)))

    block = state.value_sigma_block
    value_sigma = None
    if isinstance(block, dict):
        value_sigma = block.get("value_sigma")

    if ok and bl is not None and value_sigma is not None and hasattr(bl, "dream_probe_bundle"):
        try:
            canonical_gs = None
            boss = (state.oracle_reading.get("boss") or {}) if state.oracle_reading else {}
            if boss:
                canonical_gs = {
                    "glimmer_core": boss.get("glimmer_core"),
                    "shimmer_core": boss.get("shimmer_core"),
                    "shimmer_spec": boss.get("shimmer_spec"),
                    "ash_residual": boss.get("ash_residual"),
                }
            bundle = bl.dream_probe_bundle(value_sigma, canonical_gs=canonical_gs, include_runtime=False)
            state.bias_bundle = dict(bundle)
            sig = (bundle.get("signature") or {}).get("weave_signature16") or ""
            if sig:
                _record_receipt(state, "thursday_bias_fp", str(sig))
            notes.append("Bias bundle established.")
            if state.librarian is not None and hasattr(state.librarian, "record_bias_bundle"):
                try:
                    lib_sig = state.librarian.record_bias_bundle(state.bias_bundle, source="bias_lenses")
                    _record_receipt(state, "thursday_bias", str(lib_sig))
                    notes.append(f"Bias bundle cataloged: {lib_sig}")
                except Exception as e:
                    notes.append(f"Bias shelf downres: {e}")
            forensics.append_step("thursday_bias", {
                "ok": bundle.get("ok"),
                "weave_signature16": sig,
                "top_families": ((bundle.get("signature") or {}).get("top_families") or []),
                "glimmer": (((bundle.get("composites") or {}).get("glimmer") or {}).get("score")),
                "shimmer": (((bundle.get("composites") or {}).get("shimmer") or {}).get("score")),
            })
        except Exception as e:
            statuses[-1] = OrganStatus("bias_lenses", False, f"dream_probe_bundle failed: {e}")
            notes.append("Bias bundle failed.")
    else:
        notes.append("bias_lenses or VALUE/SIGMA specimen unavailable — Thursday downres.")

    t1 = _utc_iso()
    return DaySummary(day_name=day_name, started_utc=t0, ended_utc=t1, organs=statuses, artifacts=artifacts, notes=notes)


def _run_day_friday(day_name: str, organs: OptionalOrgans, forensics: ForensicsSpine, witness: GenesisWitness, state: WeekState) -> DaySummary:
    t0 = _utc_iso()
    statuses: List[OrganStatus] = []
    artifacts: List[str] = []
    notes: List[str] = []

    # ============================================================
    # ## DAY 5 — TEACHING WRITEUP: EXPLAIN THE WEEK TO THE NEXT BUILDER
    #
    # This file is not just a report.
    # It is an onboarding surface.
    #
    # A future builder should be able to read the writeup and answer:
    #   - what this machine tried to do,
    #   - what organs were present,
    #   - what evidence was produced,
    #   - what remained secret.
    # ============================================================

    notes.append("Day 5: produce the teaching artifact for future coders.")

    ok_sql, detail_sql, sql_mod = organs.sqlibrarian()
    statuses.append(OrganStatus("sqlibrarian", ok_sql, detail_sql if not ok_sql else _organ_seam_status("sqlibrarian", sql_mod)))

    lines = [
        "# Vitra Week Writeup",
        "",
        f"- ts: {_utc_iso()}",
        f"- host: {state.decl.host_identity}",
        f"- operator: {state.decl.operator_identity}",
        f"- node: {state.decl.node_id}",
        f"- bookshelf_mode: {state.bookshelf_mode}",
        "",
        "## Declared Reality",
        "",
        f"- identity_anchor: {state.decl.identity_anchor}",
        f"- continuity_anchor: {state.decl.continuity_anchor}",
        f"- net: {state.decl.net_channel}/{state.decl.net_mode}",
        f"- peer: {state.decl.peer_channel}/{state.decl.peer_mode}",
        "",
        "## Garden",
        "",
        f"- route_kind: {state.clearance_route_kind or '(none)'}",
        f"- local_helped: {'yes' if state.clearance_helped else 'no'}",
        f"- garden_attachment: {state.receipts.get('garden_attachment', '(none)')}",
        "",
        "## Treasure Chests",
        "",
        "- iron_chest: secret values remain local and are never written here",
        f"- glass_chest: receipts present = {'yes' if state.receipts else 'no'}",
        "- chain_seal: inactive in v2.8.1",
        "",
        "## Eden",
        "",
        f"- integrity: {(state.eden_packet.get('integrity') or state.eden_packet.get('verdict') or '(none)') if state.eden_packet else '(none)'}",
        f"- witness_sig16: {state.receipts.get('monday_witness', '(none)')}",
        "",
        "## Dream Notebook",
        "",
        f"- specimen_hash: {state.dream_invitation.get('specimen_hash', '(none)')}",
        f"- notebook_db: {str(state.dream_db) if state.dream_db else '(none)'}",
        "",
        "## Hilbert / Oracle / Bias",
        "",
        f"- oracle_sig16: {state.receipts.get('wednesday_oracle', '(none)')}",
        f"- oracle_fp16: {state.receipts.get('wednesday_oracle_fp', '(none)')}",
        f"- bias_sig16: {state.receipts.get('thursday_bias', '(none)')}",
        f"- bias_fp16: {state.receipts.get('thursday_bias_fp', '(none)')}",
        "",
        "## Bookshelf",
        "",
    ]
    if state.librarian_address:
        lines.append(f"- focus_sqlite: {state.librarian_address.get('focus_sqlite', '(none)')}")
        lines.append(f"- pg_present: {state.librarian_address.get('pg_present', False)}")
        lines.append(f"- pg_schema: {state.librarian_address.get('pg_schema', '(none)')}")
    else:
        lines.append("- bookshelf: downres / paper mode")
    lines.extend(["", "## Notes", ""])
    lines.extend([f"- {n}" for n in state.shelf_notes] or ["- (none)"])

    out = forensics.run_dir / "friday_writeup.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    artifacts.append(str(out))
    forensics.append_step("friday_writeup", {"path": str(out), "receipts": state.receipts})

    t1 = _utc_iso()
    return DaySummary(day_name=day_name, started_utc=t0, ended_utc=t1, organs=statuses, artifacts=artifacts, notes=notes)


def _run_day_saturday(day_name: str, organs: OptionalOrgans, forensics: ForensicsSpine, witness: GenesisWitness, state: WeekState) -> DaySummary:
    t0 = _utc_iso()
    statuses: List[OrganStatus] = []
    artifacts: List[str] = []
    notes: List[str] = []

    # ============================================================
    # ## DAY 6 — ARCHIVE PASS: PROMOTE ONLY WHAT DESERVES CONTINUITY
    #
    # Not everything should be remembered.
    #
    # Good archival behavior is not just saving information.
    # It is proving that the system knows what NOT to store.
    # ============================================================

    notes.append("Day 6: summarize promotion candidates and keep ROM coherent.")

    ok_sql, detail_sql, _ = organs.sqlibrarian()
    statuses.append(OrganStatus("sqlibrarian", ok_sql, detail_sql if not ok_sql else "promotion seam present"))

    if state.librarian is not None and hasattr(state.librarian, "commit_day_to_rom"):
        try:
            report = state.librarian.commit_day_to_rom(reason="end_of_week")
            _record_receipt(state, "saturday_commit", str(report.get("copied", {}).get("cards", 0)))
            lines = [
                "# ARCHIVE RECEIPT",
                f"ts_utc: {_utc_iso()}",
                f"bookshelf_mode: {state.bookshelf_mode}",
                f"focus_sqlite: {report.get('focus_sqlite', '(none)')}",
                f"pg_present: {report.get('pg_present', False)}",
                f"pg_schema: {report.get('pg_schema', '(none)')}",
                f"copied_books: {(report.get('copied') or {}).get('books', 0)}",
                f"copied_cards: {(report.get('copied') or {}).get('cards', 0)}",
                f"note: {report.get('note', '(none)')}",
            ]
            out = forensics.write_note("archive_receipt.txt", lines)
            artifacts.append(str(out))
            notes.append("Saturday promotion report written.")
        except Exception as e:
            notes.append(f"Commit-to-ROM downres: {e}")
    else:
        out = forensics.write_note("archive_receipt.txt", [
            "# ARCHIVE RECEIPT",
            f"ts_utc: {_utc_iso()}",
            f"bookshelf_mode: {state.bookshelf_mode}",
            "note: no durable shelf present; archive remains local and human-readable.",
        ])
        artifacts.append(str(out))
        notes.append("No durable shelf present; paper/scribe archive only.")

    forensics.append_step("saturday_archive", {"run_dir": str(forensics.run_dir), "receipts": state.receipts})

    t1 = _utc_iso()
    return DaySummary(day_name=day_name, started_utc=t0, ended_utc=t1, organs=statuses, artifacts=artifacts, notes=notes)


if __name__ == "__main__":
    raise SystemExit(main())
