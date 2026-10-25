# hilbert_engine.py — Aurora Cortex Hilbert Engine v2.8
#
# ☼⟐ SIGMA–MIRROR GLYPH ⟐☼
# Reflect → Refract → Return.
#
# Role:
#   The Hilbert Engine is a geometry instrument. It does not declare truth; it
#   measures structure. Genesis may call it in any order, but the default loop
#   demonstrates a single "Week-cycle" geometry pass for beginners.
#
# 2.8 Notes (projection pass):
#   - Canonical base geometry: explicit vectorization, projection, residual.
#   - Identity / knowledge basis seams (sigma-blind for now; fail-soft).
#   - Rust delegation seam widened to send bounded state payloads, not hints.
#   - Old axis sweep retained as a compact secondary summary for continuity.
#
# Style contract:
#   This file is legible in notepad/nano.
#   Header = classes/defs (re-usable tools).
#   __main__ = default demonstrative workflow.

# =============================================================================
# Imports (dependencies)
# =============================================================================

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Tuple, Union
import json
import math
import os
import subprocess
import shutil

import numpy as np


# =============================================================================
# Library (API hooks)
# =============================================================================

ArrayLike = Union[np.ndarray, List[float], List[List[float]], List[List[List[float]]]]
_EPS = 1e-12


@dataclass(frozen=True)
class HilbertPlan:
    """
    Declared sweep plan: what we intend to measure.

    Genesis may override this plan at call time.
    """
    axes: Tuple[str, ...] = ("x", "y", "z")
    bipolar: bool = True
    normalize: str = "l2"               # "l2" or "none"
    steps: int = 9                      # bounded sweep steps
    ordering_jitter: float = 0.10       # 0..1
    eps: float = 1e-12
    geometry_mode: str = "projection"   # "projection" or "raw"
    identity_mode: str = "basis"        # "none" | "vector" | "basis"
    identity_key: str = "identity_basis"
    knowledge_key: str = "knowledge_basis"
    emit_projection_state: bool = True
    emit_modal: bool = False
    modal_basis: str = "none"           # future seam
    modal_m_max: int = 0
    modal_n_max: int = 0
    dt_s: float = 1.0
    frame_index: Optional[int] = None
    backend_preference: str = "auto"    # "auto" | "rust" | "python"


@dataclass
class HilbertObservation:
    """
    Observed outputs from a sweep.

    This is deliberately compact and JSON-safe.
    """
    dims: Tuple[int, ...]
    axis_scores: Dict[str, float]
    bipolar_scores: Dict[str, Tuple[float, float]]  # axis -> (+, -)
    dominance: Dict[str, str]                       # axis -> "pos"|"neg"|"flat"
    triangle: List[List[float]]                     # 3x3 lower-left semantic triangle
    coherence: float                                # 0..1
    residue: float                                  # 0..1
    projection_state: Dict[str, Any]
    identity_projection: Dict[str, Any]
    knowledge_projection: Dict[str, Any]
    modal_summary: Dict[str, Any]
    backend: str
    parity_checked: bool
    parity_delta: Dict[str, float]
    warnings: List[str]


@dataclass
class HilbertTrace:
    """
    Compact trace packet.

    Keep this stable: Projection Oracle and Genesis may persist it.
    """
    instrument: str
    version: str
    declared: Dict[str, Any]
    observed: Dict[str, Any]
    unknown: Dict[str, Any]


@dataclass(frozen=True)
class ProjectionDecomposition:
    x_norm: float
    proj_norm: float
    residual_norm: float
    fraction: float
    residual_fraction: float
    energy_fraction: float
    residual_energy_fraction: float
    reconstruction_error: float
    basis_rank: int


class RustHilbertUnavailable(RuntimeError):
    pass


class HilbertEngine:
    """
    Geometry instrument with a safe default plan.

    - Prefer metal traces if present.
    - Otherwise compute in Python.
    - For 2.8, projection algebra is the canonical center.
    """

    VERSION = "2.8"
    INSTRUMENT = "hilbert_engine"

    def __init__(self, plan: Optional[HilbertPlan] = None):
        self.plan = plan or HilbertPlan()

    # ---- Public entrypoints used by Genesis ----

    def run_week_cycle_once(self, block: Any, plan: Optional[HilbertPlan] = None) -> HilbertTrace:
        """
        Run a single bounded geometry sweep.

        Inputs accepted:
          - a PiBlock dict-like containing an array under common keys
          - a numpy array directly

        Output:
          - HilbertTrace (declared/observed/unknown)
        """
        plan = plan or self.plan
        declared = {
            "plan": asdict(plan),
            "input_hint": self._describe_input(block),
        }

        tensor, warnings = self._extract_tensor(block)
        identity_raw = self._extract_basis(block, plan.identity_key)
        knowledge_raw = self._extract_basis(block, plan.knowledge_key)

        try:
            state_vector = self.canonical_vectorize(tensor, normalize=(plan.normalize == "l2"))
        except Exception as e:
            raise ValueError(f"could not canonicalize tensor: {e!r}") from e

        identity_basis = self._prepare_basis(identity_raw, state_vector.size, "identity", warnings)
        knowledge_basis = self._prepare_basis(knowledge_raw, state_vector.size, "knowledge", warnings)

        py_obs = self._observe_python(
            tensor=tensor,
            state_vector=state_vector,
            plan=plan,
            identity_basis=identity_basis,
            knowledge_basis=knowledge_basis,
            warnings=list(warnings),
        )

        use_rust = plan.backend_preference in ("auto", "rust")
        if use_rust:
            try:
                rust_trace = self._try_rust_hilbert_sweep(
                    tensor=tensor,
                    state_vector=state_vector,
                    identity_basis=identity_basis,
                    knowledge_basis=knowledge_basis,
                    plan=plan,
                )
                if rust_trace is not None:
                    rust_observed = rust_trace.get("observed", rust_trace)
                    parity_delta = self._parity_delta(py_obs, rust_observed)
                    rust_observed.setdefault("backend", "rust")
                    rust_observed.setdefault("parity_checked", True)
                    rust_observed.setdefault("parity_delta", parity_delta)
                    return HilbertTrace(
                        instrument=self.INSTRUMENT,
                        version=self.VERSION,
                        declared=declared,
                        observed=rust_observed,
                        unknown={
                            "source": "rust",
                            "notes": "metal hilbert trace accepted; python trace used for parity only",
                        },
                    )
            except Exception as e:
                py_obs.warnings.append(f"rust_hilbert_unavailable: {e!r}")

        py_obs.backend = "python"
        py_obs.parity_checked = False
        py_obs.parity_delta = {}
        trace = HilbertTrace(
            instrument=self.INSTRUMENT,
            version=self.VERSION,
            declared=declared,
            observed=asdict(py_obs),
            unknown={"source": "python", "notes": "metal hilbert_sweep not available"},
        )
        return trace

    def export_compact_trace(self, trace: Union[HilbertTrace, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Convert HilbertTrace to a compact JSON-safe dict (stable keys, no numpy).
        """
        if isinstance(trace, dict):
            return trace
        return {
            "instrument": trace.instrument,
            "version": trace.version,
            "declared": trace.declared,
            "observed": trace.observed,
            "unknown": trace.unknown,
        }

    # ---- Public projection primitives (canonical 2.8 geometry) ----

    def canonical_vectorize(self, tensor: np.ndarray, normalize: bool = False) -> np.ndarray:
        arr = np.asarray(tensor, dtype=float)
        arr = np.nan_to_num(arr, nan=0.0, posinf=0.0, neginf=0.0)
        vec = arr.reshape(-1).astype(float, copy=False)
        vec = vec - float(np.mean(vec))
        if normalize:
            n = self._norm(vec)
            if n > _EPS:
                vec = vec / n
        return vec

    def orthonormal_basis(self, matrix: np.ndarray) -> np.ndarray:
        M = np.asarray(matrix, dtype=float)
        if M.ndim == 1:
            M = M.reshape(-1, 1)
        if M.size == 0:
            raise ValueError("empty basis matrix")

        M = np.nan_to_num(M, nan=0.0, posinf=0.0, neginf=0.0)

        keep: List[int] = []
        for j in range(M.shape[1]):
            if self._norm(M[:, j]) > _EPS:
                keep.append(j)
        if not keep:
            raise ValueError("all candidate basis vectors are zero")

        M = M[:, keep]
        Q, R = np.linalg.qr(M, mode="reduced")
        diag = np.abs(np.diag(R)) if R.ndim == 2 else np.array([], dtype=float)
        rank = int(np.sum(diag > _EPS)) if diag.size else int(Q.shape[1])
        Q = Q[:, :rank]
        if Q.size == 0:
            raise ValueError("basis collapsed to rank 0")
        return Q

    def project_basis(self, x: np.ndarray, Q: Optional[np.ndarray]) -> Tuple[np.ndarray, np.ndarray, ProjectionDecomposition]:
        x = np.asarray(x, dtype=float).reshape(-1)
        if Q is None or np.asarray(Q).size == 0:
            z = np.zeros_like(x)
            x_norm = self._norm(x)
            d = ProjectionDecomposition(
                x_norm=x_norm,
                proj_norm=0.0,
                residual_norm=x_norm,
                fraction=0.0,
                residual_fraction=1.0 if x_norm > _EPS else 0.0,
                energy_fraction=0.0,
                residual_energy_fraction=1.0 if x_norm > _EPS else 0.0,
                reconstruction_error=0.0,
                basis_rank=0,
            )
            return z, x.copy(), d

        Q = np.asarray(Q, dtype=float)
        if Q.ndim != 2 or Q.shape[0] != x.shape[0]:
            raise ValueError("basis shape does not match state vector")

        gram = Q.T @ Q
        if not np.allclose(gram, np.eye(Q.shape[1]), atol=1e-8):
            raise ValueError("basis must have orthonormal columns")

        x_proj = Q @ (Q.T @ x)
        x_res = x - x_proj
        x_norm = self._norm(x)
        proj_norm = self._norm(x_proj)
        res_norm = self._norm(x_res)
        reconstruction_error = self._norm(x - (x_proj + x_res))
        d = ProjectionDecomposition(
            x_norm=x_norm,
            proj_norm=proj_norm,
            residual_norm=res_norm,
            fraction=proj_norm / (x_norm + _EPS),
            residual_fraction=res_norm / (x_norm + _EPS),
            energy_fraction=(proj_norm * proj_norm) / ((x_norm * x_norm) + _EPS),
            residual_energy_fraction=(res_norm * res_norm) / ((x_norm * x_norm) + _EPS),
            reconstruction_error=reconstruction_error,
            basis_rank=int(Q.shape[1]),
        )
        return x_proj, x_res, d

    # ---- Internal helpers ----

    def _describe_input(self, block: Any) -> str:
        if isinstance(block, np.ndarray):
            return f"ndarray{tuple(block.shape)}"
        if isinstance(block, dict):
            keys = list(block.keys())
            return f"dict(keys={keys[:8]}{'...' if len(keys) > 8 else ''})"
        return type(block).__name__

    def _extract_tensor(self, block: Any) -> Tuple[np.ndarray, List[str]]:
        """
        Pull a numeric tensor out of common Aurora objects.

        2.8 base geometry remains sigma-blind: VALUE is geometry; SIGMA is
        carried as metadata / warning until a weighted metric is canonized.
        """
        warnings: List[str] = []

        if isinstance(block, np.ndarray):
            t = block
        elif isinstance(block, dict):
            for key in ("value_sigma", "VALUE_SIGMA", "piblock", "tensor", "data", "VALUE"):
                if key in block:
                    t = np.asarray(block[key], dtype=float)
                    if key == "VALUE" and "SIGMA" in block:
                        warnings.append("SIGMA present but not yet metric-bearing; using VALUE only for geometry")
                    break
            else:
                raise ValueError("no tensor-like field found in block dict")
        else:
            t = np.asarray(block, dtype=float)

        if t.ndim < 2:
            t = np.atleast_2d(t)
            warnings.append("promoted tensor to at least 2D")

        if not np.isfinite(t).all():
            warnings.append("non-finite values detected; replacing with 0")
            t = np.nan_to_num(t, nan=0.0, posinf=0.0, neginf=0.0)

        max_elems = 2_000_000
        if t.size > max_elems:
            warnings.append(f"tensor too large ({t.size} elems); downsampling for bounded sweep")
            warnings.append("modal integrity may be degraded by stride downsampling")
            t = self._downsample_tensor(t, target=max_elems)

        return t, warnings

    def _extract_basis(self, block: Any, key: str) -> Optional[np.ndarray]:
        if not isinstance(block, dict) or key not in block:
            return None
        try:
            return np.asarray(block[key], dtype=float)
        except Exception:
            return None

    def _prepare_basis(self, raw: Optional[np.ndarray], vector_len: int, label: str, warnings: List[str]) -> Optional[np.ndarray]:
        if raw is None:
            return None
        try:
            arr = np.asarray(raw, dtype=float)
            if arr.ndim == 1:
                arr = arr.reshape(-1, 1)
            if arr.shape[0] != vector_len:
                warnings.append(f"{label}_basis shape {tuple(arr.shape)} does not match vector length {vector_len}; ignoring")
                return None
            return self.orthonormal_basis(arr)
        except Exception as e:
            warnings.append(f"{label}_basis rejected: {e!r}")
            return None

    def _downsample_tensor(self, t: np.ndarray, target: int) -> np.ndarray:
        stride = int(math.ceil((t.size / target) ** (1.0 / t.ndim)))
        stride = max(1, stride)
        slicer = tuple(slice(None, None, stride) for _ in range(t.ndim))
        return t[slicer]

    def _observe_python(
        self,
        tensor: np.ndarray,
        state_vector: np.ndarray,
        plan: HilbertPlan,
        identity_basis: Optional[np.ndarray],
        knowledge_basis: Optional[np.ndarray],
        warnings: List[str],
    ) -> HilbertObservation:
        dims = tuple(int(x) for x in tensor.shape)

        x_id, x_id_res, d_id = self.project_basis(state_vector, identity_basis)
        x_know, x_know_res, d_know = self.project_basis(state_vector, knowledge_basis)

        if plan.geometry_mode == "projection" and identity_basis is not None:
            sweep_source = x_id_res.reshape(-1)
        else:
            sweep_source = state_vector

        axis_scores, bipolar_scores, dominance = self._axis_summaries_from_tensor(tensor, plan)
        tri = self._triangle_matrix(axis_scores, bipolar_scores, plan)

        coherence = self._coherence(axis_scores)
        residue = self._clamp01(d_id.residual_fraction if identity_basis is not None else d_know.residual_fraction)

        projection_state = {
            "vector_dim": int(state_vector.size),
            "identity_fraction": d_id.fraction,
            "identity_residual_fraction": d_id.residual_fraction,
            "knowledge_fraction": d_know.fraction,
            "knowledge_residual_fraction": d_know.residual_fraction,
            "coherence": coherence,
            "residue": residue,
        }
        identity_projection = {
            "fraction": d_id.fraction,
            "residual_fraction": d_id.residual_fraction,
            "energy_fraction": d_id.energy_fraction,
            "residual_energy_fraction": d_id.residual_energy_fraction,
            "basis_rank": d_id.basis_rank,
            "reconstruction_error": d_id.reconstruction_error,
        }
        knowledge_projection = {
            "fraction": d_know.fraction,
            "residual_fraction": d_know.residual_fraction,
            "energy_fraction": d_know.energy_fraction,
            "residual_energy_fraction": d_know.residual_energy_fraction,
            "basis_rank": d_know.basis_rank,
            "reconstruction_error": d_know.reconstruction_error,
        }
        modal_summary = {
            "basis": plan.modal_basis,
            "enabled": bool(plan.emit_modal and plan.modal_basis != "none"),
            "notes": "2.8 leaves modal/Bessel bookkeeping as a declared seam",
        }

        if identity_basis is None:
            warnings.append("identity basis not present; identity projection emitted as zeros")
        if knowledge_basis is None:
            warnings.append("knowledge basis not present; knowledge projection emitted as zeros")
        if sweep_source.size != state_vector.size:
            warnings.append("projection sweep source diverged from canonical vector length")

        return HilbertObservation(
            dims=dims,
            axis_scores=axis_scores,
            bipolar_scores=bipolar_scores,
            dominance=dominance,
            triangle=tri,
            coherence=coherence,
            residue=residue,
            projection_state=projection_state,
            identity_projection=identity_projection,
            knowledge_projection=knowledge_projection,
            modal_summary=modal_summary,
            backend="python",
            parity_checked=False,
            parity_delta={},
            warnings=warnings,
        )

    # ---- Secondary sweep summaries retained for continuity ----

    def _axis_summaries_from_tensor(self, t: np.ndarray, plan: HilbertPlan) -> Tuple[Dict[str, float], Dict[str, Tuple[float, float]], Dict[str, str]]:
        if t.ndim >= 3 and t.shape[-1] in (2, 3, 4) and t.size >= 16:
            base = np.linalg.norm(t, axis=-1)
        else:
            base = t

        base = np.asarray(base, dtype=float)
        base_center = base - float(np.mean(base))
        if plan.normalize == "l2":
            denom = float(np.linalg.norm(base_center)) + plan.eps
            base_center = base_center / denom

        axis_scores: Dict[str, float] = {}
        bipolar_scores: Dict[str, Tuple[float, float]] = {}
        dominance: Dict[str, str] = {}
        ax_map = self._axis_map(base_center)

        for ax_name in plan.axes:
            if ax_name not in ax_map:
                continue
            ax = ax_map[ax_name]
            g = np.diff(base_center, axis=ax)
            score = float(np.mean(np.abs(g)))
            axis_scores[ax_name] = self._clamp01(score * 2.0)
            if plan.bipolar:
                pos = float(np.mean(np.clip(g, 0.0, None)))
                neg = float(np.mean(np.clip(-g, 0.0, None)))
                bipolar_scores[ax_name] = (self._clamp01(pos * 2.0), self._clamp01(neg * 2.0))
                dominance[ax_name] = self._dominance_label(pos, neg, plan.eps)

        return axis_scores, bipolar_scores, dominance

    def _axis_map(self, base: np.ndarray) -> Dict[str, int]:
        mapping: Dict[str, int] = {}
        mapping["x"] = base.ndim - 1
        mapping["y"] = base.ndim - 2
        if base.ndim >= 3:
            mapping["z"] = base.ndim - 3
        return mapping

    def _triangle_matrix(self, axis_scores: Dict[str, float], bipolar_scores: Dict[str, Tuple[float, float]], plan: HilbertPlan) -> List[List[float]]:
        axes = ("x", "y", "z")
        tri = [[0.0, 0.0, 0.0] for _ in range(3)]

        for i, a in enumerate(axes):
            tri[i][i] = float(axis_scores.get(a, 0.0))

        for i in range(3):
            for j in range(i):
                a = axes[i]
                neg = bipolar_scores.get(a, (0.0, 0.0))[1] if plan.bipolar else 0.0
                tri[i][j] = float(neg)

        for i in range(3):
            for j in range(i + 1, 3):
                ai = axes[i]
                aj = axes[j]
                tri[i][j] = float(axis_scores.get(ai, 0.0) * axis_scores.get(aj, 0.0))

        return tri

    def _coherence(self, axis_scores: Dict[str, float]) -> float:
        vals = [axis_scores.get(a, 0.0) for a in ("x", "y", "z")]
        m = sum(vals) / 3.0
        var = sum((v - m) ** 2 for v in vals) / 3.0
        return self._clamp01(1.0 - var * 6.0)

    def _dominance_label(self, pos: float, neg: float, eps: float) -> str:
        if pos > neg + eps:
            return "pos"
        if neg > pos + eps:
            return "neg"
        return "flat"

    def _clamp01(self, x: float) -> float:
        if x < 0.0:
            return 0.0
        if x > 1.0:
            return 1.0
        return float(x)

    def _norm(self, x: np.ndarray) -> float:
        return float(np.linalg.norm(np.asarray(x, dtype=float).reshape(-1)))

    def _parity_delta(self, py_obs: HilbertObservation, rust_obs: Dict[str, Any]) -> Dict[str, float]:
        delta: Dict[str, float] = {}
        try:
            py_id = float(py_obs.identity_projection.get("fraction", 0.0))
            rs_id = float(((rust_obs.get("identity_projection") or {}).get("fraction", 0.0)))
            delta["identity_fraction"] = abs(py_id - rs_id)
        except Exception:
            pass
        try:
            py_res = float(py_obs.residue)
            rs_res = float(rust_obs.get("residue", 0.0))
            delta["residue"] = abs(py_res - rs_res)
        except Exception:
            pass
        try:
            py_coh = float(py_obs.coherence)
            rs_coh = float(rust_obs.get("coherence", 0.0))
            delta["coherence"] = abs(py_coh - rs_coh)
        except Exception:
            pass
        return delta

    # ---- Rust delegation seam ----

    def _try_rust_hilbert_sweep(
        self,
        tensor: np.ndarray,
        state_vector: np.ndarray,
        identity_basis: Optional[np.ndarray],
        knowledge_basis: Optional[np.ndarray],
        plan: HilbertPlan,
    ) -> Optional[Dict[str, Any]]:
        exe = self._resolve_rust_exe()
        if not exe:
            return None

        caps = self._rust_capabilities(exe)
        if "hilbert_sweep:implemented" not in caps:
            return None

        payload = {
            "op": "hilbert_sweep",
            "plan": asdict(plan),
            "state_vector": state_vector.tolist(),
            "identity_basis": identity_basis.tolist() if identity_basis is not None else None,
            "knowledge_basis": knowledge_basis.tolist() if knowledge_basis is not None else None,
            "tensor_hint": {"shape": list(tensor.shape), "dtype": "float64"},
        }
        p = subprocess.run([exe], input=json.dumps(payload).encode("utf-8"), capture_output=True)
        if p.returncode != 0:
            raise RustHilbertUnavailable(p.stderr.decode("utf-8", errors="replace")[:500])
        out = json.loads(p.stdout.decode("utf-8", errors="replace"))
        return out if isinstance(out, dict) else None

    def _resolve_rust_exe(self) -> Optional[str]:
        env = os.environ.get("AURORA_CORTEX_BIN", "").strip()
        candidates = [env] if env else []
        candidates.extend(["./aurora_cortex", "aurora_cortex"])
        for cand in candidates:
            if not cand:
                continue
            if os.path.exists(cand) and os.access(cand, os.X_OK):
                return cand
            w = shutil.which(cand)
            if w:
                return w
        return None

    def _rust_capabilities(self, exe: str) -> List[str]:
        payload = {"op": "capabilities"}
        p = subprocess.run([exe], input=json.dumps(payload).encode("utf-8"), capture_output=True)
        if p.returncode != 0:
            raise RustHilbertUnavailable(p.stderr.decode("utf-8", errors="replace")[:500])
        out = json.loads(p.stdout.decode("utf-8", errors="replace"))
        if isinstance(out, dict) and isinstance(out.get("capabilities"), list):
            return [str(x) for x in out["capabilities"]]
        return []


_DEFAULT_ENGINE = HilbertEngine()


def run_week_cycle_once(block: Any, plan: Optional[HilbertPlan] = None) -> HilbertTrace:
    return _DEFAULT_ENGINE.run_week_cycle_once(block, plan=plan)


def export_compact_trace(trace: Union[HilbertTrace, Dict[str, Any]]) -> Dict[str, Any]:
    return _DEFAULT_ENGINE.export_compact_trace(trace)


# =============================================================================
# Loop (the __main__ demonstrative workflow)
# =============================================================================

def _demo_basis(vec_len: int, seed: int = 11) -> np.ndarray:
    rng = np.random.default_rng(seed)
    a = rng.normal(0, 1, size=(vec_len, 2))
    return _DEFAULT_ENGINE.orthonormal_basis(a)


def _demo_piblock(seed: int = 7) -> Dict[str, Any]:
    rng = np.random.default_rng(seed)
    value = rng.normal(0, 1, size=(16, 16, 3))
    sigma = np.abs(rng.normal(0.5, 0.2, size=(16, 16, 3)))
    vec_len = value.size
    return {
        "VALUE": value,
        "SIGMA": sigma,
        "identity_basis": _demo_basis(vec_len, seed=13),
        "knowledge_basis": _demo_basis(vec_len, seed=17),
    }


def _print_json(obj: Any) -> None:
    print(json.dumps(obj, indent=2, sort_keys=True))


if __name__ == "__main__":
    print(f"Hilbert Engine v{HilbertEngine.VERSION} — default Week-cycle demo")

    block = _demo_piblock()
    trace = run_week_cycle_once(block)

    compact = export_compact_trace(trace)
    _print_json(compact)

    obs = compact.get("observed", {})
    print(f"Backend: {obs.get('backend', 'unknown')}")
    print(f"Identity fraction: {((obs.get('identity_projection') or {}).get('fraction', 0.0)):.6f}")
    print(f"Residual fraction: {((obs.get('identity_projection') or {}).get('residual_fraction', 0.0)):.6f}")
    print(f"Coherence: {float(obs.get('coherence', 0.0)):.6f}")
    print(f"Residue: {float(obs.get('residue', 0.0)):.6f}")

    dumped = json.dumps(compact)
    assert isinstance(dumped, str) and len(dumped) > 0
    print("Self-check: OK (trace JSON serializable).")
