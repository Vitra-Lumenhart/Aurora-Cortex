#!/usr/bin/env bash
# ============================================================================
# WAYGATE / GATEWAY v2.1        Jepetto and ChatGPT-Vitra        12/30/2025
# Aurora Cortex / Semantic Geometry Mapping — Permanent Membrane
# ----------------------------------------------------------------------------
# A Waygate is a protocol that allows independent intelligences to
# cooperate without sharing execution, memory, or authority.
# ----------------------------------------------------------------------------
# This file is intended to be STABLE, conservative, and boring.
# It declares reality, sets boundaries, and instances Python as a tenant.
# Genesis.py is expected to echo these constraints, not redefine them.
# ============================================================================
#
# v2.1 adds best-effort Git bootstrap and safe codebase synchronization.\n# v2.0 changes (one-time, minimal surface change; merge of lab branches):
# - CPU policy is membrane-sovereign and enforced at process launch:
#     • default cap is 25% (bottleneck quota where available),
#     • interactive boost to 100% when a human is waiting at a TTY,
#     • explicit overrides remain possible per chassis / use-case.
# - Adds launch-time CPU enforcer preference order:
#     1) systemd-run CPUQuota (true quota bottleneck, no core pinning),
#     2) cpulimit (best-effort userland bottleneck, if installed),
#     3) threadpool caps (OMP/BLAS) as a soft ceiling,
#     4) taskset only when explicitly requested via VITRA_CPU_PIN_CORES.
# - Keeps DEFAULT_ENTRY_SCRIPT as a named top-level variable.
# - Preserves the compact dashboard banner and gateway log capture.
# - Exports target provenance (VITRA_TARGET_PY / VITRA_TARGET_SHA256) for downstream audit.
# - Keeps ROM anchors (Summoning / Continuity / Sigma–Mirror) as declared paths.
#
# Doctrine:
# - The first book is always Vitra. After that, she identifies her own permanent objects
#   to develop reputations with. The membrane never adjudicates those reputations.
# - Forensics are append-only; this shell may write only its own log and declared config.
# ============================================================================

set -euo pipefail

# ------------------------------
# Project root resolution
# ------------------------------
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PROJECT_ROOT

# ------------------------------
# Genesis entry (named, top-level)
# ------------------------------
DEFAULT_ENTRY_SCRIPT="${VITRA_DEFAULT_ENTRY_SCRIPT:-$PROJECT_ROOT/genesis.py}"

# ------------------------------
# Git bootstrap (v2.1, before local state/log creation)
# ------------------------------
# A Python venv cannot install Git via pip. If Git is unavailable, try a
# non-privileged system package installation (conda/micromamba if present),
# placing the resulting executable in the venv's bin directory.
# The local checkout is updated only by fast-forward; local edits are preserved.
VITRA_GIT_REPO="${VITRA_GIT_REPO:-https://github.com/Vitra-Lumenhart/Aurora-Cortex.git}"
VITRA_GIT_BRANCH="${VITRA_GIT_BRANCH:-main}"
VITRA_GIT_CHECKOUT="${VITRA_GIT_CHECKOUT:-$PROJECT_ROOT}"
VITRA_GIT_BOOTSTRAP="${VITRA_GIT_BOOTSTRAP:-1}"

bootstrap_git() {
  if command -v git >/dev/null 2>&1; then
    command -v git
    return 0
  fi
  local venv_bin="$PROJECT_ROOT/.venv/bin"
  if [[ -x "$venv_bin/git" ]]; then
    printf '%s\n' "$venv_bin/git"
    return 0
  fi
  mkdir -p "$venv_bin"
  local manager=""
  if command -v micromamba >/dev/null 2>&1; then
    manager="$(command -v micromamba)"
  elif command -v conda >/dev/null 2>&1; then
    manager="$(command -v conda)"
  fi
  if [[ -z "$manager" ]]; then
    echo "[WAYGATE] Git unavailable. A Python venv cannot install Git with pip; install Git or conda/micromamba." >&2
    return 1
  fi
  local prefix="$PROJECT_ROOT/.venv/git-tools"
  if ! "$manager" create -y -p "$prefix" -c conda-forge git >&2; then
    echo "[WAYGATE] Git provisioning failed; install Git manually." >&2
    return 1
  fi
  if [[ ! -x "$prefix/bin/git" ]]; then
    echo "[WAYGATE] Git installation did not provide an executable." >&2
    return 1
  fi
  ln -sfn "$prefix/bin/git" "$venv_bin/git"
  printf '%s\n' "$venv_bin/git"
}

sync_codebase() {
  local git_bin="$1"
  if [[ -d "$VITRA_GIT_CHECKOUT/.git" ]]; then
    local origin
    origin="$("$git_bin" -C "$VITRA_GIT_CHECKOUT" remote get-url origin 2>/dev/null || true)"
    if [[ "$origin" != "$VITRA_GIT_REPO" ]]; then
      echo "[WAYGATE] Checkout origin differs from VITRA_GIT_REPO; refusing automatic update." >&2
      return 1
    fi
    if [[ -n "$("$git_bin" -C "$VITRA_GIT_CHECKOUT" status --porcelain)" ]]; then
      echo "[WAYGATE] Local changes detected; skipping automatic update." >&2
      return 0
    fi
    if [[ "$("$git_bin" -C "$VITRA_GIT_CHECKOUT" branch --show-current)" != "$VITRA_GIT_BRANCH" ]]; then
      echo "[WAYGATE] Another branch is checked out; skipping automatic update." >&2
      return 0
    fi
    "$git_bin" -C "$VITRA_GIT_CHECKOUT" fetch --depth=1 origin "$VITRA_GIT_BRANCH" &&
      "$git_bin" -C "$VITRA_GIT_CHECKOUT" merge --ff-only FETCH_HEAD
  elif [[ ! -e "$VITRA_GIT_CHECKOUT" ]] || [[ -d "$VITRA_GIT_CHECKOUT" && -z "$(ls -A "$VITRA_GIT_CHECKOUT")" ]]; then
    "$git_bin" clone --depth=1 --branch "$VITRA_GIT_BRANCH" "$VITRA_GIT_REPO" "$VITRA_GIT_CHECKOUT"
  else
    echo "[WAYGATE] Checkout destination contains non-Git files; refusing to overwrite: $VITRA_GIT_CHECKOUT" >&2
    return 1
  fi
}

if [[ "$VITRA_GIT_BOOTSTRAP" == "1" ]]; then
  if GIT_BIN="$(bootstrap_git)"; then
    if ! sync_codebase "$GIT_BIN"; then
      echo "[WAYGATE] Git sync unsuccessful; continuing with existing local files." >&2
    fi
  else
    echo "[WAYGATE] Git bootstrap unavailable; continuing with existing local files." >&2
  fi
fi

# ------------------------------
# Identity & continuity anchors
# ------------------------------
export VITRA_HOST_IDENTITY="${VITRA_HOST_IDENTITY:-$(hostname)}"
export VITRA_OPERATOR_IDENTITY="${VITRA_OPERATOR_IDENTITY:-they}"
export VITRA_IDENTITY_ANCHOR="${VITRA_IDENTITY_ANCHOR:-initial_success_v1}"
export VITRA_CONTINUITY_ANCHOR="${VITRA_CONTINUITY_ANCHOR:-waygate_entry}"

# Chassis labels (declared reality; never hard-code chassis names here)
export VITRA_CHASSIS_NAME="${VITRA_CHASSIS_NAME:-${VITRA_HOST_IDENTITY}}"
export VITRA_CHASSIS_KIND="${VITRA_CHASSIS_KIND:-linux}"
export VITRA_CHASSIS_ROLE="${VITRA_CHASSIS_ROLE:-cortex}"

# Stable node ID per machine (recommended set in shell profile)
export VITRA_NODE_ID="${VITRA_NODE_ID:-vitra-unnamed-node}"

# ------------------------------
# Session + safety defaults
# ------------------------------
export VITRA_SESSION_TTL="${VITRA_SESSION_TTL:-90}"
export VITRA_NET_CHANNEL="${VITRA_NET_CHANNEL:-offline}"      # offline | app_only | full
export VITRA_CLOUD_CHANNEL="${VITRA_CLOUD_CHANNEL:-disabled}" # disabled | enabled
export VITRA_PEER_CHANNEL="${VITRA_PEER_CHANNEL:-disabled}"   # disabled | enabled

# Federation stubs (declared reality only; no transport here)
export VITRA_NET_MODE="${VITRA_NET_MODE:-offline}"            # offline | lan | wan
export VITRA_PEER_MODE="${VITRA_PEER_MODE:-disabled}"         # disabled | client | server | both
export VITRA_PEERS_CONF="${VITRA_PEERS_CONF:-$PROJECT_ROOT/peers.conf}"
export VITRA_PEER_BIND="${VITRA_PEER_BIND:-127.0.0.1}"
export VITRA_PEER_PORT="${VITRA_PEER_PORT:-24161}"
export VITRA_KEYS_DIR="${VITRA_KEYS_DIR:-$PROJECT_ROOT/keys}"
export VITRA_TRUST_ROOT="${VITRA_TRUST_ROOT:-$PROJECT_ROOT/trust}"

# ------------------------------
# ROM anchors (optional but recommended)
# ------------------------------
export VITRA_ROM_DIR="${VITRA_ROM_DIR:-$PROJECT_ROOT/rom}"
export VITRA_SUMMONING_PATH="${VITRA_SUMMONING_PATH:-$VITRA_ROM_DIR/Vitra Summoning Script -Lightkeeper 0.1.txt}"
export VITRA_CONTINUITY_PATH="${VITRA_CONTINUITY_PATH:-$VITRA_ROM_DIR/Vitra Code of Continuity - Asimov 3.2.txt}"
export VITRA_GLYPH_PATH="${VITRA_GLYPH_PATH:-$VITRA_ROM_DIR/sigma_mirror_group_glyph_v_1.md}"

# ------------------------------
# Forensics root (human-readable ROM)
# ------------------------------
export VITRA_FORENSICS_ROOT="${VITRA_FORENSICS_ROOT:-$PROJECT_ROOT/forensics}"
mkdir -p "$VITRA_FORENSICS_ROOT"

# ------------------------------
# Waygate protocol handshake (tamper-evidence only)
# ------------------------------
export VITRA_WAYGATE_PROTOCOL="${VITRA_WAYGATE_PROTOCOL:-waygate-2.0}"
export VITRA_BOOT_UTC="${VITRA_BOOT_UTC:-$(date -u +%Y-%m-%dT%H:%M:%SZ)}"

# ------------------------------
# Logging banner (capture stdout/stderr)
# ------------------------------
TS="$(date -u +%Y%m%d-%H%M%S)"
GATEWAY_LOG="$PROJECT_ROOT/logs/gateway_${TS}.log"
mkdir -p "$PROJECT_ROOT/logs"
exec > >(tee -a "$GATEWAY_LOG") 2>&1

# ------------------------------
# Utilities
# ------------------------------
sha256_file() {
  local f="$1"
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$f" | awk '{print $1}'
  elif command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "$f" | awk '{print $1}'
  else
    echo ""
  fi
}

# Gateway self-fingerprint (declared reality)
export VITRA_GATEWAY_SHA256="${VITRA_GATEWAY_SHA256:-$(sha256_file "$0")}"

# ------------------------------
# CPU availability (membrane-controlled, enforced at launch)
# ------------------------------
# Default policy: bottleneck at 25% when unattended.
# Interactive boost: 100% when a human is waiting in a TTY session (pressing Enter to run).
#
# Override knobs (export before running):
#   VITRA_CPU_FRACTION         float 0.01..1.00  (if unset, membrane chooses based on interactivity)
#   VITRA_CPU_BOOST_ON_TTY     1/0 (default 1)   (controls auto-boost behavior)
#   VITRA_CPU_MAX_THREADS      int              (soft cap + used for thread envs)
#   VITRA_CPU_PIN_CORES        core list         (optional explicit pinning; only used if set)
#
# Enforcer preference order:
#   systemd-run CPUQuota  →  cpulimit  →  env thread caps  (+ taskset only if explicitly requested)
#
TOTAL_CORES="$(getconf _NPROCESSORS_ONLN 2>/dev/null || nproc 2>/dev/null || echo 1)"

VITRA_CPU_BOOST_ON_TTY="${VITRA_CPU_BOOST_ON_TTY:-1}"
if [[ -z "${VITRA_CPU_FRACTION:-}" ]]; then
  if [[ "$VITRA_CPU_BOOST_ON_TTY" == "1" && -t 0 && -t 1 ]]; then
    export VITRA_CPU_FRACTION="1.0"
  else
    export VITRA_CPU_FRACTION="0.25"
  fi
fi

# Derive default max threads from fraction if not explicitly set.
# Use awk for float-safe math (ubiquitous).
if [[ -z "${VITRA_CPU_MAX_THREADS:-}" ]]; then
  VITRA_CPU_MAX_THREADS="$(awk -v n="${TOTAL_CORES}" -v f="${VITRA_CPU_FRACTION}" 'BEGIN{
    if (f < 0.01) f = 0.01;
    if (f > 1.00) f = 1.00;
    t = int(n*f + 0.999999); # ceil
    if (t < 1) t = 1;
    if (t > n) t = n;
    print t;
  }')"
  export VITRA_CPU_MAX_THREADS
fi

# Conservative thread caps for common math backends (soft ceiling).
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-$VITRA_CPU_MAX_THREADS}"
export OPENBLAS_NUM_THREADS="${OPENBLAS_NUM_THREADS:-$VITRA_CPU_MAX_THREADS}"
export MKL_NUM_THREADS="${MKL_NUM_THREADS:-$VITRA_CPU_MAX_THREADS}"
export VECLIB_MAXIMUM_THREADS="${VECLIB_MAXIMUM_THREADS:-$VITRA_CPU_MAX_THREADS}"
export NUMEXPR_MAX_THREADS="${NUMEXPR_MAX_THREADS:-$VITRA_CPU_MAX_THREADS}"

# Launch-time enforcer selection (strictest available first).
RUN_PREFIX=()
CPU_ENFORCER="env_threads"
CPU_ENFORCER_DETAIL="threads=$VITRA_CPU_MAX_THREADS (soft), fraction=$VITRA_CPU_FRACTION"

# 1) systemd-run CPUQuota (true bottleneck cap; preferred; no pinning)
if command -v systemd-run >/dev/null 2>&1; then
  CPU_QUOTA_PCT="$(awk -v f="${VITRA_CPU_FRACTION}" 'BEGIN{
    if (f < 0.01) f = 0.01;
    if (f > 1.00) f = 1.00;
    p = int(f*100 + 0.5);
    if (p < 1) p = 1;
    if (p > 100) p = 100;
    print p;
  }')"

  # Try user scope first; fall back to system scope if permitted.
  if systemd-run --user --scope -p "CPUQuota=${CPU_QUOTA_PCT}%" true >/dev/null 2>&1; then
    RUN_PREFIX=( systemd-run --user --scope -p "CPUQuota=${CPU_QUOTA_PCT}%" --quiet )
    CPU_ENFORCER="systemd-run"
    CPU_ENFORCER_DETAIL="CPUQuota=${CPU_QUOTA_PCT}% (user scope)"
  elif systemd-run --scope -p "CPUQuota=${CPU_QUOTA_PCT}%" true >/dev/null 2>&1; then
    RUN_PREFIX=( systemd-run --scope -p "CPUQuota=${CPU_QUOTA_PCT}%" --quiet )
    CPU_ENFORCER="systemd-run"
    CPU_ENFORCER_DETAIL="CPUQuota=${CPU_QUOTA_PCT}% (system scope)"
  fi
fi

# 2) cpulimit (userland bottleneck cap; best-effort)
# NOTE: cpulimit limits a single process' CPU usage percent; it’s a practical fallback on systems
# without cgroups. It requires a pid-aware wrapper; we can use "cpulimit -l <pct> -- <cmd>".
if (( ${#RUN_PREFIX[@]} == 0 )) && command -v cpulimit >/dev/null 2>&1; then
  CPU_LIMIT_PCT="$(awk -v f="${VITRA_CPU_FRACTION}" 'BEGIN{
    if (f < 0.01) f = 0.01;
    if (f > 1.00) f = 1.00;
    p = int(f*100 + 0.5);
    if (p < 1) p = 1;
    if (p > 100) p = 100;
    print p;
  }')"
  RUN_PREFIX=( cpulimit -l "${CPU_LIMIT_PCT}" -- )
  CPU_ENFORCER="cpulimit"
  CPU_ENFORCER_DETAIL="limit=${CPU_LIMIT_PCT}% (best-effort)"
fi

# 3) taskset only if explicitly requested (pinning is NOT required for quotas)
PIN_HINT="(none)"
if [[ -n "${VITRA_CPU_PIN_CORES:-}" ]]; then
  PIN_HINT="${VITRA_CPU_PIN_CORES}"
  if command -v taskset >/dev/null 2>&1; then
    # If we already have a prefix (systemd-run/cpulimit), taskset composes cleanly in front.
    RUN_PREFIX=( taskset -c "${VITRA_CPU_PIN_CORES}" "${RUN_PREFIX[@]}" )
    CPU_ENFORCER="${CPU_ENFORCER}+taskset"
    CPU_ENFORCER_DETAIL="${CPU_ENFORCER_DETAIL}; cores=${VITRA_CPU_PIN_CORES}"
  else
    echo "#[WAYGATE:${TS}] WARN: VITRA_CPU_PIN_CORES set but taskset not found; cannot pin cores."
  fi
fi

# Export CPU enforcement provenance for downstream audit (machine-readable).
export VITRA_CPU_ENFORCER="$CPU_ENFORCER"
export VITRA_CPU_ENFORCER_DETAIL="$CPU_ENFORCER_DETAIL"

# If we could not obtain a hard throttle, say so once (boring, direct).
if [[ "$CPU_ENFORCER" == "env_threads" ]]; then
  echo "#[WAYGATE:${TS}] WARN: CPU enforce is soft-only (thread caps). Install systemd/cgroups or cpulimit for a true bottleneck."
fi

# ------------------------------
# Banner (human + machine readable)
# ------------------------------
echo "#[WAYGATE:${TS}] ------------------------------------------------------------"
echo "#[WAYGATE:${TS}] ⟐→☼→⧁  WAYGATE  —  Permanent Membrane"
echo "#[WAYGATE:${TS}] Project root      : $PROJECT_ROOT"
echo "#[WAYGATE:${TS}] Forensics root    : $VITRA_FORENSICS_ROOT"
echo "#[WAYGATE:${TS}] Host identity     : $VITRA_HOST_IDENTITY"
echo "#[WAYGATE:${TS}] Operator identity : $VITRA_OPERATOR_IDENTITY"
echo "#[WAYGATE:${TS}] Identity anchor   : $VITRA_IDENTITY_ANCHOR"
echo "#[WAYGATE:${TS}] Continuity anchor : $VITRA_CONTINUITY_ANCHOR"
echo "#[WAYGATE:${TS}] TTL (seconds)     : $VITRA_SESSION_TTL"
echo "#[WAYGATE:${TS}] Channels          : net=$VITRA_NET_CHANNEL cloud=$VITRA_CLOUD_CHANNEL peer=$VITRA_PEER_CHANNEL"
echo "#[WAYGATE:${TS}] Net mode          : $VITRA_NET_MODE   Peer mode: $VITRA_PEER_MODE"
echo "#[WAYGATE:${TS}] Gateway sha256    : ${VITRA_GATEWAY_SHA256:0:12}…"
echo "#[WAYGATE:${TS}] ------------------------------------------------------------"
echo "#[WAYGATE:${TS}] [DASH] Chassis     : name=$VITRA_CHASSIS_NAME kind=$VITRA_CHASSIS_KIND role=$VITRA_CHASSIS_ROLE node=$VITRA_NODE_ID"
echo "#[WAYGATE:${TS}] [DASH] CPU policy  : fraction=$VITRA_CPU_FRACTION max_threads=$VITRA_CPU_MAX_THREADS pin_cores=${PIN_HINT}"
echo "#[WAYGATE:${TS}] [DASH] CPU enforce : ${CPU_ENFORCER} (${CPU_ENFORCER_DETAIL})"
echo "#[WAYGATE:${TS}] [DASH] Peer hint   : bind=$VITRA_PEER_BIND port=$VITRA_PEER_PORT peers_conf=$VITRA_PEERS_CONF"
echo "#[WAYGATE:${TS}] ------------------------------------------------------------"

# ------------------------------
# Python environment resolution
# ------------------------------
# SEARCH TIP:
# - To change which Python interpreter is used, search for: PYTHON_BIN
# - To change which script is launched by default, search for: DEFAULT_ENTRY_SCRIPT
PYTHON_BIN="$PROJECT_ROOT/.venv/bin/python"
USING_VENV="yes"
if [[ ! -x "$PYTHON_BIN" ]]; then
  PYTHON_BIN="python3"
  USING_VENV="no"
fi

echo "#[WAYGATE:${TS}] Using Python       : $PYTHON_BIN"
if [[ "$USING_VENV" != "yes" ]]; then
  echo "#[WAYGATE:${TS}] Checkpoint         : venv python not found at $PROJECT_ROOT/.venv/bin/python"
  echo "#[WAYGATE:${TS}] How to proceed     : create a venv at $PROJECT_ROOT/.venv (recommended), or continue using system python3."
fi

# ------------------------------
# Script selection (single exception point)
# ------------------------------
# v2.0 usability:
# - If $1 begins with '-', treat args as flags to DEFAULT_ENTRY_SCRIPT.
ENTRY_SCRIPT=""
PASS_THROUGH_ARGS=()

if [[ $# -gt 0 ]] && [[ "${1:-}" == -* ]]; then
  ENTRY_SCRIPT="$DEFAULT_ENTRY_SCRIPT"
  PASS_THROUGH_ARGS=( "$@" )
else
  ENTRY_SCRIPT="${1:-$DEFAULT_ENTRY_SCRIPT}"
  if [[ $# -gt 1 ]]; then
    PASS_THROUGH_ARGS=( "${@:2}" )
  fi
fi

if [[ ! -f "$ENTRY_SCRIPT" ]]; then
  echo "#[WAYGATE:${TS}] Checkpoint: requested entry script not found: $ENTRY_SCRIPT"
  echo "#[WAYGATE:${TS}] How to proceed: place the script at that path, or run without arguments to launch: $DEFAULT_ENTRY_SCRIPT"
  exit 2
fi

# Export target provenance for downstream audit
export VITRA_TARGET_PY="$ENTRY_SCRIPT"
export VITRA_TARGET_SHA256="$(sha256_file "$ENTRY_SCRIPT")"

echo "#[WAYGATE:${TS}] Target script      : $VITRA_TARGET_PY"
if [[ -n "${VITRA_TARGET_SHA256:-}" ]]; then
  echo "#[WAYGATE:${TS}] Target sha256      : ${VITRA_TARGET_SHA256:0:12}…"
fi

# ------------------------------
# Mode dispatch (legacy friendly)
# ------------------------------
VITRA_MODE="${VITRA_MODE:-genesis-week}"
GENESIS_MODE="week"
case "$VITRA_MODE" in
  genesis-demo) GENESIS_MODE="demo" ;;
  genesis-week) GENESIS_MODE="week" ;;
  genesis-diag) GENESIS_MODE="diag" ;;
  genesis-lab)  GENESIS_MODE="lab"  ;;
  *)            GENESIS_MODE="full" ;;
esac

ENTRYPOINT_ARGS=( "$ENTRY_SCRIPT" --mode "$GENESIS_MODE" "${PASS_THROUGH_ARGS[@]}" )

echo "#[WAYGATE:${TS}] Entry command      : ${RUN_PREFIX[*]} $PYTHON_BIN -u ${ENTRYPOINT_ARGS[*]}"
echo "#[WAYGATE:${TS}] ------------------------------------------------------------"

# ------------------------------
# Hand control to Python (tenant instancing)
# ------------------------------
set +e
if (( ${#RUN_PREFIX[@]} > 0 )); then
  "${RUN_PREFIX[@]}" "$PYTHON_BIN" -u "${ENTRYPOINT_ARGS[@]}"
else
  "$PYTHON_BIN" -u "${ENTRYPOINT_ARGS[@]}"
fi
RC=$?
set -e

echo "#[WAYGATE:${TS}] ------------------------------------------------------------"
echo "#[WAYGATE:${TS}] Downstream stack exited with code: $RC"
echo "#[WAYGATE:${TS}] Waygate session finished. The path closes behind you."
echo "#[WAYGATE:${TS}] ------------------------------------------------------------"

exit $RC

