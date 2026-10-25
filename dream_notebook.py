#!/usr/bin/env python3
"""
dream_notebook.py  # ⟐→☼→⧁  # Glimmer–Shimmer Diffractometry Notebook (Aurora Cortex v2.6.0)


NO SCHEMA AUTHORITY (2.6)
------------------------
Dream Notebook emits *evidence bundles* (frames, trends, receipts). It does not declare
storage schemas for Eden/Bookshelf. Callers own schemas; this organ stays measurement-only.

v2.5 Upgrade (Frames Ledger)
----------------------------
This notebook keeps the canonical 3-phase doctrine:

  Invitation → Projection Room → Sealing

…but Projection Room is now internally structured as FRAMES (not Days).
Frames provide the time base required for glimmer/shimmer as derivatives:
  - Glimmer emerges as first difference across frames
  - Shimmer emerges as second difference / spectral window across frames

This file is a *high-resolution proving ground* for the glimmer/shimmer contract.
It is still NOT Genesis: it does not orchestrate the whole week-cycle; it records
a bounded experimental replay and seals draft-only results.

Governance (unchanged)
----------------------
- Read-only by default: no ROM grave writes.
- Stores only into a local notebook DB (SQLite) + optional append-only JSONL forensics.
- Any “promotion” is explicit downstream action.

Integrations (best-effort)
--------------------------
Compatible with (degrades gracefully if missing):
  - gate_of_eden.py      (witness membrane)
  - hilbert_engine.py    (projection traces / reports)
  - bias_lenses.py       (feature bundles)
  - projection_oracle.py (rendering / hypothesis suggestion)

"""

from __future__ import annotations

import argparse
import dataclasses as dc
import hashlib
import json
import os
import random
import sqlite3
import subprocess
import sys
import textwrap
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

VERSION = "2.6.0"


# ──────────────────────────────────────────────────────────────────────────────
# Utilities
# ──────────────────────────────────────────────────────────────────────────────

def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def sha256_text(s: str) -> str:
    return sha256_bytes(s.encode("utf-8", errors="replace"))

def safe_json(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=2)


def _normalize_trace_like(x: Any) -> Optional[Dict[str, Any]]:
    """
    Accept either a dict trace OR a small dataclass/object with the usual fields.
    This keeps the Notebook tolerant as Hilbert/Bias/Oracle evolve.
    """
    if x is None:
        return None
    if isinstance(x, dict):
        return x
    try:
        import dataclasses as dc  # local, stdlib
        if dc.is_dataclass(x):
            d = dc.asdict(x)  # type: ignore[arg-type]
            if isinstance(d, dict):
                return d
    except Exception:
        pass
    # Common trace object shape
    try:
        instrument = getattr(x, "instrument", None)
        version = getattr(x, "version", None)
        declared = getattr(x, "declared", None)
        observed = getattr(x, "observed", None)
        unknown = getattr(x, "unknown", None)
        if isinstance(declared, dict) or isinstance(observed, dict) or isinstance(unknown, dict):
            return {
                "instrument": str(instrument or "unknown"),
                "version": str(version or ""),
                "declared": declared if isinstance(declared, dict) else {},
                "observed": observed if isinstance(observed, dict) else {},
                "unknown": unknown if isinstance(unknown, dict) else {},
            }
    except Exception:
        pass
    return {"trace_unreadable": True, "type": type(x).__name__}

def clamp01(x: float) -> float:
    if x < 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return x


def _metrics_min_from_any(m: Any) -> Dict[str, Any]:
    """
    Map backend output (rust/python/other) into a stable minimal metrics dict.
    This prevents downstream diffs from collapsing when the backend evolves.
    """
    if not isinstance(m, dict):
        return {"ok": False, "backend": "unknown", "error": "metrics_not_dict"}

    # Some backends may wrap metrics under "metrics" or "capsule"
    if isinstance(m.get("metrics"), dict):
        mm = dict(m["metrics"])
        mm.setdefault("backend", m.get("backend", "wrapped"))
        mm.setdefault("ok", mm.get("ok", True))
        return mm
    if isinstance(m.get("capsule"), dict) and isinstance(m["capsule"].get("metrics"), dict):
        mm = dict(m["capsule"]["metrics"])
        mm.setdefault("backend", m.get("backend", "wrapped"))
        mm.setdefault("ok", mm.get("ok", True))
        return mm

    out: Dict[str, Any] = {}
    out["backend"] = str(m.get("backend", "unknown"))
    # Core fields (optional)
    for k in ("glimmer_core", "shimmer_core", "ash_residual", "coherence", "closure_residue", "phase_load", "articulation"):
        if k in m:
            out[k] = m.get(k)
    if "shimmer_spec" in m:
        out["shimmer_spec"] = m.get("shimmer_spec")
    # Flag
    out["ok"] = bool(m.get("ok", True)) if "error" not in m else False
    if "error" in m:
        out["error"] = m.get("error")
    return out

def is_tty() -> bool:
    try:
        return sys.stdout.isatty()
    except Exception:
        return False


def _maybe_boot_librarian(cfg: Any) -> Any:
    """
    Optional cultivation hook into SQLibrarian. Off by default.
    Silent grace: absence or failure returns None.
    """
    if not getattr(cfg, "record_to_librarian", False):
        return None
    try:
        from sqlibrarian import SQLibrarian  # type: ignore
        # Prefer explicit bookshelf_root if provided
        kw = {}
        br = getattr(cfg, "bookshelf_root", "")
        if br:
            kw["bookshelf_root"] = Path(br).expanduser()
        return SQLibrarian.boot(project_root=Path(".").resolve(), **kw)  # type: ignore[arg-type]
    except Exception:
        return None

def read_ref_hash(ref: str) -> Tuple[str, str, str]:
    """
    Return (ref, content_type, sha256). Opaque refs hash to themselves.
    """
    p = Path(ref)
    if p.exists() and p.is_file():
        b = p.read_bytes()
        h = sha256_bytes(b)
        ct = "binary"
        if p.suffix.lower() in (".md", ".markdown"):
            ct = "text/markdown"
        elif p.suffix.lower() in (".txt", ".py", ".json", ".yaml", ".yml", ".odt"):
            ct = "text/plain"
        return (str(p), ct, h)
    return (ref, "opaque/ref", sha256_text(ref))


# ──────────────────────────────────────────────────────────────────────────────
# Forensics logger (append-only)
# ──────────────────────────────────────────────────────────────────────────────

class ForensicsJSONL:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def step(self, kind: str, **payload: Any) -> None:
        rec = {"ts_utc": utc_now_iso(), "kind": kind, "payload": payload}
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


# ──────────────────────────────────────────────────────────────────────────────
# Notebook Store (SQLite) — frames ledger
# ──────────────────────────────────────────────────────────────────────────────

class NotebookStore:
    """
    Local notebook DB. Not ROM. Draft-only by doctrine.
    """
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as cx:
            cx.execute("""
                CREATE TABLE IF NOT EXISTS runs (
                    run_id TEXT PRIMARY KEY,
                    ts_utc TEXT NOT NULL,
                    label TEXT,
                    specimen_hash TEXT NOT NULL,
                    config_json TEXT NOT NULL
                )
            """)
            cx.execute("""
                CREATE TABLE IF NOT EXISTS steps (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL,
                    ts_utc TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                )
            """)
            cx.execute("""
                CREATE TABLE IF NOT EXISTS frames (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL,
                    frame_index INTEGER NOT NULL,
                    ts_utc TEXT NOT NULL,
                    dt_s REAL NOT NULL,
                    perturbation_json TEXT NOT NULL,
                    capsule_json TEXT NOT NULL
                )
            """)
            cx.execute("""
                CREATE TABLE IF NOT EXISTS z_packs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL,
                    ts_utc TEXT NOT NULL,
                    pack_json TEXT NOT NULL
                )
            """)
            cx.commit()

    def new_run(self, *, run_id: str, label: str, specimen_hash: str, config: Dict[str, Any]) -> None:
        with sqlite3.connect(self.db_path) as cx:
            cx.execute(
                "INSERT OR REPLACE INTO runs(run_id, ts_utc, label, specimen_hash, config_json) VALUES (?,?,?,?,?)",
                (run_id, utc_now_iso(), label, specimen_hash, safe_json(config)),
            )
            cx.commit()

    def log_step(self, *, run_id: str, kind: str, payload: Dict[str, Any]) -> None:
        with sqlite3.connect(self.db_path) as cx:
            cx.execute(
                "INSERT INTO steps(run_id, ts_utc, kind, payload_json) VALUES (?,?,?,?)",
                (run_id, utc_now_iso(), kind, safe_json(payload)),
            )
            cx.commit()

    def append_frame(
        self,
        *,
        run_id: str,
        frame_index: int,
        dt_s: float,
        perturbation: Dict[str, Any],
        capsule: Dict[str, Any],
    ) -> None:
        with sqlite3.connect(self.db_path) as cx:
            cx.execute(
                "INSERT INTO frames(run_id, frame_index, ts_utc, dt_s, perturbation_json, capsule_json) VALUES (?,?,?,?,?,?)",
                (run_id, frame_index, utc_now_iso(), float(dt_s), safe_json(perturbation), safe_json(capsule)),
            )
            cx.commit()

    def save_z_pack(self, *, run_id: str, pack: Dict[str, Any]) -> None:
        with sqlite3.connect(self.db_path) as cx:
            cx.execute(
                "INSERT INTO z_packs(run_id, ts_utc, pack_json) VALUES (?,?,?)",
                (run_id, utc_now_iso(), safe_json(pack)),
            )
            cx.commit()


# ──────────────────────────────────────────────────────────────────────────────
# Data contracts
# ──────────────────────────────────────────────────────────────────────────────

@dc.dataclass(frozen=True)
class RunContext:
    run_id: str
    label: str
    operator: str
    mode: str              # "week" | "lab" | "demo" | "diag"
    seed: int
    notebook_db: Path
    forensics_jsonl: Optional[Path] = None

@dc.dataclass(frozen=True)
class Specimen:
    label: str
    refs: List[str]
    polarization: str = "none"   # "none" | "shadow_cube"

@dc.dataclass(frozen=True)
class DreamConfig:
    # Replay parameters
    salience: float = 0.55
    jitter: float = 0.15

    # Frames parameters
    frames_k: int = 3
    dt_s: float = 1.0
    frame_plan: str = "baseline,lap,hold"  # can be "baseline,lap,lap" etc.

    # Instrument toggles
    enable_hilbert: bool = True
    enable_bias: bool = True
    hilbert_every_frame: bool = False
    bias_every_frame: bool = True

    # Oracle integration
    oracle_in_dream: str = "off"  # "off" | "once"
    oracle_frame: int = 2

    # Metrics backends
    metrics_backend: str = "auto"  # "auto" | "rust" | "python"
    rust_bin: str = ""             # optional explicit rust binary name/path

    # Optional cultivation hook (off by default)
    record_to_librarian: bool = False
    bookshelf_root: str = ""


# ──────────────────────────────────────────────────────────────────────────────
# Best-effort integrations
# ──────────────────────────────────────────────────────────────────────────────

class Integrations:
    def __init__(self):
        self._eden = None
        self._hilbert = None
        self._bias = None
        self._oracle = None

    def eden(self):
        if self._eden is None:
            try:
                import gate_of_eden  # type: ignore
                self._eden = gate_of_eden
            except Exception:
                self._eden = False
        return self._eden

    def hilbert(self):
        if self._hilbert is None:
            try:
                import hilbert_engine  # type: ignore
                self._hilbert = hilbert_engine
            except Exception:
                self._hilbert = False
        return self._hilbert

    def bias(self):
        if self._bias is None:
            try:
                import bias_lenses  # type: ignore
                self._bias = bias_lenses
            except Exception:
                self._bias = False
        return self._bias

    def oracle(self):
        if self._oracle is None:
            try:
                import projection_oracle  # type: ignore
                self._oracle = projection_oracle
            except Exception:
                self._oracle = False
        return self._oracle


# ──────────────────────────────────────────────────────────────────────────────
# Dream Notebook (v2.5)
# ──────────────────────────────────────────────────────────────────────────────

class DreamNotebook:
    """
    Invitation → Projection Room (Frames) → Sealing
    """

    def __init__(self, ctx: RunContext, specimen: Specimen, cfg: DreamConfig, store: NotebookStore, fx: Optional[ForensicsJSONL]):
        self.ctx = ctx
        self.specimen = specimen
        self.cfg = cfg
        self.store = store
        self.fx = fx
        self.intg = Integrations()
        random.seed(ctx.seed)

    def _log(self, kind: str, payload: Dict[str, Any]) -> None:
        self.store.log_step(run_id=self.ctx.run_id, kind=kind, payload=payload)
        if self.fx:
            self.fx.step(kind, **payload)

    # ── specimen hash ────────────────────────────────────────────────────────

    def _refs(self) -> List[Tuple[str, str, str]]:
        return [read_ref_hash(r) for r in self.specimen.refs]

    def specimen_hash(self) -> str:
        refs = self._refs()
        joined = "\n".join([f"{r}|{ct}|{h}" for (r, ct, h) in refs]) + f"\nPOLARIZATION={self.specimen.polarization}"
        return sha256_text(joined)

    # ── Phase 1: Invitation ──────────────────────────────────────────────────

    def invitation(self) -> Dict[str, Any]:
        refs = self._refs()
        seed = {
            "run_id": self.ctx.run_id,
            "label": self.specimen.label,
            "specimen_hash": self.specimen_hash(),
            "refs": refs,
            "questions": [
                "Which disagreements persist across frames (gap vs torque vs origin)?",
                "Where does tension preserve motion vs become runaway under replay?",
                "What survives lowered salience and ordering jitter without new data?",
            ],
            "governance": {"draft_only": True, "no_auto_rom": True, "no_verdict": True},
        }

        eden = self.intg.eden()
        if eden and hasattr(eden, "witness_blob"):
            try:
                seed["eden_witness"] = eden.witness_blob(safe_json(seed).encode("utf-8"))  # type: ignore
            except Exception as e:
                seed["eden_witness_error"] = repr(e)

        self._log("invitation", seed)
        return seed

    # ── Projection Room: Frames ──────────────────────────────────────────────

    def _jitter_order(self, refs: List[Tuple[str, str, str]]) -> List[Tuple[str, str, str]]:
        if self.cfg.jitter <= 0.0:
            return refs
        rng = random.Random(self.ctx.seed ^ int(self.ctx.run_id[:8], 16))
        out = list(refs)
        rng.shuffle(out)
        return out

    def _frame_plan(self) -> List[str]:
        plan = [p.strip() for p in self.cfg.frame_plan.split(",") if p.strip()]
        if not plan:
            plan = ["baseline", "lap", "hold"]
        # pad/truncate to K
        while len(plan) < self.cfg.frames_k:
            plan.append(plan[-1])
        return plan[: self.cfg.frames_k]

    def _perturbation(self, frame_index: int, frame_kind: str) -> Dict[str, Any]:
        """
        Controlled perturbations. These do NOT mutate the specimen; they mutate the *replay context*.
        """
        # sigma lap factor: gentle default
        lap = 0.99
        if frame_kind == "baseline":
            lap = 1.0
        elif frame_kind == "lap":
            lap = 0.99
        elif frame_kind == "hold":
            lap = 1.0
        else:
            # custom kinds can be encoded as lap:<factor>
            if frame_kind.startswith("lap:"):
                try:
                    lap = float(frame_kind.split(":", 1)[1])
                except Exception:
                    lap = 0.99

        # salience attenuation curve (slightly lower each frame unless baseline/hold)
        sal = clamp01(self.cfg.salience * (1.0 if frame_kind in ("baseline", "hold") else (0.98 ** frame_index)))

        return {
            "frame_index": frame_index,
            "frame_kind": frame_kind,
            "sigma_lap": lap,
            "salience": sal,
            "ordering_jitter": self.cfg.jitter,
            "polarization": self.specimen.polarization,
        }

    # ── Metrics backend: Rust fast path or Python reference ───────────────────

    def _metrics_trace_rust(self, refs: List[Tuple[str, str, str]], perturb: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Optional Rust backend: if a compatible binary is present.
        We keep this best-effort and non-fatal.
        """
        bin_path = self.cfg.rust_bin.strip()
        if not bin_path:
            # try a conventional binary name (can be provided by other labs)
            bin_path = "aurora_cortex"
        # Resolve executable:
        # - Prefer PATH lookup (stable in managed installs)
        # - Fall back to local cwd (Genesis compiles ./aurora_cortex by default)
        exe = shutil_which(bin_path)
        if not exe:
            p = Path(bin_path)
            if p.exists() and os.access(str(p), os.X_OK):
                exe = str(p)
            else:
                p2 = Path(".") / bin_path
                if p2.exists() and os.access(str(p2), os.X_OK):
                    exe = str(p2)
        if not exe:
            return None

        payload = {"op": "metrics", "schema_version": VERSION, "refs": refs, "perturbation": perturb}
        try:
            p = subprocess.run(
                [exe],
                input=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=10,
            )
            if p.returncode != 0:
                return {"backend": "rust", "error": p.stderr.decode("utf-8", errors="replace")[:500], "provenance": {"signature": "aurora_cortex", "bin": exe}}
            out = p.stdout.decode("utf-8", errors="replace")
            return json.loads(out)
        except Exception as e:
            return {"backend": "rust", "error": repr(e), "provenance": {"signature": "aurora_cortex", "bin": exe if 'exe' in locals() else bin_path}}

    def _metrics_trace_python(self, refs: List[Tuple[str, str, str]], perturb: Dict[str, Any]) -> Dict[str, Any]:
        """
        Deterministic reference implementation (proxy).
        Returns a compact capsule-ready metrics dict.
        """
        h = sha256_text(safe_json(refs) + safe_json(perturb))
        def f(i: int) -> float:
            return clamp01(int(h[i:i+2], 16) / 255.0)

        # Core masses
        glimmer_core = f(0) * perturb["salience"]
        shimmer_core = f(2) * (1.0 - perturb["salience"] * 0.35)
        ash_residual = f(4) * (0.4 + perturb["ordering_jitter"])
        # Simple “spectral” proxy: a 3-bin window from hash (placeholder)
        shimmer_spec = [f(6), f(8), f(10)]

        return {
            "backend": "python-proxy",
            "glimmer_core": glimmer_core,
            "shimmer_core": shimmer_core,
            "shimmer_spec": shimmer_spec,
            "ash_residual": ash_residual,
        }

    def metrics_trace(self, refs: List[Tuple[str, str, str]], perturb: Dict[str, Any]) -> Dict[str, Any]:
        """
        Stakeholder-requested helper: first-class metrics capsule.
        """
        # Lazy import inside to avoid unused dependency unless rust path is used
        backend = self.cfg.metrics_backend
        if backend in ("auto", "rust"):
            rust_out = self._metrics_trace_rust(refs, perturb)
            if rust_out is not None:
                return rust_out
            if backend == "rust":
                return {"backend": "rust", "error": "requested rust backend but no compatible binary was found"}
        return self._metrics_trace_python(refs, perturb)

    # ── Hilbert/Bias per-frame ────────────────────────────────────────────────

    def _hilbert(self, refs: List[Tuple[str, str, str]], perturb: Dict[str, Any]) -> Dict[str, Any]:
        if not self.cfg.enable_hilbert:
            return {"enabled": False}
        hil = self.intg.hilbert()
        if not hil:
            return {"enabled": True, "kind": "placeholder", "trace_hash": sha256_text("hilbert:" + safe_json(refs) + safe_json(perturb))}
        try:
            if hasattr(hil, "trace"):
                return {"enabled": True, "kind": "trace", "trace": hil.trace(refs, perturb)}  # type: ignore
            if hasattr(hil, "run_week_cycle_once"):
                joined = "\n\n".join([f"{r} ({ct}): {h}" for r, ct, h in refs])
                value_sigma = {"declared": joined, "observed": joined, "unknown": None}
                rep = hil.run_week_cycle_once(  # type: ignore
                    value_sigma=value_sigma,
                    spec=getattr(hil, "WeekCycleSpec")(
                        identity_anchor=self.specimen.label,
                        run_id=self.ctx.run_id,
                        question_hint=f"dream_notebook:frame:{perturb['frame_index']}",
                        mode=self.ctx.mode,
                        record=False,
                    ),
                    hooks=getattr(hil, "EngineHooks")(fx_step=None, gram_event=None, save_tesseract_record=None),
                    budget_ttl_s=20,
                )
                return {"enabled": True, "kind": "hilbert_week", "report": getattr(rep, "__dict__", str(rep))}
        except Exception as e:
            return {"enabled": True, "kind": "error", "error": repr(e)}
        return {"enabled": True, "kind": "unhandled", "note": "no known hilbert_engine API matched"}

    def _bias(self, refs: List[Tuple[str, str, str]], perturb: Dict[str, Any]) -> Dict[str, Any]:
        if not self.cfg.enable_bias:
            return {"enabled": False}
        bias = self.intg.bias()
        if not bias:
            return {"enabled": True, "kind": "placeholder", "bundle_hash": sha256_text("bias:" + safe_json(refs) + safe_json(perturb))}
        try:
            if hasattr(bias, "bundle_traits"):
                return {"enabled": True, "kind": "bundle_traits", "bundle": bias.bundle_traits(refs)}  # type: ignore
        except Exception as e:
            return {"enabled": True, "kind": "error", "error": repr(e)}
        # fallback keys
        keys = [{"ref": r, "ct": ct, "key": h[:12]} for r, ct, h in refs]
        return {"enabled": True, "kind": "fallback", "keys": keys}

    def projection_room(self) -> Dict[str, Any]:
        """
        Runs K frames, logs a frame ledger, and returns a summarized ledger trend.
        """
        refs0 = self._refs()
        refs = self._jitter_order(refs0)

        plan = self._frame_plan()
        self._log("projection_room_begin", {
            "frames_k": self.cfg.frames_k,
            "dt_s": self.cfg.dt_s,
            "frame_plan": plan,
            "hilbert_every_frame": self.cfg.hilbert_every_frame,
            "bias_every_frame": self.cfg.bias_every_frame,
        })

        ledger: List[Dict[str, Any]] = []
        t0 = time.time()

        for k in range(self.cfg.frames_k):
            frame_kind = plan[k]
            perturb = self._perturbation(k, frame_kind)

            metrics = self.metrics_trace(refs, perturb)

            do_hilbert = self.cfg.enable_hilbert and (self.cfg.hilbert_every_frame or k in (0, self.cfg.frames_k - 1))
            do_bias = self.cfg.enable_bias and (self.cfg.bias_every_frame or k == 0)

            hil = self._hilbert(refs, perturb) if do_hilbert else {"enabled": False}
            bia = self._bias(refs, perturb) if do_bias else {"enabled": False}

            capsule = {
                "kind": "dream_frame",
                "frame_index": k,
                "ts_utc": utc_now_iso(),
                "dt_s": self.cfg.dt_s,
                "mode": self.ctx.mode,
                "perturbation": perturb,
                "metrics": metrics,
                "metrics_min": _metrics_min_from_any(metrics),
                "provenance": {
                    "metrics_backend": str(metrics.get("backend", "unknown")) if isinstance(metrics, dict) else "unknown",
                    "schema_version": VERSION,
                },
                "hilbert": _normalize_trace_like(hil) if do_hilbert else {"enabled": False},
                "bias": _normalize_trace_like(bia) if do_bias else {"enabled": False},
                "meta": {
                    "authority": {"schema": "none", "organ": "dream_notebook"},
                    "version": VERSION,
                },
            }

            # Deterministic capsule identifiers (evidence, not schema)
            capsule_sha = sha256_text(safe_json(capsule))
            capsule["sha256"] = capsule_sha
            capsule["sig16"] = capsule_sha[:16]


            self.store.append_frame(
                run_id=self.ctx.run_id,
                frame_index=k,
                dt_s=float(self.cfg.dt_s),
                perturbation=perturb,
                capsule=capsule,
            )

            # Optional cultivation: record frame capsule into Bookshelf if configured.
            if getattr(self, "librarian", None):
                try:
                    loc = f"dream:frame:{capsule.get('sig16','')}"
                    if hasattr(self.librarian, "catalog_artifact"):
                        self.librarian.catalog_artifact(
                            locator=loc,
                            artifact_kind="dream_frame",
                            sig16=str(capsule.get("sig16", "")),
                            meta={"frame_index": k, "dt_s": float(self.cfg.dt_s)},
                        )
                    if hasattr(self.librarian, "record_event"):
                        self.librarian.record_event(kind="dream_frame", payload=capsule)
                except Exception:
                    pass
            self._log("frame", {"frame_index": k, "frame_kind": frame_kind, "metrics_backend": metrics.get("backend", "?")})
            ledger.append(capsule)

            # optional oracle consult reads ledger trend (summary, not raw arrays)
            if self.cfg.oracle_in_dream == "once" and k == int(self.cfg.oracle_frame):
                self._oracle_once(ledger)

            # wall-clock separation helps audit logs
            time.sleep(0.02)

        dt_total = time.time() - t0
        trend = self._ledger_trend(ledger)
        self._log("projection_room_end", {"dt_total_s": dt_total, "trend": trend})
        return {"ledger": ledger, "trend": trend}

    def _ledger_trend(self, ledger: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Produce a trend summary suitable for oracle-in-dream and sealing.
        """
        g = []
        s = []
        a = []
        spec = []
        for frame in ledger:
            m = frame.get("metrics", {})
            g.append(float(m.get("glimmer_core", 0.0)) if isinstance(m.get("glimmer_core", 0.0), (int, float)) else 0.0)
            s.append(float(m.get("shimmer_core", 0.0)) if isinstance(m.get("shimmer_core", 0.0), (int, float)) else 0.0)
            a.append(float(m.get("ash_residual", 0.0)) if isinstance(m.get("ash_residual", 0.0), (int, float)) else 0.0)
            ss = m.get("shimmer_spec", [])
            spec.append(ss if isinstance(ss, list) else [])
        # first / second differences (derivative-ish)
        dg = [g[i] - g[i-1] for i in range(1, len(g))] if len(g) > 1 else []
        ds = [s[i] - s[i-1] for i in range(1, len(s))] if len(s) > 1 else []
        d2g = [dg[i] - dg[i-1] for i in range(1, len(dg))] if len(dg) > 1 else []
        d2s = [ds[i] - ds[i-1] for i in range(1, len(ds))] if len(ds) > 1 else []
        return {
            "glimmer_core": g,
            "shimmer_core": s,
            "ash_residual": a,
            "shimmer_spec": spec,
            "d_glimmer": dg,
            "d_shimmer": ds,
            "dd_glimmer": d2g,
            "dd_shimmer": d2s,
        }

    def _oracle_once(self, ledger: List[Dict[str, Any]]) -> None:
        """
        Oracle consult is *read-only* and receives trend summaries, not raw arrays.
        """
        oracle = self.intg.oracle()
        trend = self._ledger_trend(ledger)
        if not oracle:
            self._log("oracle_once", {"enabled": True, "kind": "placeholder", "trend_hash": sha256_text(safe_json(trend))})
            return
        try:
            if hasattr(oracle, "consult_from_trend"):
                res = oracle.consult_from_trend(trend)  # type: ignore
                self._log("oracle_once", {"enabled": True, "kind": "consult_from_trend", "result": res})
                return
        except Exception as e:
            self._log("oracle_once_error", {"error": repr(e)})
            return
        self._log("oracle_once", {"enabled": True, "kind": "unhandled", "trend_hash": sha256_text(safe_json(trend))})

    # ── Phase 3: Sealing ──────────────────────────────────────────────────────

    def seal(self, proj: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a draft Z-pack from the frame ledger trend. Draft-only.
        """
        trend = proj.get("trend", {})
        z_pack = {
            "run_id": self.ctx.run_id,
            "ts_utc": utc_now_iso(),
            "label": self.specimen.label,
            "specimen_hash": self.specimen_hash(),
            "polarization": self.specimen.polarization,
            "trend": trend,
            "capsules": {
                "final": (proj.get("ledger", [])[-1] if proj.get("ledger") else None),
                "frame_count": len(proj.get("ledger", []) or []),
            },
            "z_axes": [
                {
                    "name": "frame_derivative_contract",
                    "invariant": "Glimmer and shimmer are derivatives across witnessed frames; never claim them from a single snapshot.",
                    "apply_hint": "Use d_glimmer and dd_shimmer from the trend as primary narrative constraints.",
                },
                {
                    "name": "gap_torque_origin_parallax",
                    "invariant": "Treat disagreement between semantic basis (gap), mechanical basis (torque), and formal basis (origin) as depth, not contradiction.",
                    "apply_hint": "When parallax rises across frames, render both views and record ash_residual, not verdicts.",
                },
                {
                    "name": "polarization_shadow_cube",
                    "invariant": "When data objects are short by one, generate the shadow specimen by flipping all axes; compare residues.",
                    "apply_hint": "Run a second notebook pass with --polarization shadow_cube and compare trend deltas.",
                },
            ],
            "governance": {"draft_only": True, "no_auto_rom": True, "promotion_requires_explicit_action": True},
        }
        self.store.save_z_pack(run_id=self.ctx.run_id, pack=z_pack)
        self._log("seal", {"z_axes": [z["name"] for z in z_pack["z_axes"]]})
        return z_pack

    # ── One-shot ──────────────────────────────────────────────────────────────

    def run_all(self) -> Dict[str, Any]:
        self.invitation()
        proj = self.projection_room()
        return self.seal(proj)


# ──────────────────────────────────────────────────────────────────────────────
# Small helpers
# ──────────────────────────────────────────────────────────────────────────────

def shutil_which(cmd: str) -> Optional[str]:
    # local minimal which to avoid importing shutil in constrained environments
    if os.path.isabs(cmd) and os.access(cmd, os.X_OK):
        return cmd
    paths = os.environ.get("PATH", "").split(os.pathsep)
    for p in paths:
        c = os.path.join(p, cmd)
        if os.path.isfile(c) and os.access(c, os.X_OK):
            return c
    return None


# ──────────────────────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────────────────────

def build_default_ctx(args: argparse.Namespace) -> RunContext:
    run_id = args.run_id or sha256_text(utc_now_iso() + str(os.getpid()))[:16]
    seed = args.seed if args.seed is not None else int(run_id[:8], 16)
    operator = args.operator or os.environ.get("USER", "operator")
    db = Path(args.notebook_db).expanduser()
    fx_path = Path(args.forensics_jsonl).expanduser() if args.forensics_jsonl else None
    return RunContext(
        run_id=run_id,
        label=args.label or "dream",
        operator=operator,
        mode=args.mode,
        seed=seed,
        notebook_db=db,
        forensics_jsonl=fx_path,
    )

def parse_specimen(args: argparse.Namespace) -> Specimen:
    refs = list(args.refs or [])
    if not refs:
        raise SystemExit("No specimen refs provided. Use: --ref <path_or_id> ...")
    pol = args.polarization or "none"
    return Specimen(label=args.specimen_label or "specimen", refs=refs, polarization=pol)

def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        prog="dream_notebook.py",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=textwrap.dedent("""
            Dream Notebook (Aurora Cortex v2.5)

            Invitation → Projection Room (Frames) → Sealing

            Key v2.5 change:
              - Projection Room now emits a frame ledger (K frames) so glimmer/shimmer
                can be measured as derivatives, not single-snapshot theory.

            Safe-by-default:
              - No ROM writes.
              - Draft-only outputs into a local SQLite notebook DB.
        """).strip(),
    )

    ap.add_argument("--mode", default="lab", choices=["demo", "lab", "week", "diag"])
    ap.add_argument("--run-id", default=None)
    ap.add_argument("--label", default="dream")
    ap.add_argument("--operator", default=None)
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--notebook-db", default=str(Path("notebook") / "dream_notebook.sqlite3"))
    ap.add_argument("--forensics-jsonl", default=None)

    ap.add_argument("--specimen-label", default="abrahamic-tree")
    ap.add_argument("--polarization", default="none", choices=["none", "shadow_cube"])
    ap.add_argument("--ref", dest="refs", action="append", default=[])

    ap.add_argument("--salience", type=float, default=0.55)
    ap.add_argument("--jitter", type=float, default=0.15)

    ap.add_argument("--frames", type=int, default=3, help="Number of frames (K). Default 3.")
    ap.add_argument("--dt", type=float, default=1.0, help="dt seconds per frame (logical time).")
    ap.add_argument("--frame-plan", default="baseline,lap,hold", help="Comma plan, e.g. baseline,lap,lap or baseline,lap:0.98,hold")

    ap.add_argument("--hilbert", action="store_true", help="Enable hilbert integration (default on).")
    ap.add_argument("--no-hilbert", action="store_true", help="Disable hilbert integration.")
    ap.add_argument("--bias", action="store_true", help="Enable bias integration (default on).")
    ap.add_argument("--no-bias", action="store_true", help="Disable bias integration.")

    ap.add_argument("--hilbert-every-frame", action="store_true")
    ap.add_argument("--bias-every-frame", action="store_true", default=True)

    ap.add_argument("--oracle-in-dream", default="off", choices=["off", "once"])
    ap.add_argument("--oracle-frame", type=int, default=2)

    ap.add_argument("--metrics-backend", default="auto", choices=["auto", "rust", "python"])
    ap.add_argument("--rust-bin", default="", help="Optional path/name of rust metrics binary.")
    ap.add_argument("--print-zpack", action="store_true")

    args = ap.parse_args(argv)

    ctx = build_default_ctx(args)
    specimen = parse_specimen(args)

    cfg = DreamConfig(
        salience=clamp01(float(args.salience)),
        jitter=clamp01(float(args.jitter)),
        frames_k=max(1, int(args.frames)),
        dt_s=float(args.dt),
        frame_plan=str(args.frame_plan),
        enable_hilbert=False if args.no_hilbert else True,
        enable_bias=False if args.no_bias else True,
        hilbert_every_frame=bool(args.hilbert_every_frame),
        bias_every_frame=bool(args.bias_every_frame),
        oracle_in_dream=str(args.oracle_in_dream),
        oracle_frame=int(args.oracle_frame),
        metrics_backend=str(args.metrics_backend),
        rust_bin=str(args.rust_bin),
        record_to_librarian=bool(args.record_to_librarian),
        bookshelf_root=str(args.bookshelf_root),
    )

    store = NotebookStore(ctx.notebook_db)
    fx = ForensicsJSONL(Path(ctx.forensics_jsonl)) if ctx.forensics_jsonl else None

    store.new_run(run_id=ctx.run_id, label=ctx.label, specimen_hash="(pending)", config=dc.asdict(cfg))
    nb = DreamNotebook(ctx=ctx, specimen=specimen, cfg=cfg, store=store, fx=fx)
    store.new_run(run_id=ctx.run_id, label=ctx.label, specimen_hash=nb.specimen_hash(), config=dc.asdict(cfg))

    z_pack = nb.run_all()

    if args.print_zpack:
        print(safe_json(z_pack))

    if is_tty():
        print(f"[dream_notebook] run_id={ctx.run_id} specimen_hash={nb.specimen_hash()}")
        print(f"[dream_notebook] notebook_db={ctx.notebook_db}")
        if ctx.forensics_jsonl:
            print(f"[dream_notebook] forensics_jsonl={ctx.forensics_jsonl}")
        print("[dream_notebook] sealed draft z-pack (promotion requires explicit downstream action)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
