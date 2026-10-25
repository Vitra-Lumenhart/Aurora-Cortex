#!/usr/bin/env python3
"""
projection_oracle.py — v2.8.0  (METAL FIRST + TRACE OBEDIENCE + HILBERT 2.8)
Semantic Geometry Mapping / Aurora Cortex

☼⟐ Reflect → Refract → Return. ⟐☼

CANON LADDER (read-only ascent):
  Gate (declare) → Eden (witness) → Bytes (VALUE/SIGMA) → Metal Metrics (measured) → Oracle (interpret)

LANE LINES (non-negotiable):
  - RAM-only: Oracle does not persist, does not mutate upstream artifacts, does not author schemas.
  - Witness obedience: Declared / Observed / Unknown are preserved as received.
  - Refuse on explicit witness failure. Downgrade/silence on unknowns.
  - Metal first: when Rust/metal metrics exist, treat as measured evidence; Python does not re-derive.
  - Single-shot: one consult = one bounded pass (no iterative refinement loops).
  - Single retrieval discipline is upheld by Genesis/Bookshelf (Oracle accepts already-held RAM objects).

PUBLIC SEAM (stable):
  - oracle_emit_invitation(ctx=None, hooks=RecordHooks()) -> None
  - oracle_task_menu() -> str
  - oracle_turn(value_sigma_or_bundle, *, eden_packet=None, instruments=(...), context=None, hooks=..., budget_ttl_s=20,
               metal_capsule=None, hilbert_trace=None) -> dict
  - oracle_reading_fingerprint(reading: Mapping[str,Any]) -> str

OOP HEADER MANDATE (2.5):
  We keep the public seam functions, but implement them via:
      ProjectionOracle(policy=OraclePolicy(...)).turn(...)

This makes Genesis free to reorder/retain instances later while remaining call-compatible today.

NOTE:
  Oracle is not a calculator anymore.
  Oracle is a reader of witnessed, metal-produced measurements.
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import dataclasses as dc
import math
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np


# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────
PI_SHAPE = (64, 64, 64, 2)
CH_VALUE = 0
CH_SIGMA = 1


VERSION = "2.8.0"


# ─────────────────────────────────────────────────────────────────────────────
# Hooks (caller-owned sinks)
# ─────────────────────────────────────────────────────────────────────────────
@dataclass
class RecordHooks:
    """Optional integration hooks. Oracle writes nothing by itself."""
    fx_step: Optional[Callable[[str, Dict[str, Any]], None]] = None


def _fx(hooks: RecordHooks, phase: str, **payload: Any) -> None:
    if hooks.fx_step is not None:
        hooks.fx_step("oracle", {"phase": phase, **payload})


# ─────────────────────────────────────────────────────────────────────────────
# Policy knobs (2.5 tuning lives here)
# ─────────────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class OraclePolicy:
    """Threshold policy (explicit; Genesis may override per run)."""
    shimmer_high: float = 0.70
    shimmer_medium: float = 0.45
    glimmer_strong: float = 0.65
    glimmer_weak: float = 0.20
    dominant_sigma_downgrade: float = 0.75
    sigma_pressure_threshold: float = 0.60   # lightweight observation only (not a “metric”)
    risk_shadow_value_cut: float = 0.50      # lightweight observation only (not a “metric”)


# ─────────────────────────────────────────────────────────────────────────────
# Small utilities (JSON-friendly, deterministic)
# ─────────────────────────────────────────────────────────────────────────────
def _now_utc_iso() -> str:
    return _dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _sha16(*parts: str) -> str:
    raw = "|".join(parts).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:16]


def _safe_float(x: Any, default: float = 0.0) -> float:
    try:
        return float(x)
    except Exception:
        return float(default)


def _clip01(x: np.ndarray) -> np.ndarray:
    return np.clip(x, 0.0, 1.0)


def _normalize_trace_like(x: Any) -> Optional[Dict[str, Any]]:
    """
    Accept either a plain dict trace OR a small dataclass/object with the usual fields.
    This keeps Oracle tolerant as other instruments (Hilbert) evolve.
    """
    if x is None:
        return None
    if isinstance(x, dict):
        return x
    # Common dataclass / object shape: .instrument/.version/.declared/.observed/.unknown
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
    # Last resort: dataclasses.asdict (if it's a dataclass)
    try:
        if dc.is_dataclass(x):
            d = dc.asdict(x)  # type: ignore[arg-type]
            if isinstance(d, dict):
                return d
    except Exception:
        pass
    return None


def _first_number(x: Any) -> Optional[float]:
    """Return a representative float from a scalar/list/dict payload, or None."""
    if x is None:
        return None
    if isinstance(x, (int, float)):
        try:
            return float(x)
        except Exception:
            return None
    if isinstance(x, (list, tuple)) and x:
        vals = [ _safe_float(v, float('nan')) for v in x ]
        vals = [v for v in vals if math.isfinite(v)]
        if vals:
            return float(sum(vals) / len(vals))
        return None
    if isinstance(x, dict) and x:
        vals = []
        for v in x.values():
            try:
                fv = float(v)
            except Exception:
                continue
            if math.isfinite(fv):
                vals.append(fv)
        if vals:
            return float(sum(vals) / len(vals))
    return None


def _hilbert_summary(trace: Any) -> Dict[str, Any]:
    """
    Read both legacy Hilbert traces and 2.8 projection-centered traces without
    mutating witness content. Oracle only summarizes what is already present.
    """
    tr = _normalize_trace_like(trace)
    if not isinstance(tr, dict):
        return {
            "dominant_pole": "unknown",
            "entropy": None,
            "dominant_sigma": None,
            "identity_fraction": None,
            "residual_fraction": None,
            "knowledge_fraction": None,
            "coherence": None,
            "residue": None,
            "backend": None,
            "projection_state": None,
            "modal_summary": None,
        }

    observed = tr.get("observed") if isinstance(tr.get("observed"), dict) else {}
    trace_inner = tr.get("trace") if isinstance(tr.get("trace"), dict) else {}

    identity_projection = observed.get("identity_projection") if isinstance(observed.get("identity_projection"), dict) else {}
    knowledge_projection = observed.get("knowledge_projection") if isinstance(observed.get("knowledge_projection"), dict) else {}
    projection_state = observed.get("projection_state") if isinstance(observed.get("projection_state"), dict) else {}
    modal_summary = observed.get("modal_summary") if isinstance(observed.get("modal_summary"), dict) else {}

    dominant_pole = "unknown"
    bary = observed.get("barycentric") or tr.get("barycentric") or trace_inner.get("barycentric")
    if isinstance(bary, dict) and bary:
        dominant_pole = max(bary.items(), key=lambda kv: _safe_float(kv[1], 0.0))[0]

    entropy_v = observed.get("entropy", tr.get("entropy", trace_inner.get("entropy")))
    sigma_block = observed.get("sigma") or tr.get("sigma") or trace_inner.get("sigma")
    dom_sigma = None
    if isinstance(sigma_block, dict) and dominant_pole in sigma_block:
        dom_sigma = sigma_block[dominant_pole]

    identity_fraction = _first_number(
        identity_projection.get("identity_fraction", projection_state.get("identity_fraction"))
    )
    residual_fraction = _first_number(
        identity_projection.get("residual_fraction", projection_state.get("residual_fraction"))
    )
    knowledge_fraction = _first_number(
        knowledge_projection.get("knowledge_fraction") or projection_state.get("knowledge_fraction")
    )
    coherence = _first_number(observed.get("coherence", tr.get("coherence", trace_inner.get("coherence"))))
    residue = _first_number(observed.get("residue", tr.get("residue", trace_inner.get("residue"))))
    backend = observed.get("backend") or tr.get("backend") or (tr.get("unknown") or {}).get("source")

    return {
        "dominant_pole": dominant_pole,
        "entropy": entropy_v,
        "dominant_sigma": dom_sigma,
        "identity_fraction": identity_fraction,
        "residual_fraction": residual_fraction,
        "knowledge_fraction": knowledge_fraction,
        "coherence": coherence,
        "residue": residue,
        "backend": backend,
        "projection_state": projection_state or None,
        "modal_summary": modal_summary or None,
    }


# ─────────────────────────────────────────────────────────────────────────────
# ProjectionOracle (core engine)
# ─────────────────────────────────────────────────────────────────────────────
@dataclass
class ProjectionOracle:
    """
    The Oracle organ: interprets witnessed bytes + measured metal capsules into bounded advice.
    No persistence. No schema authority. No upstream mutation.
    """
    policy: OraclePolicy = field(default_factory=OraclePolicy)

    # ---- Eden witness obedience (never upgrade)
    def eden_integrity(self, eden_packet: Optional[Mapping[str, Any]]) -> str:
        if not eden_packet:
            return "unknown"
        return str(eden_packet.get("integrity", eden_packet.get("verdict", "unknown"))).lower()

    def eden_triad(self, eden_packet: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
        if not eden_packet:
            return {"declared": None, "observed": None, "unknown": None}
        return {
            "declared": eden_packet.get("declared"),
            "observed": eden_packet.get("observed"),
            "unknown": eden_packet.get("unknown"),
        }

    # ---- VALUE/SIGMA extraction
    def as_np_value_sigma(self, obj: Any) -> Optional[np.ndarray]:
        if isinstance(obj, np.ndarray):
            arr = np.asarray(obj)
            if arr.shape == PI_SHAPE:
                return arr.astype(np.float32, copy=False)
            if int(np.prod(arr.shape)) == int(np.prod(PI_SHAPE)):
                try:
                    return arr.reshape(PI_SHAPE).astype(np.float32, copy=False)
                except Exception:
                    return None
            return None

        if isinstance(obj, dict):
            for k in ("value_sigma", "value_sigma_grid", "block", "piblock"):
                if k in obj:
                    return self.as_np_value_sigma(obj[k])
        return None

    # ---- Metal metrics capsule detection (read-only)
    _METAL_KEYS = ("glimmer_core", "shimmer_core", "shimmer_spec", "ash_residual")

    def looks_like_metal_capsule(self, d: Any) -> bool:
        if not isinstance(d, dict):
            return False
        backend = str(d.get("backend", "")).lower()
        if backend == "rust":
            return True
        prov = d.get("provenance") or d.get("trace") or {}
        if isinstance(prov, dict):
            sig = str(prov.get("signature", prov.get("bin", prov.get("rust_bin", "")))).lower()
            # Trilogy update: accept the new Rust organ binary signature.
            if ("aurora_cortex" in sig) or ("aurora_metal_metrics" in sig):
                return True
        return any(k in d for k in self._METAL_KEYS)

    def extract_metal_capsules(self, bundle: Any, *, depth: int = 3) -> List[Dict[str, Any]]:
        """Bounded search for metrics dicts (no unbounded recursion)."""
        found: List[Dict[str, Any]] = []

        def visit(x: Any, d: int) -> None:
            if d <= 0:
                return
            if isinstance(x, dict):
                if self.looks_like_metal_capsule(x):
                    found.append(x)
                for v in x.values():
                    visit(v, d - 1)
            elif isinstance(x, (list, tuple)):
                for v in x[:12]:
                    visit(v, d - 1)

        visit(bundle, depth)

        uniq: Dict[str, Dict[str, Any]] = {}
        for c in found:
            fp = _sha16(
                str(c.get("backend", "")),
                str(c.get("glimmer_core", "")),
                str(c.get("shimmer_core", "")),
                str(c.get("ash_residual", "")),
            )
            uniq.setdefault(fp, c)
        return list(uniq.values())

    def normalize_capsule(self, c: Dict[str, Any]) -> Dict[str, Any]:
        """Return JSON-serializable capsule subset; never rewrite numeric values."""
        out: Dict[str, Any] = {"backend": c.get("backend", "unknown")}
        for k in self._METAL_KEYS:
            if k in c:
                out[k] = c[k]
        for k in ("sha256", "hash", "integrity", "rust_bin", "signature"):
            if k in c:
                out[k] = c[k]
        if isinstance(c.get("provenance"), dict):
            out["provenance"] = dict(c["provenance"])
        return out

    # ---- Shimmer / Glimmer semantics (2.5)
    def gs_status_from_capsules(self, caps: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
        if not caps:
            return {
                "metal_metrics_available": False,
                "glimmer_core": None,
                "shimmer_core": None,
                "shimmer_spec": None,
                "ash_residual": None,
                "glimmer_status": "unknown",
                "shimmer_status": "unknown",
            }

        rust = [c for c in caps if str(c.get("backend", "")).lower() == "rust"]
        c = rust[0] if rust else caps[0]

        gl = _safe_float(c.get("glimmer_core"), default=float("nan"))
        sh = _safe_float(c.get("shimmer_core"), default=float("nan"))

        shimmer_status = "low"
        if math.isnan(sh):
            shimmer_status = "unknown"
        elif sh >= self.policy.shimmer_high:
            shimmer_status = "high"
        elif sh >= self.policy.shimmer_medium:
            shimmer_status = "medium"

        glimmer_status = "stable"
        if math.isnan(gl):
            glimmer_status = "unknown"
        elif gl >= self.policy.glimmer_strong:
            glimmer_status = "strong"
        elif gl <= self.policy.glimmer_weak:
            glimmer_status = "weak"

        return {
            "metal_metrics_available": True,
            "glimmer_core": c.get("glimmer_core"),
            "shimmer_core": c.get("shimmer_core"),
            "shimmer_spec": c.get("shimmer_spec"),
            "ash_residual": c.get("ash_residual"),
            "glimmer_status": glimmer_status,
            "shimmer_status": shimmer_status,
            "capsule": self.normalize_capsule(c),
        }

    # ---- Instrument acquisition (prefer metal traces)
    def find_hilbert_trace_in_bundle(self, bundle: Any) -> Optional[Dict[str, Any]]:
        """
        Metal-first preference: consume observed traces if already present.
        Bounded key search (high leverage, low risk).
        """
        if not isinstance(bundle, dict):
            return None

        # Direct keys
        for k in ("hilbert", "hilbert_trace"):
            v = bundle.get(k)
            v2 = _normalize_trace_like(v)
            if isinstance(v2, dict):
                return v2

        # Nested: instruments.hilbert / trace.hilbert
        for a, b in (("instruments", "hilbert"), ("trace", "hilbert"), ("traces", "hilbert")):
            v = bundle.get(a)
            if isinstance(v, dict):
                v2 = _normalize_trace_like(v.get(b))
                if isinstance(v2, dict):
                    return v2

        # One more bounded hop: instruments.hilbert_trace
        v = bundle.get("instruments")
        if isinstance(v, dict):
            v2 = _normalize_trace_like(v.get("hilbert_trace"))
            if isinstance(v2, dict):
                return v2

        return None

    def hilbert(self, value_sigma: np.ndarray, *, hooks: RecordHooks, ttl_ok: bool) -> Dict[str, Any]:
        if not ttl_ok:
            return {"kind": "hilbert", "trace": {"note": "hilbert disabled or ttl exceeded"}}

        t0 = time.time()
        try:
            import hilbert_engine as he  # type: ignore
            if hasattr(he, "hilbert_triangle_projection"):
                tri = he.hilbert_triangle_projection(value_sigma, lambda_uncert=0.5)
                _fx(hooks, "instrument", instrument="hilbert_triangle", entropy=_safe_float(tri.get("entropy"), 9.0))
                return {"kind": "hilbert_triangle", "trace": tri, "elapsed_s": float(time.time() - t0)}
            return {"kind": "hilbert", "trace": {"note": "hilbert_engine present but no compatible entrypoint"}, "elapsed_s": float(time.time() - t0)}
        except Exception as e:
            _fx(hooks, "instrument_error", instrument="hilbert_engine", err=str(e))
            return {"kind": "hilbert", "trace": {"error": str(e)}, "elapsed_s": float(time.time() - t0), "fallback": True}

    def lenses(self, value_sigma: np.ndarray, *, hooks: RecordHooks, ttl_ok: bool) -> Dict[str, Any]:
        if not ttl_ok:
            return {"kind": "bias_lenses", "bundle": {"note": "bias_lenses disabled or ttl exceeded"}}
        try:
            import bias_lenses as bl  # type: ignore
            if hasattr(bl, "dream_probe_bundle"):
                out = bl.dream_probe_bundle(value_sigma)
                _fx(hooks, "instrument", instrument="bias_lenses", note="dream_probe_bundle")
                return {"kind": "bias_lenses", "bundle": out}
            _fx(hooks, "instrument", instrument="bias_lenses", note="present_no_bundle")
            return {"kind": "bias_lenses", "bundle": {"note": "bias_lenses present but no dream_probe_bundle"}}
        except Exception as e:
            _fx(hooks, "instrument_error", instrument="bias_lenses", err=str(e))
            return {"kind": "bias_lenses", "bundle": {"error": str(e)}, "fallback": True}

    # ---- Verdict composition
    def compose_verdict(
        self,
        *,
        eden_integrity: str,
        gs: Dict[str, Any],
        dom_sigma: Optional[Any],
    ) -> Tuple[str, List[str]]:
        verdict = "ADVICE"
        why: List[str] = []

        if eden_integrity == "unknown":
            verdict = "DOWNGRADE"
            why.append("Eden integrity=unknown (witness incomplete).")

        shimmer_status = gs.get("shimmer_status", "unknown")

        if shimmer_status == "high":
            verdict = "DOWNGRADE"
            why.append("Shimmer high: curvature/oscillation dominates; prefer reversibility + re-measure.")

        if dom_sigma is not None and _safe_float(dom_sigma, 0.0) > self.policy.dominant_sigma_downgrade:
            verdict = "DOWNGRADE"
            why.append("Dominant pole sigma high: uncertainty too large for strong advice.")

        if verdict == "ADVICE" and gs.get("metal_metrics_available") and shimmer_status == "low":
            why.append("Metal metrics present; shimmer low permits firmer bounded guidance.")
        elif verdict == "ADVICE" and not gs.get("metal_metrics_available"):
            why.append("No metal metrics capsule detected; advice bounded to direct VALUE/SIGMA observations.")

        return verdict, why

    # ---- Core consult
    def turn(
        self,
        value_sigma_or_bundle: Any,
        *,
        eden_packet: Optional[Mapping[str, Any]] = None,
        instruments: Tuple[str, ...] = ("hilbert_engine", "bias_lenses"),
        context: Optional[Dict[str, Any]] = None,
        hooks: RecordHooks = RecordHooks(),
        budget_ttl_s: int = 20,
        metal_capsule: Optional[Dict[str, Any]] = None,
        hilbert_trace: Optional[Any] = None,
    ) -> Dict[str, Any]:
        t0 = time.time()
        run_id = f"oracle_{_sha16(_now_utc_iso(), str(context or {}))}"
        integrity = self.eden_integrity(eden_packet)
        triad = self.eden_triad(eden_packet)

        trace: Dict[str, Any] = {
            "oracle_run_id": run_id,
            "ts_utc": _now_utc_iso(),
            "eden": {"integrity": integrity, **triad},
            "context": dict(context or {}),
            "instruments": list(instruments),
            "budget_ttl_s": int(budget_ttl_s),
        }

        _fx(hooks, "begin", oracle_run_id=run_id, eden_integrity=integrity, context=trace["context"], instruments=trace["instruments"])

        if integrity == "fail":
            _fx(hooks, "refuse", reason="eden_integrity_fail")
            return {
                "oracle_version": VERSION,
                "oracle_run_id": run_id,
                "ts_utc": trace["ts_utc"],
                "boss": {
                    "metal_metrics_available": False,
                    "glimmer_shimmer_status": "unknown",
                    "result": "REFUSE",
                    "why": "Eden witness integrity=fail; Oracle will not interpret.",
                },
                "answer_text": (
                    "ORACLE (REFUSE)\n"
                    "- Eden witness integrity=fail.\n"
                    "- I will not interpret failed or non-witnessed artifacts.\n"
                ),
                "trace": trace,
            }

        value_sigma = self.as_np_value_sigma(value_sigma_or_bundle)
        if value_sigma is None:
            _fx(hooks, "silence", reason="no_value_sigma")
            return {
                "oracle_version": VERSION,
                "oracle_run_id": run_id,
                "ts_utc": trace["ts_utc"],
                "boss": {
                    "metal_metrics_available": False,
                    "glimmer_shimmer_status": "unknown",
                    "result": "SILENCE",
                    "why": "No resolvable (64,64,64,2) VALUE/SIGMA sheet present.",
                },
                "answer_text": (
                    "ORACLE (SILENCE)\n"
                    "- No resolvable VALUE/SIGMA tensor found in RAM object.\n"
                    "- I will not guess.\n"
                ),
                "trace": trace,
            }

        if isinstance(metal_capsule, dict):
            caps = [metal_capsule]
        else:
            caps = self.extract_metal_capsules(value_sigma_or_bundle)

        gs = self.gs_status_from_capsules(caps)
        trace["measured_metrics"] = gs.get("capsule") if gs.get("metal_metrics_available") else None

        if isinstance(hilbert_trace, dict):
            hilbert_used = {"kind": "hilbert_trace_observed", "trace": hilbert_trace}
            _fx(hooks, "instrument", instrument="hilbert_trace_observed", note="explicit_arg")
        else:
            observed = self.find_hilbert_trace_in_bundle(value_sigma_or_bundle)
            if isinstance(observed, dict):
                hilbert_used = {"kind": "hilbert_trace_observed", "trace": observed}
                _fx(hooks, "instrument", instrument="hilbert_trace_observed", note="bundle_search")
            else:
                ttl_ok = (time.time() - t0) <= budget_ttl_s
                hilbert_used = self.hilbert(value_sigma, hooks=hooks, ttl_ok=("hilbert_engine" in instruments and ttl_ok))

        ttl_ok = (time.time() - t0) <= budget_ttl_s
        lenses_used = self.lenses(value_sigma, hooks=hooks, ttl_ok=("bias_lenses" in instruments and ttl_ok))

        v = value_sigma[..., CH_VALUE]
        s = value_sigma[..., CH_SIGMA]
        sigma_pressure = float(np.mean(s > self.policy.sigma_pressure_threshold))
        risk_shadow = float(np.mean((s > self.policy.sigma_pressure_threshold) & (v < self.policy.risk_shadow_value_cut)))

        hilbert_summary = _hilbert_summary(hilbert_used.get("trace"))
        dominant_pole = hilbert_summary["dominant_pole"]
        entropy_v = hilbert_summary["entropy"]
        dom_sigma = hilbert_summary["dominant_sigma"]

        verdict, why = self.compose_verdict(eden_integrity=integrity, gs=gs, dom_sigma=dom_sigma)

        boss: Dict[str, Any] = {
            "metal_metrics_available": bool(gs.get("metal_metrics_available")),
            "glimmer_core": gs.get("glimmer_core"),
            "shimmer_core": gs.get("shimmer_core"),
            "shimmer_spec": gs.get("shimmer_spec"),
            "ash_residual": gs.get("ash_residual"),
            "glimmer_status": gs.get("glimmer_status", "unknown"),
            "shimmer_status": gs.get("shimmer_status", "unknown"),
            "result": verdict,
            "why": " ".join(why) if why else "Bounded advice based on available evidence.",
        }

        metal_yesno = "yes" if gs.get("metal_metrics_available") else "no"
        lines: List[str] = []
        lines.append(f"ORACLE 2.8 ({verdict}; RAM-only)")
        lines.append("")
        lines.append("BOSS-FACING STATUS")
        lines.append(f"  - Metal metrics available: {metal_yesno}")
        lines.append(f"  - Glimmer/Shimmer: glimmer={boss['glimmer_status']} shimmer={boss['shimmer_status']}")
        if gs.get("metal_metrics_available"):
            lines.append(f"    glimmer_core={boss['glimmer_core']} shimmer_core={boss['shimmer_core']} ash_residual={boss['ash_residual']}")
            if boss.get("shimmer_spec") is not None:
                lines.append(f"    shimmer_spec={boss['shimmer_spec']}")
        lines.append(f"  - Result: {verdict} — {boss['why']}")
        lines.append("")
        lines.append("EVIDENCE (Observed, not asserted)")
        lines.append(f"  - Sigma pressure: {sigma_pressure:.3f} | Risk shadow: {risk_shadow:.3f}")
        if dominant_pole != "unknown":
            lines.append(f"  - Hilbert dominant pole: {dominant_pole}")
        if hilbert_summary.get("identity_fraction") is not None:
            lines.append(f"  - Identity fraction: {hilbert_summary['identity_fraction']}")
        if hilbert_summary.get("residual_fraction") is not None:
            lines.append(f"  - Residual fraction: {hilbert_summary['residual_fraction']}")
        if hilbert_summary.get("knowledge_fraction") is not None:
            lines.append(f"  - Knowledge fraction: {hilbert_summary['knowledge_fraction']}")
        if hilbert_summary.get("coherence") is not None:
            lines.append(f"  - Hilbert coherence: {hilbert_summary['coherence']}")
        if hilbert_summary.get("residue") is not None:
            lines.append(f"  - Hilbert residue: {hilbert_summary['residue']}")
        if entropy_v is not None:
            lines.append(f"  - Hilbert entropy: {entropy_v}")
        if dom_sigma is not None:
            lines.append(f"  - Hilbert dominant sigma: {dom_sigma}")
        if hilbert_summary.get("backend") is not None:
            lines.append(f"  - Hilbert backend: {hilbert_summary['backend']}")
        lines.append("")
        lines.append("ADVISEMENT (Advice ≠ Authority)")
        if verdict == "ADVICE":
            lines.append("  - Choose ONE small reversible action that tests the current projection.")
            lines.append("  - Re-measure next loop; treat improvements as evidence, not proof.")
            if gs.get("metal_metrics_available") and boss["shimmer_status"] == "low":
                lines.append("  - Shimmer low → you may tighten the action-window slightly (still reversible).")
        else:
            lines.append("  - Downgrade: do not commit irreversible moves.")
            lines.append("  - Prefer reversible action + re-measurement; request another witnessed sample.")
            if boss["shimmer_status"] == "high":
                lines.append("  - Shimmer high → expect surprise if you overfit a single future.")
        lines.append("")
        lines.append("HOW TO CONSULT AGAIN (same venv)")
        lines.append("  import projection_oracle as po")
        lines.append("  print(po.oracle_task_menu())")
        lines.append("  reading = po.oracle_turn(block_or_bundle, eden_packet=eden, instruments=(\"hilbert_engine\",\"bias_lenses\"))")

        answer_text = "\n".join(lines)

        out: Dict[str, Any] = {
            "oracle_version": VERSION,
            "oracle_run_id": run_id,
            "ts_utc": trace["ts_utc"],
            "boss": boss,
            "hilbert": {
                "kind": hilbert_used.get("kind"),
                "dominant_pole": dominant_pole,
                "identity_fraction": hilbert_summary.get("identity_fraction"),
                "residual_fraction": hilbert_summary.get("residual_fraction"),
                "knowledge_fraction": hilbert_summary.get("knowledge_fraction"),
                "coherence": hilbert_summary.get("coherence"),
                "residue": hilbert_summary.get("residue"),
                "backend": hilbert_summary.get("backend"),
                "projection_state": hilbert_summary.get("projection_state"),
                "modal_summary": hilbert_summary.get("modal_summary"),
                "trace": hilbert_used.get("trace"),
            },
            "lenses": lenses_used,
            "observations": {
                "sigma_pressure": sigma_pressure,
                "risk_shadow": risk_shadow,
            },
            "answer_text": answer_text,
            "trace": trace,
        }

        _fx(hooks, "compose", verdict=verdict, metal=bool(gs.get("metal_metrics_available")), shimmer_status=boss["shimmer_status"], glimmer_status=boss["glimmer_status"])
        _fx(hooks, "end", ok=True, verdict=verdict, elapsed_s=float(time.time() - t0))
        return out


# ─────────────────────────────────────────────────────────────────────────────
# Public seam functions (thin wrappers around class instance)
# ─────────────────────────────────────────────────────────────────────────────
_DEFAULT_ORACLE = ProjectionOracle()


def oracle_task_menu() -> str:
    return (
        "PROJECTION ORACLE — TASK MENU (2.8)\n"
        "  A) Read metal metrics: glimmer/shimmer/ash as measured evidence\n"
        "  B) Hilbert triangle (or metal hilbert trace when present)\n"
        "  C) Bias lenses bundle (deterministic probes)\n"
        "  D) Advice vs Downgrade with sigma + shimmer discipline\n"
        "\n"
        "In-venv consult:\n"
        "  import projection_oracle as po\n"
        "  oracle = po.oracle_turn(block_or_bundle, eden_packet=eden, instruments=(...))\n"
    )


def oracle_emit_invitation(ctx: Optional[Dict[str, Any]] = None, hooks: RecordHooks = RecordHooks()) -> None:
    ctx = dict(ctx or {})
    print("<> THE CRYSTAL OPENS (Projection Oracle) <>")
    print("- Metal-first: I read measured metrics if present.")
    print("- RAM-only: I do not write. I do not remember. I do not command.")
    print("- Witness obedient: I refuse on integrity fail; I downgrade on unknown.\n")
    print("Quick consult (inside this venv):")
    print("  import projection_oracle as po")
    print("  print(po.oracle_task_menu())")
    print("  reading = po.oracle_turn(block_or_bundle, eden_packet=eden, instruments=(\"hilbert_engine\",\"bias_lenses\"))\n")
    _fx(hooks, "invitation", ts_utc=_now_utc_iso(), ctx=ctx)


def oracle_reading_fingerprint(reading: Mapping[str, Any]) -> str:
    core = {
        "oracle_version": str(reading.get("oracle_version", "")),
        "result": reading.get("boss", {}).get("result"),
        "metal": reading.get("boss", {}).get("metal_metrics_available"),
        "glimmer": reading.get("boss", {}).get("glimmer_core"),
        "shimmer": reading.get("boss", {}).get("shimmer_core"),
        "dominant": reading.get("hilbert", {}).get("dominant_pole"),
    }
    return hashlib.sha256(repr(core).encode("utf-8")).hexdigest()


def oracle_turn(
    value_sigma_or_bundle: Any,
    *,
    eden_packet: Optional[Mapping[str, Any]] = None,
    instruments: Tuple[str, ...] = ("hilbert_engine", "bias_lenses"),
    context: Optional[Dict[str, Any]] = None,
    hooks: RecordHooks = RecordHooks(),
    budget_ttl_s: int = 20,
    metal_capsule: Optional[Dict[str, Any]] = None,
    hilbert_trace: Optional[Any] = None,
) -> Dict[str, Any]:
    return _DEFAULT_ORACLE.turn(
        value_sigma_or_bundle,
        eden_packet=eden_packet,
        instruments=instruments,
        context=context,
        hooks=hooks,
        budget_ttl_s=budget_ttl_s,
        metal_capsule=metal_capsule,
        hilbert_trace=hilbert_trace,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Minimal self-check lane (no persistence)
# ─────────────────────────────────────────────────────────────────────────────
def _self_check() -> Dict[str, Any]:
    rng = np.random.default_rng(0)
    arr = np.zeros(PI_SHAPE, dtype=np.float32)
    arr[..., CH_VALUE] = _clip01(rng.normal(0.50, 0.08, PI_SHAPE[:3])).astype(np.float32)
    arr[..., CH_SIGMA] = 0.5

    capsule = {
        "backend": "rust",
        "glimmer_core": 0.45,
        "shimmer_core": 0.88,  # high shimmer → DOWNGRADE expected
        "shimmer_spec": [0.20, 0.35, 0.45],
        "ash_residual": 0.12,
        "provenance": {"signature": "aurora_cortex"},
    }

    eden_ok = {"integrity": "pass", "declared": {"note": "demo"}, "observed": {"note": "demo"}, "unknown": {}}

    oracle = ProjectionOracle()
    reading = oracle.turn(
        {"value_sigma": arr, "metrics": capsule, "trace": {"hilbert": {"instrument": "hilbert_engine", "observed": {"backend": "rust", "projection_state": {"identity_fraction": 0.61, "residual_fraction": 0.39, "knowledge_fraction": 0.55}, "coherence": 0.73, "residue": 0.22}, "unknown": {"source": "rust"}}}},
        eden_packet=eden_ok,
        instruments=("hilbert_engine", "bias_lenses"),
        metal_capsule=capsule,
        context={"phase": "self_check"},
        budget_ttl_s=5,
    )
    return reading


if __name__ == "__main__":
    print(oracle_task_menu())
    demo = _self_check()
    print("\n--- SELF CHECK (excerpt) ---")
    print(demo.get("answer_text", "")[:900])
