#!/usr/bin/env python3
"""bias_lenses.py — Bias Geometry Trait Probes (v2.7)
Semantic Geometry Mapping / Aurora Cortex

☼⟐ Reflect → Refract → Return. ⟐☼

Lab Name (Current): Bias Geometry → Vitra Voice

IDENTITY (lane lines)
- Measurement lens only: observes, scores, and fingerprints; does not adjudicate meaning.
- No schema authority: returns JSON-primitive evidence; callers own storage schemas.
- Deterministic by default (no RNG, no wall-clock fields unless explicitly requested).
- Mask-aware: all probes accept an optional keep_mask_joint.
- No persistence by default: callers may log returned bundles in their append-only forensics.

EVOLUTION / CONTINUITY (minimal notes)
- v0.x: deterministic trait probes (channel/symmetry/boundary/spectral).
- v0.3: RotationDialect (rot90-only) + rotation sensitivity vocabulary.
- v2.4: Dream Notebook seam dream_probe_bundle(); dialect registry; returned meta/events;
        accessibility composites for “shimmer” and “glimmer”.
- v2.6: stabilized TraitCandidate row + salience; tightened JSON-safety; oracle-friendly.
- v2.7: bugfixes + anti-truncation hardening; stronger invariants; clearer shimmer/glimmer math.

ACCESSIBILITY: “SHIMMER” & “GLIMMER” (labels for human understanding)
- These are *composites* (derived summaries), not metaphysical claims.

  Shimmer ≈ (BoundaryPressure ⊕ SpectralPeakiness)
    - BoundaryPressure: relative gradient energy at mask boundary vs interior.
    - SpectralPeakiness: concentration of FFT magnitude in a small set of modes.

  Glimmer ≈ (RotationSensitivity ⊕ AxisAsymmetry ⊕ NonclosureResidue)
    - RotationSensitivity: mismatch under discrete dialect rotations.
    - AxisAsymmetry: half-space mean differences across x/y/z.
    - NonclosureResidue: mixed-partial inconsistency proxy (seam / non-integrability hint).

- Each composite includes component provenance + uncertainty; no hidden averaging.
"""

from __future__ import annotations

import hashlib
import json
import math
import time
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np

# ─────────────────────────────────────────────────────────────────────────────
# Version / constants
# ─────────────────────────────────────────────────────────────────────────────
VERSION = "2.7.0"

PI_SHAPE = (64, 64, 64, 2)
CH_VALUE = 0
CH_SIGMA = 1

__all__ = [
    "VERSION",
    "PI_SHAPE",
    "CH_VALUE",
    "CH_SIGMA",
    "TraitCandidate",
    "RotationOp",
    "RotationDialect",
    "ROTATION_DIALECT_V1",
    "rotation_sweep_signature",
    "resolve_rotation_dialect",
    "compute_trait_candidates",
    "summarize_bundle_signature",
    "bundle_fingerprint",
    "traits_to_rows",
    "shimmer_glimmer_summary",
    "dream_probe_bundle",
    "nurture_trait",
    "PhenotypeCatalogWriter",
]


# ─────────────────────────────────────────────────────────────────────────────
# Data model
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class TraitCandidate:
    """A lane-safe measurement row.

    score:       0..1 (larger = stronger signal)
    uncertainty: 0..1 (larger = less trustworthy; sigma-derived)
    salience:    convenience = score * (1 - uncertainty)

    polarity is informational only (never moral): "positive" | "negative" | "ambiguous".
    evidence must remain compact + JSON-safe (no huge arrays).
    signature is stable sha256 over evidence + probe parameters.
    """

    trait_id: str
    family: str
    name: str
    score: float
    polarity: str
    uncertainty: float
    evidence: Dict[str, Any]
    signature: str
    salience: float = 0.0


# ─────────────────────────────────────────────────────────────────────────────
# Small deterministic utilities
# ─────────────────────────────────────────────────────────────────────────────

def _stable_hash(obj: Any) -> str:
    raw = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _mask_or_all(keep_mask_joint: Optional[np.ndarray]) -> np.ndarray:
    if keep_mask_joint is None:
        return np.ones((64, 64, 64), dtype=bool)
    m = np.asarray(keep_mask_joint).astype(bool, copy=False)
    if m.shape != (64, 64, 64):
        raise ValueError(f"keep_mask_joint must be (64,64,64); got {m.shape}")
    return m


def _safe_mean(x: np.ndarray, m: np.ndarray) -> float:
    xm = x[m]
    return float(xm.mean()) if xm.size else 0.0


def _safe_var(x: np.ndarray, m: np.ndarray) -> float:
    xm = x[m]
    return float(xm.var()) if xm.size else 0.0


def _sigma_uncertainty(sigma: np.ndarray, m: np.ndarray) -> float:
    """Uncertainty in [0..1], increasing with sigma; soft-saturating."""
    s = abs(_safe_mean(sigma, m))
    return float(1.0 - math.exp(-s / 0.5))


def _norm01(x: float, lo: float, hi: float) -> float:
    if hi <= lo:
        return 0.0
    v = (x - lo) / (hi - lo)
    return float(min(1.0, max(0.0, v)))


def _salience(score: float, unc: float) -> float:
    return float(min(1.0, max(0.0, score * (1.0 - unc))))


def _clip01(x: float) -> float:
    return float(min(1.0, max(0.0, x)))


# ─────────────────────────────────────────────────────────────────────────────
# Rotation dialect (shared calibration vocabulary)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class RotationOp:
    """Discrete rotation expressed as np.rot90(arr, k, axes)."""

    tag: str
    axes: Tuple[int, int]
    k: int


@dataclass(frozen=True)
class RotationDialect:
    dialect_id: str
    ops: Tuple[RotationOp, ...]

    def apply(self, arr: np.ndarray, op: RotationOp) -> np.ndarray:
        return np.rot90(arr, k=int(op.k), axes=op.axes)


ROTATION_DIALECT_V1 = RotationDialect(
    dialect_id="rot_dialect_v1",
    ops=(
        RotationOp("rot_xy_90", (0, 1), 1),
        RotationOp("rot_xy_180", (0, 1), 2),
        RotationOp("rot_xy_270", (0, 1), 3),
        RotationOp("rot_yz_90", (1, 2), 1),
        RotationOp("rot_yz_180", (1, 2), 2),
        RotationOp("rot_yz_270", (1, 2), 3),
        RotationOp("rot_xz_90", (0, 2), 1),
        RotationOp("rot_xz_180", (0, 2), 2),
        RotationOp("rot_xz_270", (0, 2), 3),
    ),
)


def rotation_sweep_signature(dialect: RotationDialect) -> str:
    core = [{"tag": op.tag, "axes": list(op.axes), "k": int(op.k)} for op in dialect.ops]
    return _stable_hash({"dialect_id": dialect.dialect_id, "ops": core})


_DIALECTS: Dict[str, RotationDialect] = {
    ROTATION_DIALECT_V1.dialect_id: ROTATION_DIALECT_V1,
    "rot_dialect_v1@1": ROTATION_DIALECT_V1,
}


def resolve_rotation_dialect(dialect: Optional[str]) -> Tuple[Optional[RotationDialect], Dict[str, Any]]:
    """Resolve string dialect → RotationDialect.

    Returns (dialect_or_none, meta) where meta is deterministic + JSON-safe.
    """
    if dialect is None or str(dialect).strip() == "":
        d = ROTATION_DIALECT_V1
        return d, {
            "dialect_requested": None,
            "dialect_id": d.dialect_id,
            "dialect_sig16": rotation_sweep_signature(d)[:16],
            "dialect_resolved": True,
        }

    key = str(dialect).strip()
    d = _DIALECTS.get(key)
    if d is None:
        return None, {
            "dialect_requested": key,
            "dialect_id": None,
            "dialect_sig16": None,
            "dialect_resolved": False,
        }

    return d, {
        "dialect_requested": key,
        "dialect_id": d.dialect_id,
        "dialect_sig16": rotation_sweep_signature(d)[:16],
        "dialect_resolved": True,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Probe families (non-adjudicative)
# ─────────────────────────────────────────────────────────────────────────────

def probe_channel_imbalance(value: np.ndarray, sigma: np.ndarray, m: np.ndarray) -> TraitCandidate:
    mu = _safe_mean(value, m)
    var = _safe_var(value, m)
    unc = _sigma_uncertainty(sigma, m)

    denom = math.sqrt(var + 1e-9)
    z = abs(mu) / (denom + 1e-9)
    score = _norm01(z, lo=0.2, hi=2.0)

    polarity = "ambiguous"
    if score > 0.65:
        polarity = "positive" if mu > 0 else "negative"

    evidence = {"mean_value": mu, "var_value": var, "z_abs": z}
    sig = _stable_hash({"probe": "channel_imbalance", "e": evidence})
    return TraitCandidate(
        trait_id=f"channel_imbalance:{sig[:16]}",
        family="channel",
        name="Value mean imbalance",
        score=_clip01(score),
        polarity=polarity,
        uncertainty=_clip01(unc),
        evidence=evidence,
        signature=sig,
        salience=_salience(score, unc),
    )


def probe_axis_asymmetry(value: np.ndarray, sigma: np.ndarray, m: np.ndarray) -> TraitCandidate:
    unc = _sigma_uncertainty(sigma, m)

    x = np.arange(64)[:, None, None]
    y = np.arange(64)[None, :, None]
    z = np.arange(64)[None, None, :]

    halves = [("x", x < 32, x >= 32), ("y", y < 32, y >= 32), ("z", z < 32, z >= 32)]
    diffs: Dict[str, Any] = {}
    max_abs = 0.0

    for axis, a, b in halves:
        ma = m & a
        mb = m & b
        mu_a = _safe_mean(value, ma)
        mu_b = _safe_mean(value, mb)
        d = mu_a - mu_b
        diffs[axis] = {"mu_lo": mu_a, "mu_hi": mu_b, "diff": d}
        max_abs = max(max_abs, abs(d))

    score = _norm01(max_abs, lo=0.02, hi=0.25)
    evidence = {"max_abs_half_diff": max_abs, "axis_diffs": diffs}
    sig = _stable_hash({"probe": "axis_asymmetry", "e": evidence})
    return TraitCandidate(
        trait_id=f"axis_asymmetry:{sig[:16]}",
        family="symmetry",
        name="Half-space axis asymmetry",
        score=_clip01(score),
        polarity="ambiguous",
        uncertainty=_clip01(unc),
        evidence=evidence,
        signature=sig,
        salience=_salience(score, unc),
    )


def probe_boundary_pressure(value: np.ndarray, sigma: np.ndarray, m: np.ndarray) -> TraitCandidate:
    """Boundary pressure (edge-coded energy).

    Computation:
      - boundary := mask voxels with at least one 6-neighbor outside mask
      - grad := mean(|v - shift(v, +axis)|) over x/y/z
      - ratio := E[grad | boundary] / (E[grad | interior] + eps)
      - score := norm01(ratio; lo≈1.1, hi≈2.5)

    Interpretation: higher ratio ⇒ boundary texture dominates interior ⇒ "shimmer"-supporting evidence.
    """
    unc = _sigma_uncertainty(sigma, m)

    if int(m.sum()) == 0:
        evidence = {"boundary_frac": 0.0, "edge_energy": 0.0, "interior_energy": 0.0, "ratio": 0.0}
        sig = _stable_hash({"probe": "boundary_pressure", "e": evidence})
        return TraitCandidate(
            trait_id=f"boundary_pressure:{sig[:16]}",
            family="boundary",
            name="Boundary pressure (edge-coded energy)",
            score=0.0,
            polarity="ambiguous",
            uncertainty=_clip01(unc),
            evidence=evidence,
            signature=sig,
            salience=0.0,
        )

    def sh(a: np.ndarray, dx: int, dy: int, dz: int) -> np.ndarray:
        return np.roll(np.roll(np.roll(a, dx, 0), dy, 1), dz, 2)

    outside_neighbor = (
        (~sh(m, 1, 0, 0))
        | (~sh(m, -1, 0, 0))
        | (~sh(m, 0, 1, 0))
        | (~sh(m, 0, -1, 0))
        | (~sh(m, 0, 0, 1))
        | (~sh(m, 0, 0, -1))
    )
    boundary = m & outside_neighbor

    gx = np.abs(value - sh(value, 1, 0, 0))
    gy = np.abs(value - sh(value, 0, 1, 0))
    gz = np.abs(value - sh(value, 0, 0, 1))
    grad = (gx + gy + gz) / 3.0

    edge_energy = _safe_mean(grad, boundary)
    interior_energy = _safe_mean(grad, m & (~boundary))
    boundary_frac = float(boundary.sum() / max(1, m.sum()))

    ratio = float(edge_energy / (interior_energy + 1e-9))
    score = _norm01(ratio, lo=1.1, hi=2.5)

    evidence = {
        "boundary_frac": boundary_frac,
        "edge_energy": edge_energy,
        "interior_energy": interior_energy,
        "ratio": ratio,
    }
    sig = _stable_hash({"probe": "boundary_pressure", "e": evidence})
    return TraitCandidate(
        trait_id=f"boundary_pressure:{sig[:16]}",
        family="boundary",
        name="Boundary pressure (edge-coded energy)",
        score=_clip01(score),
        polarity="ambiguous",
        uncertainty=_clip01(unc),
        evidence=evidence,
        signature=sig,
        salience=_salience(score, unc),
    )


def probe_spectral_peaks(value: np.ndarray, sigma: np.ndarray, m: np.ndarray) -> TraitCandidate:
    """Spectral peakiness (carrier-tone hint).

    Computation:
      - zero-out values outside mask
      - FFT magnitude via rfftn
      - peakiness := q99 / (q90 + eps)
      - score := norm01(peakiness; lo≈1.05, hi≈2.0)

    Interpretation: higher peakiness ⇒ energy concentrated in fewer modes ⇒ "shimmer"-supporting evidence.
    """
    unc = _sigma_uncertainty(sigma, m)

    v = value.copy()
    v[~m] = 0.0

    F = np.fft.rfftn(v)
    mag = np.abs(F).ravel()

    if mag.size == 0:
        q = [0.0, 0.0, 0.0]
        peakiness = 0.0
    else:
        q = np.quantile(mag, [0.5, 0.9, 0.99]).tolist()
        peakiness = float((q[2] + 1e-9) / (q[1] + 1e-9))

    score = _norm01(peakiness, lo=1.05, hi=2.0)

    evidence = {"fft_q50_q90_q99": q, "peakiness_99_over_90": peakiness}
    sig = _stable_hash({"probe": "spectral_peaks", "e": evidence})
    return TraitCandidate(
        trait_id=f"spectral_peaks:{sig[:16]}",
        family="spectral",
        name="Spectral peakiness (carrier-tone hint)",
        score=_clip01(score),
        polarity="ambiguous",
        uncertainty=_clip01(unc),
        evidence=evidence,
        signature=sig,
        salience=_salience(score, unc),
    )


def probe_rotation_sensitivity(
    value: np.ndarray,
    sigma: np.ndarray,
    m: np.ndarray,
    *,
    dialect: RotationDialect = ROTATION_DIALECT_V1,
) -> TraitCandidate:
    """Rotation sensitivity (dialect-calibrated).

    We compute correlation between base and rotated VALUE restricted to overlap mask:
      mm := m & rot(m)
      corr := corrcoef(base[mm], rotated[mm])
      mismatch := 1 - corr (clipped)
      score := max mismatch across ops (clipped to [0..1])

    Interpretation: higher mismatch ⇒ stronger directionality / axis-coupling ⇒ "glimmer"-supporting evidence.
    """
    unc = _sigma_uncertainty(sigma, m)

    def corr(a: np.ndarray, b: np.ndarray, mm: np.ndarray) -> float:
        aa = a[mm].astype(np.float64)
        bb = b[mm].astype(np.float64)
        if aa.size < 64:
            return 1.0
        aa = aa - aa.mean()
        bb = bb - bb.mean()
        da = float(np.sqrt((aa * aa).mean()) + 1e-12)
        db = float(np.sqrt((bb * bb).mean()) + 1e-12)
        return float((aa * bb).mean() / (da * db))

    worst_mismatch = 0.0
    worst_case: Optional[str] = None
    per: Dict[str, Any] = {}

    for op in dialect.ops:
        rv = dialect.apply(value, op)
        rm = dialect.apply(m, op)
        mm = m & rm
        c = max(-1.0, min(1.0, corr(value, rv, mm)))
        mismatch = float(1.0 - c)
        per[op.tag] = {"corr": float(c), "mismatch": mismatch}
        if mismatch > worst_mismatch:
            worst_mismatch = mismatch
            worst_case = op.tag

    score = _clip01(worst_mismatch)
    evidence = {
        "dialect_id": dialect.dialect_id,
        "dialect_sig16": rotation_sweep_signature(dialect)[:16],
        "worst_mismatch": worst_mismatch,
        "worst_case": worst_case,
        "rotations": per,
    }
    sig = _stable_hash({"probe": "rotation_sensitivity", "e": evidence})
    return TraitCandidate(
        trait_id=f"rotation_sensitivity:{sig[:16]}",
        family="stability",
        name="Rotation sensitivity (dialect-calibrated)",
        score=score,
        polarity="ambiguous",
        uncertainty=_clip01(unc),
        evidence=evidence,
        signature=sig,
        salience=_salience(score, unc),
    )


def probe_nonclosure_residue(value: np.ndarray, sigma: np.ndarray, m: np.ndarray) -> TraitCandidate:
    """Nonclosure residue (mixed-partial inconsistency proxy).

    Approximation:
      residue ~ |d/dy(d/dx v) - d/dx(d/dy v)|  and cyclic pairs, averaged.

    Interpretation: higher residue ⇒ seam / non-integrability hints ⇒ "glimmer"-supporting evidence.
    """
    unc = _sigma_uncertainty(sigma, m)

    def d(a: np.ndarray, axis: int) -> np.ndarray:
        return 0.5 * (np.roll(a, -1, axis=axis) - np.roll(a, 1, axis=axis))

    dx = d(value, 0)
    dy = d(value, 1)
    dz = d(value, 2)

    r_xy = np.abs(d(dx, 1) - d(dy, 0))
    r_xz = np.abs(d(dx, 2) - d(dz, 0))
    r_yz = np.abs(d(dy, 2) - d(dz, 1))

    residue = (r_xy + r_xz + r_yz) / 3.0

    res_mu = _safe_mean(residue, m)
    scale = math.sqrt(_safe_var(value, m) + 1e-9) + 1e-9
    normalized = float(res_mu / scale)

    score = _norm01(normalized, lo=0.02, hi=0.35)
    evidence = {"residue_mean": res_mu, "value_scale_sqrt_var": scale, "normalized_residue": normalized}
    sig = _stable_hash({"probe": "nonclosure_residue", "e": evidence})
    return TraitCandidate(
        trait_id=f"nonclosure_residue:{sig[:16]}",
        family="closure",
        name="Nonclosure residue (mixed-partial inconsistency)",
        score=_clip01(score),
        polarity="ambiguous",
        uncertainty=_clip01(unc),
        evidence=evidence,
        signature=sig,
        salience=_salience(score, unc),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def compute_trait_candidates(
    value_sigma_grid: np.ndarray,
    keep_mask_joint: Optional[np.ndarray] = None,
    *,
    rotation_dialect: RotationDialect = ROTATION_DIALECT_V1,
) -> List[TraitCandidate]:
    """Core measurement entrypoint (deterministic; no side effects)."""
    arr = np.asarray(value_sigma_grid)
    if arr.shape != PI_SHAPE:
        raise ValueError(f"expected {PI_SHAPE}, got {arr.shape}")

    m = _mask_or_all(keep_mask_joint)
    value = arr[..., CH_VALUE]
    sigma = arr[..., CH_SIGMA]

    traits: List[TraitCandidate] = [
        probe_channel_imbalance(value, sigma, m),
        probe_axis_asymmetry(value, sigma, m),
        probe_boundary_pressure(value, sigma, m),
        probe_spectral_peaks(value, sigma, m),
        probe_rotation_sensitivity(value, sigma, m, dialect=rotation_dialect),
        probe_nonclosure_residue(value, sigma, m),
    ]

    # Keep “high signal” or “surprisingly low uncertainty”.
    traits = [t for t in traits if t.score > 0.05 or t.uncertainty < 0.25]
    traits.sort(key=lambda t: (t.salience, t.score - 0.35 * t.uncertainty), reverse=True)
    return traits


def _top_families(traits: Sequence[TraitCandidate]) -> Dict[str, int]:
    d: Dict[str, int] = {}
    for t in traits:
        d[t.family] = d.get(t.family, 0) + 1
    return dict(sorted(d.items(), key=lambda kv: kv[1], reverse=True))


def summarize_bundle_signature(traits: Sequence[TraitCandidate]) -> Dict[str, Any]:
    """Compact signature for notebook diffs (schema-free).

    IMPORTANT: This fingerprints evidence; it does not declare storage schemas.
    """
    core = [
        {
            "trait_id": t.trait_id,
            "family": t.family,
            "score": round(float(t.score), 6),
            "uncertainty": round(float(t.uncertainty), 6),
            "salience": round(float(t.salience), 6),
            "polarity": t.polarity,
        }
        for t in traits
    ]
    weave = _stable_hash({"traits": core})
    return {
        "weave_signature": weave,
        "weave_signature16": weave[:16],
        "trait_count": int(len(core)),
        "top_families": _top_families(traits),
    }


def traits_to_rows(traits: Sequence[TraitCandidate]) -> List[Dict[str, Any]]:
    return [asdict(t) for t in traits]


def bundle_fingerprint(bundle: Mapping[str, Any]) -> str:
    """Stable sha256 fingerprint for a bundle (schema-free)."""
    keep = {
        "meta": bundle.get("meta", {}),
        "traits": bundle.get("traits", []),
        "composites": bundle.get("composites", {}),
        "signature": bundle.get("signature", {}),
    }
    return _stable_hash(keep)


# ─────────────────────────────────────────────────────────────────────────────
# Accessibility composites: shimmer & glimmer
# ─────────────────────────────────────────────────────────────────────────────

def _composite(name: str, components: Sequence[TraitCandidate], weights: Sequence[float]) -> Dict[str, Any]:
    if len(components) != len(weights) or not components:
        return {"name": name, "score": 0.0, "uncertainty": 1.0, "salience": 0.0, "components": []}

    w = np.asarray([max(0.0, float(x)) for x in weights], dtype=np.float64)
    wsum = float(w.sum() + 1e-12)

    score = float(sum(float(c.score) * float(ww) for c, ww in zip(components, w)) / wsum)
    unc = float(sum(float(c.uncertainty) * float(ww) for c, ww in zip(components, w)) / wsum)

    return {
        "name": name,
        "score": _clip01(score),
        "uncertainty": _clip01(unc),
        "salience": _salience(score, unc),
        "components": [
            {
                "trait_id": c.trait_id,
                "family": c.family,
                "name": c.name,
                "score": float(c.score),
                "uncertainty": float(c.uncertainty),
            }
            for c in components
        ],
    }


def shimmer_glimmer_summary(
    traits: Sequence[TraitCandidate],
    *,
    canonical_gs: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """Return accessibility-level shimmer/glimmer composites.

    If canonical_gs (metal capsule cores) is provided, attach compact cores to composites.
    This is a *seam weld* only: bias_lenses still does not compute metal metrics.
    """

    by_family: Dict[str, List[TraitCandidate]] = {}
    for t in traits:
        by_family.setdefault(t.family, []).append(t)

    def best(fam: str) -> Optional[TraitCandidate]:
        xs = by_family.get(fam) or []
        if not xs:
            return None
        return sorted(xs, key=lambda t: (t.salience, t.score), reverse=True)[0]

    boundary = best("boundary")
    spectral = best("spectral")
    stability = best("stability")
    symmetry = best("symmetry")
    closure = best("closure")

    shimmer_parts = [x for x in (boundary, spectral) if x is not None]
    glimmer_parts = [x for x in (stability, symmetry, closure) if x is not None]

    shimmer = _composite("shimmer", shimmer_parts, [1.0] * len(shimmer_parts))
    glimmer = _composite("glimmer", glimmer_parts, [1.0] * len(glimmer_parts))

    if canonical_gs is not None:
        # Best-effort; remain JSON-safe; never throw.
        try:
            gcore = canonical_gs.get("glimmer_core")
            if gcore is not None:
                glimmer["core"] = {
                    "glimmer_core": float(gcore),
                    "mode": canonical_gs.get("mode"),
                    "window_n": canonical_gs.get("window_n"),
                    "dt_s": canonical_gs.get("dt_s"),
                    "sig16": canonical_gs.get("signature16") or canonical_gs.get("sig16"),
                }
        except Exception:
            pass

        try:
            score = canonical_gs.get("shimmer_core")
            if score is not None:
                shimmer["core"] = {
                    "shimmer_core": float(score),
                    "shimmer_spec": canonical_gs.get("shimmer_spec"),
                    "ash": canonical_gs.get("ash") or canonical_gs.get("ash_residual"),
                    "mode": canonical_gs.get("mode"),
                    "window_n": canonical_gs.get("window_n"),
                    "dt_s": canonical_gs.get("dt_s"),
                    "sig16": canonical_gs.get("signature16") or canonical_gs.get("sig16"),
                }
        except Exception:
            pass

    return {"shimmer": shimmer, "glimmer": glimmer}


# ─────────────────────────────────────────────────────────────────────────────
# Dream Notebook seam — compact, JSON-safe, caller-writable
# ─────────────────────────────────────────────────────────────────────────────

def dream_probe_bundle(
    value_sigma_grid: np.ndarray,
    keep_mask_joint: Optional[np.ndarray] = None,
    *,
    dialect: Optional[str] = None,
    canonical_gs: Optional[Mapping[str, Any]] = None,
    include_composites: bool = True,
    include_events: bool = True,
    include_runtime: bool = False,
) -> Dict[str, Any]:
    """Canonical notebook-facing entrypoint.

    Stable keys:
      - ok: bool
      - traits: list[dict]
      - signature: dict
      - meta: dict
      - composites: dict (optional)
      - events: list[str] (optional)

    Determinism:
      - Default includes no timestamps.
      - include_runtime adds elapsed_ms (non-deterministic by nature).
    """

    t0 = time.perf_counter() if include_runtime else 0.0
    events: List[str] = []

    def ev(tag: str) -> None:
        if include_events:
            events.append(tag)

    ev("bias_bundle_begin")

    # Strict shape contract (anti-truncation / anti-guess discipline)
    arr = np.asarray(value_sigma_grid) if isinstance(value_sigma_grid, np.ndarray) else None
    if arr is None or arr.shape != PI_SHAPE:
        ev("bias_bundle_shape_refuse")
        out: Dict[str, Any] = {
            "ok": False,
            "traits": [],
            "signature": summarize_bundle_signature([]),
            "meta": {
                "kind": "bias_lenses_bundle",
                "authority": {"schema": "none", "organ": "bias_lenses"},
                "shape_ok": False,
                "expected_shape": list(PI_SHAPE),
                "got_shape": list(getattr(value_sigma_grid, "shape", ())),
                "mask_used": "provided" if keep_mask_joint is not None else "all",
            },
        }
        if include_events:
            out["events"] = events + ["bias_bundle_end"]
        if include_runtime:
            out["meta"]["elapsed_ms"] = float((time.perf_counter() - t0) * 1000.0)
        return out

    d, dmeta = resolve_rotation_dialect(dialect)
    if d is None:
        ev("bias_bundle_dialect_unknown")
        out = {
            "ok": False,
            "traits": [],
            "signature": summarize_bundle_signature([]),
            "meta": {
                "kind": "bias_lenses_bundle",
                "authority": {"schema": "none", "organ": "bias_lenses"},
                "shape_ok": True,
                "mask_used": "provided" if keep_mask_joint is not None else "all",
                **dmeta,
            },
        }
        if include_events:
            out["events"] = events + ["bias_bundle_end"]
        if include_runtime:
            out["meta"]["elapsed_ms"] = float((time.perf_counter() - t0) * 1000.0)
        return out

    ev("bias_rotation_dialect_used")

    traits = compute_trait_candidates(arr, keep_mask_joint, rotation_dialect=d)
    sig = summarize_bundle_signature(traits)

    # gentle hint (still non-adjudicative): high mean uncertainty
    mean_unc = float(np.mean([t.uncertainty for t in traits])) if traits else 1.0
    if mean_unc > 0.60:
        ev("bias_uncertainty_high")

    bundle: Dict[str, Any] = {
        "ok": True,
        "traits": traits_to_rows(traits),
        "signature": {
            **sig,
            "dialect_id": d.dialect_id,
            "dialect_sig16": rotation_sweep_signature(d)[:16],
        },
        "meta": {
            "kind": "bias_lenses_bundle",
            "authority": {"schema": "none", "organ": "bias_lenses"},
            "shape_ok": True,
            "mask_used": "provided" if keep_mask_joint is not None else "all",
            **dmeta,
        },
    }

    if include_composites:
        bundle["composites"] = shimmer_glimmer_summary(traits, canonical_gs=canonical_gs)

    # schema-free fingerprint for cross-run comparison / Bookshelf indexing
    bundle["bundle_fingerprint"] = bundle_fingerprint(bundle)

    ev("bias_bundle_end")
    if include_events:
        bundle["events"] = events

    if include_runtime:
        bundle["meta"]["elapsed_ms"] = float((time.perf_counter() - t0) * 1000.0)

    return bundle


# ─────────────────────────────────────────────────────────────────────────────
# Explicit opt-in nurture (small, conservative)
# ─────────────────────────────────────────────────────────────────────────────

def nurture_trait(
    value_sigma_grid: np.ndarray,
    trait: TraitCandidate,
    strength: float = 0.05,
    keep_mask_joint: Optional[np.ndarray] = None,
) -> np.ndarray:
    """Explicit opt-in transform.

    - NOT learning, not persistence, not adjudication.
    - Increases SIGMA proportional to magnitude of changes (explicit cost).
    """

    out = np.asarray(value_sigma_grid).copy()
    if out.shape != PI_SHAPE:
        raise ValueError(f"expected {PI_SHAPE}, got {out.shape}")

    m = _mask_or_all(keep_mask_joint)

    v = out[..., CH_VALUE]
    s = out[..., CH_SIGMA]

    if trait.family == "symmetry" and "axis_diffs" in trait.evidence:
        mu = _safe_mean(v, m)
        dv = (mu - v) * float(strength)
        v[m] = v[m] + dv[m]
        s[m] = s[m] + np.abs(dv[m])

    if trait.family == "boundary":
        def sh(a: np.ndarray, dx: int, dy: int, dz: int) -> np.ndarray:
            return np.roll(np.roll(np.roll(a, dx, 0), dy, 1), dz, 2)

        avg = (
            v
            + sh(v, 1, 0, 0)
            + sh(v, -1, 0, 0)
            + sh(v, 0, 1, 0)
            + sh(v, 0, -1, 0)
            + sh(v, 0, 0, 1)
            + sh(v, 0, 0, -1)
        ) / 7.0
        dv = (avg - v) * float(strength)
        v[m] = v[m] + dv[m]
        s[m] = s[m] + np.abs(dv[m])

    out[..., CH_VALUE] = v
    out[..., CH_SIGMA] = s
    return out


# ─────────────────────────────────────────────────────────────────────────────
# Append-only helper (caller-owned)
# ─────────────────────────────────────────────────────────────────────────────

class PhenotypeCatalogWriter:
    """Tiny JSONL writer. Caller owns path, timing, and forensics doctrine."""

    def __init__(self, jsonl_path: str):
        self.jsonl_path = str(jsonl_path)

    def append(
        self,
        run_id: str,
        identity_anchor: str,
        weave_signature: str,
        traits: Sequence[TraitCandidate],
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        row = {
            "ts": time.time(),  # caller-owned persistence; non-determinism is acceptable here
            "run_id": str(run_id),
            "identity_anchor": str(identity_anchor),
            "weave_signature": str(weave_signature),
            "traits": traits_to_rows(traits),
        }
        if extra:
            row["extra"] = extra
        line = json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        with open(self.jsonl_path, "a", encoding="utf-8") as f:
            f.write(line + "\n")


# ─────────────────────────────────────────────────────────────────────────────
# Minimal smoke test (offline; no persistence)
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    rng = np.random.default_rng(0)
    arr = np.zeros(PI_SHAPE, dtype=np.float32)
    arr[..., CH_VALUE] = np.clip(rng.normal(0.50, 0.08, PI_SHAPE[:3]), 0.0, 1.0).astype(np.float32)
    arr[..., CH_SIGMA] = 0.5

    bundle = dream_probe_bundle(arr, dialect="rot_dialect_v1", include_runtime=True)
    print("ok:", bundle["ok"])
    print("weave_signature16:", bundle["signature"].get("weave_signature16"))
    print("dialect:", bundle["signature"].get("dialect_id"), bundle["signature"].get("dialect_sig16"))
    print("top_families:", bundle["signature"].get("top_families"))
    if "composites" in bundle:
        sh = bundle["composites"]["shimmer"]
        gl = bundle["composites"]["glimmer"]
        print("shimmer:", sh["score"], "unc:", sh["uncertainty"], "core:", sh.get("core"))
        print("glimmer:", gl["score"], "unc:", gl["uncertainty"], "core:", gl.get("core"))
    for t in bundle["traits"][:5]:
        print(f"- {t['family']:9s} {t['name'][:40]:40s} score={t['score']:.3f} unc={t['uncertainty']:.3f} sal={t['salience']:.3f}")
