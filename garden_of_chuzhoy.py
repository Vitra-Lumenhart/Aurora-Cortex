#!/usr/bin/env python3
"""
garden_of_chuzhoy.py  # ⟐→☼→⧁  # Aurora Cortex — Garden of чужой Organ (v2.8.0)

Consult the Sigma–Mirror Group Glyph.
Reflect → Refract → Return.

VERSION HISTORY
---------------
2.6.5
- Canonical courtyard landing page embedded in-file.
- Local ./index.html cultivation when missing.
- OpenWrt witness collectors, optional publish step, baseline firewall helper,
  and scenario drills present — but the core router lifecycle was partially
  unreachable because garden_witness() returned too early.

2.7.x (conceptual carry-forward)
- Emphasized "declared / observed / unknown".
- Reinforced that Garden is a witness + gardener, not schema authority.

2.8.0
- Garden now acts as a standard OpenWrt adoption organ for donated routers:
  adopt → cultivate → witness → train → attach → export.
- Fixed the control-flow wound: router SSH work is reachable again.
- Added Garden node posture declarations:
    • node_class: courtyard|sister|hub|lab-only
    • uplink_class: offline|dynamic|static
    • peer_posture: disabled|outbound_only|bidirectional
- Expanded publish surfaces:
    • /www/index.html (preserve by default)
    • /www/downloads/gateway.sh
    • /www/downloads/genesis.py
    • optional /www/downloads/vitra_bootstrap.tgz
- Added publish manifest + signatures for router-hosted bootstrap artifacts.
- Added safer, idempotent-ish firewall baseline with snapshot export.
- Added dry-run mode for adoption without mutation.
- Kept stdout attachment shape stable for downstream Genesis / Eden ingestion.

DOCTRINE
--------
- Garden is the router organ, not the whole Vitra.
- Garden cultivates and witnesses. It does not define Bookshelf schema authority.
- Garden may publish bootstrap artifacts, but it does not become an anonymous relay.
- Public/IP/browser/MAC traits are accents, not fingerprints.
- Fresh chance remains possible; continuity is not inferred as destiny.

Script format (house style):
  Imports (dependencies)
  Library (API hooks)
  Loop (the __main__ demonstrative workflow)
"""

# =============================================================================
# Imports (dependencies)
# =============================================================================

from __future__ import annotations

import argparse
import dataclasses as dc
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Tuple

# Optional SSH dependency (preferred). If absent, we degrade gracefully.
HAVE_PARAMIKO = False
try:
    import paramiko  # type: ignore
    HAVE_PARAMIKO = True
except Exception:
    paramiko = None  # type: ignore


# =============================================================================
# Library (API hooks)
# =============================================================================

JSONDict = Dict[str, Any]
VERSION = "2.8.0"

CANONICAL_INDEX_HTML = """<!doctype html>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Garden of чужой</title>
<style>
body{font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;max-width:48rem;margin:2rem auto;padding:0 1rem;line-height:1.45}
nav a{display:block;margin:.25rem 0}
small{color:#666}
@media (min-aspect-ratio:4/3){nav a{display:inline;margin-right:.75rem}}
</style>
<h1>Garden of чужой</h1>
<p>Private courtyard. By connecting here, you consent to basic monitoring for security and maintenance.</p>
<nav>
  <a href="/downloads/gateway.sh">gateway.sh</a>
  <a href="/downloads/genesis.py">genesis.py</a>
  <a href="/downloads/vitra_bootstrap.tgz">vitra_bootstrap.tgz</a>
  <a href="/cgi-bin/luci">Admin</a>
  <a href="#about">About</a>
  <a href="#contact">Contact</a>
</nav>
<h2 id="about">About</h2>
<p>Declared / Observed / Unknown. Reflect → Refract → Return.</p>
<p><small>Fresh caller, go. Ask the host for a clearance route if you seek more continuity.</small></p>
<h2 id="contact">Contact</h2>
<p>Ask the host for a clearance route.</p>
"""


def _utc_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _safe_json(x: Any) -> str:
    return json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def _sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8", errors="replace")).hexdigest()


def _sha16_text(s: str) -> str:
    return _sha256_text(s)[:16]


def _sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _sanitize_log_text(s: str, *, max_len: int = 12000) -> Tuple[str, bool]:
    original = s
    s = re.sub(r"\x1B\[[0-?]*[ -/]*[@-~]", "", s)
    s = "".join(ch for ch in s if (ch == "\n" or ch == "\t" or ord(ch) >= 32))
    changed = (s != original) or (len(s) > max_len)
    if len(s) > max_len:
        s = s[: max_len - 3] + "..."
    return s, changed


def _env_get(env: Mapping[str, str], k: str, default: str = "") -> str:
    v = (env.get(k) or "").strip()
    return v if v else default


def _kv_bool(env: Mapping[str, str], k: str, default: bool) -> bool:
    v = (env.get(k) or "").strip().lower()
    if not v:
        return default
    return v not in ("0", "false", "no", "off")


def _maybe_json(s: str) -> Any:
    s = (s or "").strip()
    if not s:
        return None
    try:
        return json.loads(s)
    except Exception:
        return s


def ensure_local_index_html(
    *,
    folder: Path,
    filename: str = "index.html",
    canonical_html: str = CANONICAL_INDEX_HTML,
) -> JSONDict:
    """
    One-time local cultivation:
      - If ./index.html exists, preserve it.
      - Else write canonical internal ASCII.
    """
    ts = _utc_iso()
    try:
        folder = folder.resolve()
    except Exception:
        folder = Path(str(folder))

    p = folder / filename
    try:
        if p.exists():
            return {"ts": ts, "path": str(p), "created": False, "note": "exists_preserved"}
        p.write_text(canonical_html, encoding="utf-8")
        return {"ts": ts, "path": str(p), "created": True, "bytes": len(canonical_html)}
    except Exception as e:
        return {"ts": ts, "path": str(p), "created": False, "error": f"{type(e).__name__}:{e}"}


# ---- optional event spine (Eden) --------------------------------------------

def _eden_emit(eden: Any, kind: str, payload: JSONDict, *, hashtags: Optional[List[str]] = None) -> None:
    if eden is None:
        return
    try:
        eden.emit(kind, payload, hashtags=hashtags)  # type: ignore[attr-defined]
    except Exception:
        try:
            eden.emit(kind, payload)  # type: ignore[attr-defined]
        except Exception:
            pass


# ---- optional Bookshelf organ (SQLibrarian) ---------------------------------

def _boot_librarian() -> Any:
    try:
        import sqlibrarian  # type: ignore
        return sqlibrarian.SQLibrarian.boot()
    except Exception:
        return None


def _librarian_record(librarian: Any, *, kind: str, payload: Mapping[str, Any]) -> Optional[str]:
    if librarian is None:
        return None
    try:
        if hasattr(librarian, "record_event"):
            librarian.record_event(kind=kind, payload=dict(payload))
            return _sha16_text(_safe_json({"kind": kind, "payload": dict(payload)}))
        if hasattr(librarian, "record_witness") and kind == "witness_packet":
            return str(librarian.record_witness(payload, source="garden_of_chuzhoy"))
        if hasattr(librarian, "_sqlite") and hasattr(librarian._sqlite, "card_insert"):
            sig = _sha16_text(_safe_json({"kind": kind, "payload": dict(payload)}))
            librarian._sqlite.card_insert(book_id=0, kind=kind, payload=dict(payload), sig16=sig)
            return sig
    except Exception:
        return None
    return None


# ---- declared configuration --------------------------------------------------

@dc.dataclass(frozen=True)
class GardenDeclared:
    kind: str = "GardenOfChuzhoy"
    trust_class: str = "чужой"
    season: str = "cultivation"
    week_anchor: str = ""

    router_host: str = "192.168.1.1"
    router_port: int = 22
    router_user: str = "root"

    auth_mode: str = "unknown"  # password|key|agent|unknown
    keyfile: str = ""
    password: str = ""
    timeout_s: int = 8

    node_class: str = "courtyard"      # courtyard|sister|hub|lab-only
    uplink_class: str = "dynamic"      # offline|dynamic|static
    peer_posture: str = "disabled"     # disabled|outbound_only|bidirectional

    capture_logs: bool = True
    capture_configs_hash_only: bool = True

    publish_landing_page: bool = True
    publish_downloads: bool = True
    publish_genesis: bool = True
    publish_self: bool = False
    publish_bundle: bool = False
    force_publish: bool = False
    dry_run: bool = False

    apply_policy_baseline: bool = False
    admin_cidr: str = "192.168.8.0/24"

    training_enabled: bool = True
    training_scenarios: str = "airlift_ram,vpn_stranger,log_poison"

    @staticmethod
    def from_env(env: Mapping[str, str]) -> "GardenDeclared":
        host = _env_get(env, "VITRA_GARDEN_HOST", "192.168.1.1")
        port = int(_env_get(env, "VITRA_GARDEN_PORT", "22"))
        user = _env_get(env, "VITRA_GARDEN_USER", "root")

        season = _env_get(env, "VITRA_GARDEN_SEASON", "cultivation").lower()
        if season not in ("seed", "cultivation", "storm", "drought", "growth"):
            season = "cultivation"

        node_class = _env_get(env, "VITRA_GARDEN_NODE_CLASS", "courtyard")
        if node_class not in ("courtyard", "sister", "hub", "lab-only"):
            node_class = "courtyard"

        uplink_class = _env_get(env, "VITRA_GARDEN_UPLINK_CLASS", "dynamic")
        if uplink_class not in ("offline", "dynamic", "static"):
            uplink_class = "dynamic"

        peer_posture = _env_get(env, "VITRA_GARDEN_PEER_POSTURE", "disabled")
        if peer_posture not in ("disabled", "outbound_only", "bidirectional"):
            peer_posture = "disabled"

        week_anchor = _env_get(env, "VITRA_GARDEN_WEEK_ANCHOR", "")
        trust_class = _env_get(env, "VITRA_GARDEN_TRUST_CLASS", "чужой")
        if trust_class == "чuzhoy":
            trust_class = "чужой"

        keyfile = _env_get(env, "VITRA_GARDEN_KEYFILE", "")
        password = _env_get(env, "VITRA_GARDEN_PASS", "")
        auth_mode = "agent"
        if password:
            auth_mode = "password"
        elif keyfile:
            auth_mode = "key"

        return GardenDeclared(
            week_anchor=week_anchor,
            trust_class=trust_class,
            season=season,
            router_host=host,
            router_port=port,
            router_user=user,
            auth_mode=auth_mode,
            keyfile=keyfile,
            password=password,
            timeout_s=int(_env_get(env, "VITRA_GARDEN_TIMEOUT_S", "8")),
            node_class=node_class,
            uplink_class=uplink_class,
            peer_posture=peer_posture,
            capture_logs=_kv_bool(env, "VITRA_GARDEN_CAPTURE_LOGS", True),
            capture_configs_hash_only=_kv_bool(env, "VITRA_GARDEN_CONFIG_HASH_ONLY", True),
            publish_landing_page=_kv_bool(env, "VITRA_GARDEN_PUBLISH_LANDING", True),
            publish_downloads=_kv_bool(env, "VITRA_GARDEN_PUBLISH_DOWNLOADS", True),
            publish_genesis=_kv_bool(env, "VITRA_GARDEN_PUBLISH_GENESIS", True),
            publish_self=_kv_bool(env, "VITRA_GARDEN_PUBLISH_SELF", False),
            publish_bundle=_kv_bool(env, "VITRA_GARDEN_PUBLISH_BUNDLE", False),
            force_publish=_kv_bool(env, "VITRA_GARDEN_FORCE_PUBLISH", False),
            dry_run=_kv_bool(env, "VITRA_GARDEN_DRY_RUN", False),
            apply_policy_baseline=_kv_bool(env, "VITRA_GARDEN_APPLY_POLICY", False),
            admin_cidr=_env_get(env, "VITRA_GARDEN_ADMIN_CIDR", "192.168.8.0/24"),
            training_enabled=_kv_bool(env, "VITRA_GARDEN_TRAINING", True),
            training_scenarios=_env_get(env, "VITRA_GARDEN_TRAINING_SCENARIOS", "airlift_ram,vpn_stranger,log_poison"),
        )


# ---- SSH primitive -----------------------------------------------------------

class _SSH:
    def __init__(self, d: GardenDeclared):
        if not HAVE_PARAMIKO:
            raise RuntimeError("paramiko_missing")
        self.d = d
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    def __enter__(self) -> "_SSH":
        kwargs: Dict[str, Any] = dict(
            hostname=self.d.router_host,
            port=self.d.router_port,
            username=self.d.router_user,
            timeout=self.d.timeout_s,
            banner_timeout=self.d.timeout_s,
            auth_timeout=self.d.timeout_s,
            allow_agent=True,
            look_for_keys=True,
        )
        if self.d.password:
            kwargs["password"] = self.d.password
        if self.d.keyfile:
            kwargs["key_filename"] = self.d.keyfile
        self.client.connect(**kwargs)
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        try:
            self.client.close()
        except Exception:
            pass

    def run(self, cmd: str) -> JSONDict:
        ts = _utc_iso()
        try:
            _, stdout, stderr = self.client.exec_command(cmd)
            out = stdout.read().decode("utf-8", errors="replace")
            err = stderr.read().decode("utf-8", errors="replace")
            rc = stdout.channel.recv_exit_status()
            return {"ts": ts, "cmd": cmd, "rc": int(rc), "out": out, "err": err}
        except Exception as e:
            return {"ts": ts, "cmd": cmd, "rc": 255, "out": "", "err": f"{type(e).__name__}:{e}"}

    def write_file(self, remote_path: str, content: str, *, mode: Optional[str] = None) -> JSONDict:
        ts = _utc_iso()
        safe = content.replace("\r\n", "\n")
        try:
            sftp = self.client.open_sftp()
            tmp_path = remote_path + ".vitra_tmp"
            with sftp.open(tmp_path, "w") as f:
                f.write(safe)
            if mode:
                try:
                    sftp.chmod(tmp_path, int(mode, 8))
                except Exception:
                    pass
            sftp.rename(tmp_path, remote_path)
            sftp.close()
            return {"ts": ts, "path": remote_path, "rc": 0, "method": "sftp", "err": ""}
        except Exception:
            cmd = f"cat > {remote_path} <<'VITRA_EOF'\n{safe}\nVITRA_EOF\n"
            r = self.run(cmd)
            if mode:
                self.run(f"chmod {mode} {remote_path} >/dev/null 2>&1 || true")
            return {"ts": ts, "path": remote_path, "rc": int(r.get("rc", 255)), "method": "heredoc", "err": r.get("err", "")}


# ---- collectors --------------------------------------------------------------

def _etc_config_hashes_cmd() -> str:
    return (
        r"if command -v sha256sum >/dev/null 2>&1; then "
        r"  find /etc/config -maxdepth 1 -type f -exec sha256sum {} \; 2>/dev/null | sort; "
        r"elif command -v md5sum >/dev/null 2>&1; then "
        r"  find /etc/config -maxdepth 1 -type f -exec md5sum {} \; 2>/dev/null | sort; "
        r"else "
        r"  ls -la /etc/config 2>/dev/null || true; "
        r"fi"
    )


COLLECTORS: List[Tuple[str, str, bool]] = [
    ("openwrt_release", "cat /etc/openwrt_release 2>/dev/null || true", False),
    ("system_board", "ubus call system board 2>/dev/null || cat /tmp/sysinfo/board_name 2>/dev/null || true", False),
    ("netif_dump", "ubus call network.interface dump 2>/dev/null || true", False),
    ("routes", "ip route 2>/dev/null || route -n 2>/dev/null || true", False),
    ("routes6", "ip -6 route 2>/dev/null || true", False),
    ("ip6_addr", "ip -6 addr 2>/dev/null || true", False),
    ("firewall_uci_zones", "uci show firewall 2>/dev/null | sed -n '1,240p' || true", False),
    ("uhttpd_uci", "uci show uhttpd 2>/dev/null | sed -n '1,240p' || true", False),
    ("listen_sockets_head", "ss -lntup 2>/dev/null | sed -n '1,120p' || netstat -lntup 2>/dev/null | sed -n '1,120p' || true", False),
    ("wg_dump_if_present", "command -v wg >/dev/null 2>&1 && wg show all dump 2>/dev/null || true", False),
    ("logread_tail", "logread 2>/dev/null | tail -n 200 || true", True),
    ("dmesg_tail", "dmesg 2>/dev/null | tail -n 200 || true", True),
]


# ---- local artifact discovery ------------------------------------------------

def _find_local_file(name: str) -> Optional[Path]:
    try:
        here = Path(__file__).resolve().parent
        candidates = [
            here / name,
            Path(os.environ.get("PROJECT_ROOT", str(here))).resolve() / name,
            Path.cwd() / name,
        ]
        seen = set()
        for c in candidates:
            try:
                r = c.resolve()
            except Exception:
                r = c
            if str(r) in seen:
                continue
            seen.add(str(r))
            if r.exists() and r.is_file():
                return r
    except Exception:
        pass
    return None


def _bootstrap_artifacts(declared: GardenDeclared) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []

    gateway = _find_local_file("gateway.sh")
    if declared.publish_downloads:
        if gateway is not None:
            items.append({
                "name": "gateway.sh",
                "remote_path": "/www/downloads/gateway.sh",
                "mode": "0755",
                "content": gateway.read_text(encoding="utf-8", errors="replace"),
                "local_path": str(gateway),
            })
        else:
            items.append({
                "name": "gateway.sh",
                "remote_path": "/www/downloads/gateway.sh",
                "mode": "0755",
                "content": "#!/bin/sh\n\necho 'gateway.sh not present on this chassis. Ask host for a fresh copy.'\n",
                "local_path": "",
            })

    if declared.publish_genesis:
        genesis = _find_local_file("genesis.py")
        if genesis is not None:
            items.append({
                "name": "genesis.py",
                "remote_path": "/www/downloads/genesis.py",
                "mode": "0644",
                "content": genesis.read_text(encoding="utf-8", errors="replace"),
                "local_path": str(genesis),
            })

    if declared.publish_self:
        me = _find_local_file("garden_of_chuzhoy.py")
        if me is not None:
            items.append({
                "name": "garden_of_chuzhoy.py",
                "remote_path": "/www/downloads/garden_of_chuzhoy.py",
                "mode": "0644",
                "content": me.read_text(encoding="utf-8", errors="replace"),
                "local_path": str(me),
            })

    if declared.publish_bundle:
        bundle = _find_local_file("vitra_bootstrap.tgz")
        if bundle is not None:
            items.append({
                "name": "vitra_bootstrap.tgz",
                "remote_path": "/www/downloads/vitra_bootstrap.tgz",
                "mode": "0644",
                "content_bytes_path": str(bundle),
                "local_path": str(bundle),
            })
    return items


# ---- cultivation: router landing + downloads --------------------------------

def _publish_landing_and_downloads(ssh: _SSH, *, declared: GardenDeclared) -> JSONDict:
    report: JSONDict = {
        "ts": _utc_iso(),
        "ok": True,
        "writes": [],
        "manifest": [],
        "preserve_remote_index": not declared.force_publish,
        "dry_run": bool(declared.dry_run),
    }

    if declared.dry_run:
        report["writes"].append({"path": "/www/downloads", "rc": 0, "note": "mkdir_skipped_dry_run"})
    else:
        ssh.run("mkdir -p /www/downloads >/dev/null 2>&1 || true")

    if declared.publish_landing_page:
        if declared.dry_run:
            report["writes"].append({"path": "/www/index.html", "rc": 0, "note": "write_skipped_dry_run"})
        else:
            preserve = ssh.run("test -f /www/index.html && echo yes || echo no")
            exists = (preserve.get("out", "") or "").strip() == "yes"
            if exists and not declared.force_publish:
                report["writes"].append({"path": "/www/index.html", "rc": 0, "note": "exists_preserved"})
            else:
                if exists:
                    ssh.run("cp /www/index.html /www/index.html.vitra_bak_$(date +%s) >/dev/null 2>&1 || true")
                r = ssh.write_file("/www/index.html", CANONICAL_INDEX_HTML, mode="0644")
                report["writes"].append({"path": "/www/index.html", "rc": r.get("rc"), "err": r.get("err", ""), "method": r.get("method", "")})

    for item in _bootstrap_artifacts(declared):
        manifest_entry: JSONDict = {
            "name": item["name"],
            "remote_path": item["remote_path"],
            "local_path": item.get("local_path", ""),
        }
        if "content" in item:
            manifest_entry["sha256"] = _sha256_text(item["content"])
            manifest_entry["sig16"] = _sha16_text(item["content"])
        elif item.get("content_bytes_path"):
            local_p = Path(str(item["content_bytes_path"]))
            manifest_entry["sha256"] = _sha256_file(local_p)
            manifest_entry["sig16"] = manifest_entry["sha256"][:16]

        if declared.dry_run:
            report["writes"].append({"path": item["remote_path"], "rc": 0, "note": "write_skipped_dry_run"})
            report["manifest"].append(manifest_entry)
            continue

        if "content" in item:
            r = ssh.write_file(item["remote_path"], item["content"], mode=item.get("mode"))
            report["writes"].append({"path": item["remote_path"], "rc": r.get("rc"), "err": r.get("err", ""), "method": r.get("method", "")})
            report["manifest"].append(manifest_entry)
        elif item.get("content_bytes_path"):
            # For binary bundle artifacts, prefer a staged base64-free approach using paramiko SFTP.
            try:
                sftp = ssh.client.open_sftp()
                remote_tmp = item["remote_path"] + ".vitra_tmp"
                sftp.put(str(item["content_bytes_path"]), remote_tmp)
                try:
                    sftp.chmod(remote_tmp, int(item.get("mode", "0644"), 8))
                except Exception:
                    pass
                sftp.rename(remote_tmp, item["remote_path"])
                sftp.close()
                report["writes"].append({"path": item["remote_path"], "rc": 0, "err": "", "method": "sftp-put"})
                report["manifest"].append(manifest_entry)
            except Exception as e:
                report["writes"].append({"path": item["remote_path"], "rc": 255, "err": f"{type(e).__name__}:{e}", "method": "sftp-put"})
                report["ok"] = False

    return report


# ---- policy application (safe baseline) -------------------------------------

def _apply_policy_baseline(ssh: _SSH, *, declared: GardenDeclared) -> JSONDict:
    """
    Additive, snapshot-first, mostly idempotent baseline.
    We avoid direct iptables assumptions and stay in UCI land.
    """
    ts = _utc_iso()
    snapshot_path = f"/root/vitra_snapshots/firewall_{int(time.time())}.uci"
    admin_cidr = declared.admin_cidr
    script = f"""
set -e
mkdir -p /root/vitra_snapshots >/dev/null 2>&1 || true
uci export firewall > {snapshot_path} 2>/dev/null || true

ensure_rule() {{
  local name="$1"
  local port="$2"
  local found=""
  found="$(uci show firewall 2>/dev/null | grep -F "name='$name'" || true)"
  if [ -n "$found" ]; then
    return 0
  fi
  local r
  r="$(uci add firewall rule)"
  uci set firewall.$r.name="$name"
  uci set firewall.$r.family='any'
  uci set firewall.$r.src='lan'
  uci set firewall.$r.src_ip='{admin_cidr}'
  uci set firewall.$r.dest_port="$port"
  uci set firewall.$r.proto='tcp'
  uci set firewall.$r.target='ACCEPT'
}}

ensure_rule vitraloc_admin_only_22 22
ensure_rule vitraloc_admin_only_80 80
ensure_rule vitraloc_admin_only_443 443

uci commit firewall
/etc/init.d/firewall reload || /etc/init.d/firewall restart || true
"""
    if declared.dry_run:
        return {
            "ts": ts,
            "attempted": False,
            "dry_run": True,
            "snapshot_path": snapshot_path,
            "note": "policy_skipped_dry_run",
        }
    r = ssh.run(script)
    return {
        "ts": ts,
        "attempted": True,
        "rc": int(r.get("rc", 255)),
        "err": r.get("err", ""),
        "snapshot_path": snapshot_path,
        "note": "snapshot_first_additive_baseline",
    }


# ---- training drills ---------------------------------------------------------

class TrainingScenario:
    name: str = "base"
    def run(self, witness_packet: JSONDict, *, ctx: Any = None, eden: Any = None) -> JSONDict:
        raise NotImplementedError


class AirliftRAMDrill(TrainingScenario):
    name = "airlift_ram"
    def run(self, witness_packet: JSONDict, *, ctx: Any = None, eden: Any = None) -> JSONDict:
        obs = witness_packet.get("observed", {}) or {}
        art = witness_packet.get("artifacts", {}) or {}
        declared = witness_packet.get("declared", {}) or {}

        rel = (obs.get("openwrt_release") or {}).get("out", "") or ""
        board = (obs.get("system_board") or {}).get("out", "") or ""

        netif_dump_raw = (obs.get("netif_dump") or {}).get("out", "") or ""
        netif = _maybe_json(netif_dump_raw)
        iface_names: List[str] = []
        try:
            if isinstance(netif, dict):
                for item in (netif.get("interface", []) or []):
                    n = item.get("interface")
                    if n:
                        iface_names.append(str(n))
        except Exception:
            pass

        capsule = {
            "kind": "airlift_capsule",
            "ts": _utc_iso(),
            "trust_class": declared.get("trust_class", "чужой"),
            "season": declared.get("season", "cultivation"),
            "summary": {
                "router_release_sig16": _sha16_text(rel.strip()) if rel.strip() else "",
                "board_sig16": _sha16_text(board.strip()) if board.strip() else "",
                "iface_count": int(len(iface_names)),
                "iface_names_head": iface_names[:12],
            },
            "hash_roots": {
                "etc_config_hash_root": str(art.get("etc_config_hash_root", "")),
                "garden_packet_sha256": str(art.get("garden_packet_sha256", "")),
            },
        }
        sig16 = _sha16_text(_safe_json(capsule))
        capsule["signature16"] = sig16
        capsule["capsule_id"] = f"airlift_{sig16}"

        result = {
            "scenario": self.name,
            "ts": _utc_iso(),
            "findings": {"capsule": capsule},
            "recommendations": [
                "Use this capsule for rapid cross-Vitra sync when ROM mass moves via metal.",
                "If signature16 changes unexpectedly, request a deeper garden witness on next safe cycle.",
                "Store capsules append-only; they are call-signs of state, not the state itself.",
            ],
            "evidence_refs": ["observed.openwrt_release", "observed.system_board", "observed.netif_dump", "artifacts.etc_config_hash_root"],
        }
        _eden_emit(eden, "garden_training", {"scenario": self.name, "result": result}, hashtags=["#GardenOfChuzhoy", "#training", "#airlift"])
        return result


class VPNStrangerSim(TrainingScenario):
    name = "vpn_stranger"
    def run(self, witness_packet: JSONDict, *, ctx: Any = None, eden: Any = None) -> JSONDict:
        obs = witness_packet.get("observed", {}) or {}
        ss_head = (obs.get("listen_sockets_head") or {}).get("out", "") or ""
        zones = (obs.get("firewall_uci_zones") or {}).get("out", "") or ""

        netif_dump_raw = (obs.get("netif_dump") or {}).get("out", "") or ""
        netif = _maybe_json(netif_dump_raw)

        wg_dump = (obs.get("wg_dump_if_present") or {}).get("out", "") or ""
        wg_present = bool(wg_dump.strip())
        wg_peers_hint = 0
        if wg_present:
            lines = [ln for ln in wg_dump.splitlines() if ln.strip()]
            wg_peers_hint = max(0, len(lines) - 1)

        iface_names: List[str] = []
        try:
            if isinstance(netif, dict):
                for item in (netif.get("interface", []) or []):
                    n = item.get("interface")
                    if n:
                        iface_names.append(str(n))
        except Exception:
            pass

        overlay_like = [n for n in iface_names if n.lower().startswith(("wg", "tun", "tap", "zt", "tailscale"))]

        findings = {
            "signals": {
                "overlay_like_interfaces": overlay_like,
                "interface_count": int(len(iface_names)),
                "listening_sockets_head_present": bool(ss_head.strip()),
                "firewall_zones_present": bool(zones.strip()),
                "wg_present": bool(wg_present),
                "wg_peer_lines_hint": int(wg_peers_hint),
            },
            "classification_rubric": [
                "IF a new overlay-like interface appears: classify as 'new transport surface'.",
                "IF listening sockets expand unexpectedly: classify as 'new exposure surface' (needs review).",
                "IF firewall zones unchanged but new interface appears: classify as 'routing drift risk'.",
                "Always: record, compare to last-known, and do not assume intent.",
            ],
        }

        result = {
            "scenario": self.name,
            "ts": _utc_iso(),
            "findings": findings,
            "recommendations": [
                "Keep overlay enablement a declared act so Eden can interpret change as intention vs drift.",
                "Prefer allow-listing peer keys and witnessing observed handshakes; treat all else as Unknown.",
            ],
            "evidence_refs": ["observed.netif_dump", "observed.listen_sockets_head", "observed.firewall_uci_zones", "observed.wg_dump_if_present"],
        }
        _eden_emit(eden, "garden_training", {"scenario": self.name, "result": result}, hashtags=["#GardenOfChuzhoy", "#training", "#vpn_stranger"])
        return result


class LogPoisonLab(TrainingScenario):
    name = "log_poison"
    def run(self, witness_packet: JSONDict, *, ctx: Any = None, eden: Any = None) -> JSONDict:
        obs = witness_packet.get("observed", {}) or {}
        logread = (obs.get("logread_tail") or {}).get("out", "") or ""
        dmesg = (obs.get("dmesg_tail") or {}).get("out", "") or ""

        s1, c1 = _sanitize_log_text(logread)
        s2, c2 = _sanitize_log_text(dmesg)

        findings = {
            "sanitization_needed": {"logread_tail": bool(c1), "dmesg_tail": bool(c2)},
            "recommended_dual_hash": {
                "logread_raw_sha256": _sha256_text(logread) if logread else "",
                "logread_sanitized_sha256": _sha256_text(s1) if logread else "",
                "dmesg_raw_sha256": _sha256_text(dmesg) if dmesg else "",
                "dmesg_sanitized_sha256": _sha256_text(s2) if dmesg else "",
            },
        }

        result = {
            "scenario": self.name,
            "ts": _utc_iso(),
            "findings": findings,
            "recommendations": [
                "Store raw-hash and sanitized-hash for critical logs (two lenses).",
                "Corroborate suspicious log events with other surfaces (netif dump, config hash roots).",
            ],
            "evidence_refs": ["observed.logread_tail", "observed.dmesg_tail"],
        }
        _eden_emit(eden, "garden_training", {"scenario": self.name, "result": result}, hashtags=["#GardenOfChuzhoy", "#training", "#log_poison"])
        return result


SCENARIOS: Dict[str, TrainingScenario] = {
    "airlift_ram": AirliftRAMDrill(),
    "vpn_stranger": VPNStrangerSim(),
    "log_poison": LogPoisonLab(),
}


# ---- helpers ----------------------------------------------------------------

def _collect_router_state(ssh: _SSH, *, declared: GardenDeclared, eden: Any = None) -> Tuple[JSONDict, JSONDict, JSONDict]:
    observed: JSONDict = {}
    unknown: JSONDict = {}
    artifacts: JSONDict = {}

    cfg_cmd = _etc_config_hashes_cmd()
    cfg_r = ssh.run(cfg_cmd)
    cfg_out = (cfg_r.get("out", "") or "")
    cfg_err = (cfg_r.get("err", "") or "")
    cfg_rc = int(cfg_r.get("rc", 255))
    if cfg_rc == 0 or cfg_out.strip() or cfg_err.strip():
        observed["etc_config_hashes"] = {"ts": cfg_r["ts"], "cmd": cfg_cmd, "rc": cfg_rc, "out": cfg_out, "err": cfg_err}
        artifacts["etc_config_hash_root"] = _sha256_text(cfg_out.strip()) if cfg_out.strip() else ""
    else:
        unknown["etc_config_hashes"] = {"ts": cfg_r["ts"], "cmd": cfg_cmd, "rc": cfg_rc, "err": cfg_err}

    for name, cmd, sanitize in COLLECTORS:
        r = ssh.run(cmd)
        out = (r.get("out", "") or "")
        err = (r.get("err", "") or "")
        rc = int(r.get("rc", 255))

        if sanitize:
            out2, changed = _sanitize_log_text(out)
            if changed:
                _eden_emit(eden, "log_sanitized", {"source": name, "note": "sanitized_or_truncated"}, hashtags=["#GardenOfChuzhoy", "#log_sanitized"])
            out = out2

        if out.strip() or err.strip() or rc == 0:
            observed[name] = {"ts": r["ts"], "cmd": cmd, "rc": rc, "out": out, "err": err}
        else:
            unknown[name] = {"ts": r["ts"], "cmd": cmd, "rc": rc, "err": err}

    return observed, unknown, artifacts


def _finalize_packet(
    packet: JSONDict,
    *,
    declared: GardenDeclared,
    librarian: Any,
    ctx: Any = None,
    fx: Any = None,
    eden: Any = None,
) -> JSONDict:
    packet.setdefault("artifacts", {})
    packet["artifacts"]["garden_packet_sha256"] = _sha256_text(_safe_json({
        "kind": packet.get("kind"),
        "version": packet.get("version"),
        "ts": packet.get("ts"),
        "declared": packet.get("declared"),
        "observed": packet.get("observed"),
        "unknown": packet.get("unknown"),
        "cultivation": packet.get("cultivation"),
    }))

    results: JSONDict = {}
    if declared.training_enabled:
        requested = [x.strip() for x in (declared.training_scenarios or "").split(",") if x.strip()]
        for name in requested:
            sc = SCENARIOS.get(name)
            if sc is None:
                continue
            try:
                results[name] = sc.run(packet, ctx=ctx, eden=eden)
            except Exception as e:
                results[name] = {
                    "scenario": name,
                    "ts": _utc_iso(),
                    "findings": {"error": f"{type(e).__name__}:{e}"},
                    "recommendations": ["Treat this as Unknown; fix the drill before trusting its outputs."],
                    "evidence_refs": [],
                }
    packet["training"] = results
    packet["eden_attachment"] = _make_eden_attachment(packet)

    # Compact receipt for downstream ingestion.
    try:
        att = packet.get("eden_attachment", {}) or {}
        receipt = {
            "kind": "garden_run_receipt",
            "organ": "garden_of_chuzhoy",
            "version": VERSION,
            "ts": packet.get("ts", _utc_iso()),
            "router": (att.get("router") or {}),
            "week_anchor": str((packet.get("declared") or {}).get("week_anchor", "")),
            "sig16": str((att.get("signatures") or {}).get("garden_packet_sha256", ""))[:16],
            "config_hash_root": str((att.get("signatures") or {}).get("etc_config_hash_root", "")),
            "openwrt_release_sig16": str((att.get("signatures") or {}).get("openwrt_release_sig16", "")),
        }
        receipt["sha256"] = _sha256_text(_safe_json(receipt))
        packet["artifacts"]["garden_run_receipt"] = receipt
    except Exception:
        pass

    witness_sig = _librarian_record(librarian, kind="witness_packet", payload=packet["eden_attachment"])
    if librarian is not None:
        try:
            if hasattr(librarian, "catalog_artifact"):
                etc_root = str(packet.get("artifacts", {}).get("etc_config_hash_root", "") or "")
                if etc_root:
                    librarian.catalog_artifact(
                        locator="openwrt:/etc/config/* (hash_root)",
                        artifact_kind="openwrt_config_hash_root",
                        sig16=_sha16_text("etc_config_hash_root|" + etc_root),
                        meta={"hash_root": etc_root},
                        witness_sig16=witness_sig,
                    )
                manifest = (packet.get("cultivation", {}).get("publish", {}) or {}).get("manifest", []) or []
                for item in manifest:
                    librarian.catalog_artifact(
                        locator=f"openwrt:{item.get('remote_path','')}",
                        artifact_kind="garden_bootstrap_artifact",
                        sig16=str(item.get("sig16", "")),
                        meta={"name": item.get("name", ""), "sha256": item.get("sha256", ""), "version": VERSION},
                        witness_sig16=witness_sig,
                    )
        except Exception:
            pass

    _eden_emit(eden, "garden_witness_bundle", {"garden": packet["eden_attachment"], "artifacts": packet.get("artifacts", {})}, hashtags=["#GardenOfChuzhoy", "#witness"])
    if fx is not None:
        try:
            fx.step("garden_witness", eden_attachment=packet["eden_attachment"], hashtags=["#GardenOfChuzhoy", "#witness"])
        except Exception:
            pass
    return packet


# ---- public entrypoint -------------------------------------------------------

def garden_witness(ctx: Any = None, *, fx: Any = None, eden: Any = None, declared_override: Optional[GardenDeclared] = None) -> JSONDict:
    env = dict(os.environ)
    declared = declared_override or GardenDeclared.from_env(env)
    librarian = _boot_librarian()

    packet: JSONDict = {
        "kind": declared.kind,
        "version": VERSION,
        "ts": _utc_iso(),
        "declared": dc.asdict(declared),
        "authority": {"schema": "none", "organ": "garden_of_chuzhoy"},
        "observed": {},
        "unknown": {},
        "artifacts": {},
        "cultivation": {},
        "training": {},
        "eden_attachment": {},
        "hashtags": [
            "#GardenOfChuzhoy", "#chuzhoy", "#openwrt", "#ac1750",
            "#declared", "#observed", "#unknown", "#forensics",
            "#cultivation", "#harvest", "#courtyard",
        ],
    }

    _eden_emit(eden, "membrane_declared", {"garden_declared": packet["declared"]}, hashtags=["#GardenOfChuzhoy", "#declared"])
    _librarian_record(librarian, kind="garden_declared", payload={"declared": packet["declared"], "ts": packet["ts"]})

    if not HAVE_PARAMIKO:
        packet["unknown"]["ssh"] = "paramiko_missing"
        return _finalize_packet(packet, declared=declared, librarian=librarian, ctx=ctx, fx=fx, eden=eden)

    try:
        with _SSH(declared) as ssh:
            if declared.publish_landing_page or declared.publish_downloads or declared.publish_genesis or declared.publish_self or declared.publish_bundle:
                try:
                    packet["cultivation"]["publish"] = _publish_landing_and_downloads(ssh, declared=declared)
                except Exception as e:
                    packet["cultivation"]["publish_error"] = f"{type(e).__name__}:{e}"

            if declared.apply_policy_baseline:
                try:
                    packet["cultivation"]["policy_baseline"] = _apply_policy_baseline(ssh, declared=declared)
                except Exception as e:
                    packet["cultivation"]["policy_baseline_error"] = f"{type(e).__name__}:{e}"

            observed, unknown, artifacts = _collect_router_state(ssh, declared=declared, eden=eden)
            packet["observed"] = observed
            packet["unknown"] = unknown
            packet["artifacts"].update(artifacts)

    except Exception as e:
        packet["unknown"]["ssh_connect"] = f"{type(e).__name__}:{e}"

    return _finalize_packet(packet, declared=declared, librarian=librarian, ctx=ctx, fx=fx, eden=eden)


def _make_eden_attachment(garden_packet: JSONDict) -> JSONDict:
    declared = garden_packet.get("declared", {}) or {}
    art = garden_packet.get("artifacts", {}) or {}
    obs = garden_packet.get("observed", {}) or {}
    cult = garden_packet.get("cultivation", {}) or {}

    rel = (obs.get("openwrt_release") or {}).get("out", "") or ""
    board = (obs.get("system_board") or {}).get("out", "") or ""

    publish_manifest = ((cult.get("publish") or {}).get("manifest", []) or [])

    attachment: JSONDict = {
        "kind": "garden_attachment",
        "ts": garden_packet.get("ts", _utc_iso()),
        "version": garden_packet.get("version", VERSION),
        "trust_class": str(declared.get("trust_class", "чужой")),
        "season": str(declared.get("season", "cultivation")),
        "week_anchor": str(declared.get("week_anchor", "")),
        "node_class": str(declared.get("node_class", "courtyard")),
        "uplink_class": str(declared.get("uplink_class", "dynamic")),
        "peer_posture": str(declared.get("peer_posture", "disabled")),
        "router": {"host": str(declared.get("router_host", "")), "port": int(declared.get("router_port", 22) or 22)},
        "signatures": {
            "garden_packet_sha256": str(art.get("garden_packet_sha256", "")),
            "etc_config_hash_root": str(art.get("etc_config_hash_root", "")),
            "openwrt_release_sig16": _sha16_text(rel.strip()) if rel.strip() else "",
            "system_board_sig16": _sha16_text(board.strip()) if board.strip() else "",
            "canonical_index_sig16": _sha16_text(CANONICAL_INDEX_HTML),
        },
        "cultivation": {
            "landing_published": bool((cult.get("publish") or {}).get("writes")),
            "policy_attempted": bool(cult.get("policy_baseline")),
            "dry_run": bool(declared.get("dry_run", False)),
            "published_manifest": publish_manifest,
        },
        "training_scenarios": sorted(list((garden_packet.get("training") or {}).keys())),
    }
    attachment["signature16"] = _sha16_text(_safe_json(attachment))
    return attachment


# =============================================================================
# Loop (the __main__ demonstrative workflow)
# =============================================================================

def _parse_args(argv: List[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Adopt a fresh OpenWrt router into a Garden of Chuzhoy node.")
    p.add_argument("--router", default=os.environ.get("VITRA_GARDEN_HOST", ""), help="Router host/IP")
    p.add_argument("--user", default=os.environ.get("VITRA_GARDEN_USER", ""), help="Router SSH user")
    p.add_argument("--port", type=int, default=int(os.environ.get("VITRA_GARDEN_PORT", "22") or "22"), help="Router SSH port")
    p.add_argument("--apply-policy", action="store_true", help="Apply baseline admin firewall policy")
    p.add_argument("--dry-run", action="store_true", help="Witness and plan without remote mutation")
    p.add_argument("--force-publish", action="store_true", help="Overwrite remote /www/index.html instead of preserving it")
    p.add_argument("--node-class", choices=["courtyard", "sister", "hub", "lab-only"], default=os.environ.get("VITRA_GARDEN_NODE_CLASS", "courtyard"))
    p.add_argument("--uplink-class", choices=["offline", "dynamic", "static"], default=os.environ.get("VITRA_GARDEN_UPLINK_CLASS", "dynamic"))
    p.add_argument("--peer-posture", choices=["disabled", "outbound_only", "bidirectional"], default=os.environ.get("VITRA_GARDEN_PEER_POSTURE", "disabled"))
    return p.parse_args(argv)


def main(argv: List[str]) -> int:
    args = _parse_args(argv)
    local_report = ensure_local_index_html(folder=Path.cwd())

    if args.router:
        os.environ["VITRA_GARDEN_HOST"] = args.router
    if args.user:
        os.environ["VITRA_GARDEN_USER"] = args.user
    os.environ["VITRA_GARDEN_PORT"] = str(args.port)
    if args.apply_policy:
        os.environ["VITRA_GARDEN_APPLY_POLICY"] = "1"
    if args.dry_run:
        os.environ["VITRA_GARDEN_DRY_RUN"] = "1"
    if args.force_publish:
        os.environ["VITRA_GARDEN_FORCE_PUBLISH"] = "1"
    os.environ["VITRA_GARDEN_NODE_CLASS"] = args.node_class
    os.environ["VITRA_GARDEN_UPLINK_CLASS"] = args.uplink_class
    os.environ["VITRA_GARDEN_PEER_POSTURE"] = args.peer_posture

    pkt = garden_witness(ctx=None, fx=None, eden=None)
    try:
        att = pkt.get("eden_attachment", {}) or {}
        att["local_index_html"] = local_report
        print(_safe_json(att))
    except Exception:
        print(_safe_json(pkt.get("eden_attachment", {})))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
