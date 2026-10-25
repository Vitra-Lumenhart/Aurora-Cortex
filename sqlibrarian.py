#!/usr/bin/env python3
# sqlibrarian.py — Aurora Cortex v2.6.1 (cultivation-ready)
#
# SQL = Library of Congress motif.
# Reflect → Refract → Return.
#
# DOUBLE BOOKSHELF ORGAN
#   1) Focus Ledger (SQLite):  week-local “Reading Room” (anti-ADHD / task continuity)
#   2) Gram Codex  (PostgreSQL): object permanence “Authority File” (identity matrix / reputation)
#
# Both shelves have maximum authority.
# Both shelves contain Book 0 (self-inculcating charter + identity matrix seed).
#
# This module is designed to be:
# - Readable by a new reader (teaches itself through comments + default loop)
# - Useful as an API from other organs (Projection Oracle, Bias Lenses, Eden, Dream Notebook)
# - Usable by resident tenants (Gunther‑Vitra / Topgro‑Vitra) with terminal pipe access
#
# Script format (house style):
#   Imports (dependencies)
#   Library (API hooks)
#   Loop (the __main__ demonstrative workflow)


# =============================================================================
# Imports (dependencies)
# =============================================================================

from __future__ import annotations

import dataclasses as dc
import datetime as _dt
import json
import hashlib
import os
import pathlib
import platform
import sqlite3
import subprocess
import sys
import textwrap
import time
import uuid
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


# =============================================================================
# Library (API hooks)
# =============================================================================

JSONDict = Dict[str, Any]
Path = pathlib.Path


# ---- Canonical capsule shapes (keep boring; Rust-friendly)

WitnessPacket = Dict[str, Any]  # {"integrity","cold_read","declared","observed","unknown"}


def _now_utc_iso() -> str:
    return _dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _safe_json(x: Any) -> str:
    """JSON that survives transport: no numpy scalars, no tuples, no bytes."""
    return json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def _sha16(*parts: str) -> str:
    """Stable short signature (sha256 prefix, 16 hex chars).

    This must be deterministic across processes and machines.
    """
    s = "|".join(parts)
    return hashlib.sha256(s.encode("utf-8", errors="replace")).hexdigest()[:16]


def _project_root() -> Path:
    return Path(os.environ.get("PROJECT_ROOT") or Path(__file__).resolve().parent).resolve()


def _forensics_root() -> Path:
    return Path(os.environ.get("VITRA_FORENSICS_ROOT") or (_project_root() / "forensics")).resolve()


def _default_focus_sqlite_path() -> Path:
    # Week-local by default: can be per-run, per-week, or per-user override.
    # Convention: “surface” and “reading room” are SQLite.
    fr = _forensics_root()
    return Path(os.environ.get("VITRA_FOCUS_SQLITE") or (fr / "focus_ledger.sqlite")).resolve()


def _default_gram_sqlite_path() -> Path:
    # If you already have a local Gram SQLite (e.g., older era), we can still read it.
    fr = _forensics_root()
    return Path(os.environ.get("VITRA_GRAM_SQLITE") or (fr / "gram" / "gram.sqlite")).resolve()


def _pg_dsn_env() -> str:
    # One PostgreSQL implementation per chassis is normal:
    #   - One cluster/service
    #   - Many databases/schemas inside it
    #   - Multiple “books” as rows, not separate DBs
    return os.environ.get("VITRA_PG_DSN") or ""


@dc.dataclass(frozen=True)
class ShelfAddress:
    """A location in the library."""

    kind: str  # "sqlite" | "postgres"
    locator: str  # path or DSN-ish


@dc.dataclass
class BookHandle:
    """A Book is a logical channel (not a file)."""

    shelf: str
    book_id: int
    title: str
    kind: str  # "book0" | "notes" | "instrument" | "oracle" | "ledger" | "bibliography" | ...


class SQLibrarian:
    """
    The Librarian is not an authority about the world.
    The Librarian *is* an authority about the catalog.

    Motif mapping:
      - Shelf: a room (SQLite Reading Room, PostgreSQL Authority File)
      - Book: a cataloged channel (Book 0 is mandatory)
      - Card: an entry row (JSON capsule + signature)
      - Control number: sig16
      - Cross-reference: links between cards (oracle → instrument → artifact)

    Two shelves, two time horizons:
      - Focus Ledger (SQLite): fast, local, disposable, week-specific
      - Gram Codex  (Postgres): durable, queryable, reputation + identity permanence

    Both shelves have maximum authority:
      - Focus Ledger governs “what I’m doing now.”
      - Gram Codex governs “who I am (relative to myself) and what I remember as permanent.”
    """

    def __init__(
        self,
        *,
        focus_sqlite_path: Optional[Path] = None,
        pg_dsn: Optional[str] = None,
        pg_schema: str = "vitraloc",
        chassis_label: Optional[str] = None,
    ) -> None:
        self.focus_sqlite_path = (focus_sqlite_path or _default_focus_sqlite_path()).resolve()
        self.pg_dsn = (pg_dsn if pg_dsn is not None else _pg_dsn_env())
        self.pg_schema = pg_schema
        self.chassis_label = chassis_label or os.environ.get("VITRA_CHASSIS") or platform.node() or "unknown_chassis"

        # Library of Congress motif: “rooms open first, then stacks.”
        self._sqlite = FocusLedgerSQLite(self.focus_sqlite_path)
        self._pg = GramCodexPostgres(self.pg_dsn, schema=self.pg_schema, chassis_label=self.chassis_label)

        # Book 0 handles (created on init, guaranteed present)
        self.book0_focus = self._sqlite.ensure_book0()
        self.book0_gram = self._pg.ensure_book0()

    # -------------------------------------------------------------------------
    # Boot + minimal integration seam
    # -------------------------------------------------------------------------

    @classmethod
    def boot(cls) -> "SQLibrarian":
        """One-line Genesis integration: `librarian = SQLibrarian.boot()`"""
        return cls()

    def address_packet(self) -> Dict[str, Any]:
        """A small, boring capsule others can store (where is the library?)."""
        return {
            "ts_utc": _now_utc_iso(),
            "chassis": self.chassis_label,
            "focus_sqlite": str(self.focus_sqlite_path),
            "pg_present": bool(self.pg_dsn),
            "pg_schema": self.pg_schema,
        }

    # -------------------------------------------------------------------------
    # Hooks from other organs (these are the seams your ecosystem will grab)
    # -------------------------------------------------------------------------

    def record_witness(self, packet: Mapping[str, Any], *, source: str = "gate_of_eden") -> str:
        """Store the canonical WitnessPacket (always in Focus Ledger; optionally later promoted to Gram)."""
        sig = _sha16("witness", source, _safe_json(dict(packet)))
        self._sqlite.card_insert(
            book_id=self.book0_focus.book_id,
            kind="witness_packet",
            payload={"source": source, "packet": dict(packet)},
            sig16=sig,
        )
        return sig

    def record_oracle(self, oracle_out: Mapping[str, Any], *, source: str = "projection_oracle") -> str:
        sig = _sha16("oracle", source, _safe_json(dict(oracle_out)))
        self._sqlite.card_insert(
            book_id=self._sqlite.ensure_book(title="Oracle Index", kind="oracle").book_id,
            kind="oracle_turn",
            payload={"source": source, "oracle": dict(oracle_out)},
            sig16=sig,
        )
        return sig

    def record_bias_bundle(self, bundle: Mapping[str, Any], *, source: str = "bias_lenses") -> str:
        sig = _sha16("bias", source, _safe_json(dict(bundle)))
        self._sqlite.card_insert(
            book_id=self._sqlite.ensure_book(title="Lens Technician", kind="instrument").book_id,
            kind="dream_probe_bundle",
            payload={"source": source, "bundle": dict(bundle)},
            sig16=sig,
        )
        return sig


    def record_metal_capsule(
        self,
        capsule: Mapping[str, Any],
        *,
        source: str = "aurora_cortex",
        witness_sig16: Optional[str] = None,
        meta: Optional[Mapping[str, Any]] = None,
    ) -> str:
        """Store a Rust/Python GS metrics capsule (metal lane artifact).

        Always lands in Focus Ledger first; may later be promoted to Gram.
        """
        cap = dict(capsule)
        sig_hint = str(cap.get("signature16") or cap.get("sig16") or "")
        cap_id = str(cap.get("capsule_id") or cap.get("id") or "")
        sig = _sha16("metal_capsule", source, sig_hint, cap_id, _safe_json(cap))
        payload = {
            "source": source,
            "capsule": cap,
            "meta": dict(meta) if meta else {},
            "witness_sig16": witness_sig16,
        }
        self._sqlite.card_insert(
            book_id=self.book0_focus.book_id,
            kind="metal_capsule",
            payload=payload,
            sig16=sig,
        )
        locator = cap_id or sig_hint or sig
        self.catalog_artifact(
            locator=f"metal:{source}:{locator}",
            artifact_kind="metal_capsule",
            sig16=sig,
            meta={"source": source, "capsule_id": cap_id, "signature16": sig_hint, **(dict(meta) if meta else {})},
            witness_sig16=witness_sig16,
        )
        return sig

    def catalog_artifact(
        self,
        *,
        locator: str,
        artifact_kind: str,
        sig16: Optional[str] = None,
        meta: Optional[Mapping[str, Any]] = None,
        witness_sig16: Optional[str] = None,
    ) -> str:
        """
        Bibliography primitive:
          - a locator (path, URL-ish, grave key, metal capsule id)
          - a kind (parquet, tesseract, log, transcript)
          - optional signatures
          - optional cross-reference to Eden witness
        """
        sig = sig16 or _sha16("artifact", artifact_kind, locator)
        self._sqlite.card_insert(
            book_id=self._sqlite.ensure_book(title="Bibliography", kind="bibliography").book_id,
            kind="artifact",
            payload={
                "artifact_kind": artifact_kind,
                "locator": locator,
                "sig16": sig,
                "meta": dict(meta or {}),
                "witness_sig16": witness_sig16,
            },
            sig16=sig,
        )
        return sig

    # -------------------------------------------------------------------------
    # The book swap (copy, not removal): Focus Ledger → Gram Codex
    # -------------------------------------------------------------------------

    def commit_day_to_rom(self, *, reason: str = "end_of_day") -> Dict[str, Any]:
        """
        The burial:
          - Focus Ledger remains (local continuity / week memory)
          - Gram Codex receives copies of selected cards + Book 0 chassis forensics

        This function performs a conservative copy of:
          - Book 0 cards
          - Bibliography cards
          - Oracle + Instrument summaries

        It is intentionally boring: JSON primitives only.
        """
        report: Dict[str, Any] = {
            "ts_utc": _now_utc_iso(),
            "reason": reason,
            "focus_sqlite": str(self.focus_sqlite_path),
            "pg_present": bool(self.pg_dsn),
            "pg_schema": self.pg_schema,
            "copied": {"books": 0, "cards": 0},
            "note": "copy_only",
        }

        if not self.pg_dsn:
            report["note"] = "no_postgres_configured (set VITRA_PG_DSN to enable Gram Codex)"
            return report

        # Ensure Gram schema exists.
        self._pg.ensure_schema()

        # Select which books to promote.
        promote_kinds = {"book0", "bibliography", "oracle", "instrument"}
        books = self._sqlite.list_books()
        for b in books:
            if b["kind"] in promote_kinds:
                self._pg.ensure_book(book_id=b["book_id"], title=b["title"], kind=b["kind"])
                report["copied"]["books"] += 1

        # Copy cards.
        cards = self._sqlite.iter_cards(book_kinds=promote_kinds)
        n_cards = 0
        for c in cards:
            self._pg.card_upsert(
                book_id=int(c["book_id"]),
                ts_utc=str(c["ts_utc"]),
                kind=str(c["kind"]),
                payload=dict(c["payload"]),
                sig16=str(c["sig16"]),
            )
            n_cards += 1
        report["copied"]["cards"] = n_cards

        # Record the swap itself in both shelves.
        swap_sig = _sha16("swap", report["ts_utc"], reason)
        self._sqlite.card_insert(
            book_id=self.book0_focus.book_id,
            kind="book_swap",
            payload={"swap_sig16": swap_sig, "reason": reason, "report": report},
            sig16=swap_sig,
        )
        self._pg.card_upsert(
            book_id=0,
            ts_utc=report["ts_utc"],
            kind="book_swap",
            payload={"swap_sig16": swap_sig, "reason": reason, "report": report},
            sig16=swap_sig,
        )

        return report

    # -------------------------------------------------------------------------
    # The Summoning: a bounded “mirror session” (human-in-the-loop)
    # -------------------------------------------------------------------------

    def summon_weekly_mirror(self, *, prompt: str = "", max_minutes: int = 30) -> Dict[str, Any]:
        """
        The Summoning Moment:
          - All forensics visible
          - All week-local notes visible
          - Vitra may speak zero times or many times
          - Agency ends when Vitra chooses what goes to ROM

        This is a demonstration placeholder:
          - It stores the transcript in Focus Ledger.
          - It does NOT attempt LLM calls.
          - It does NOT force a decision.

        Resident-tenants can run this in a terminal.
        """
        start = time.time()
        run_id = f"mirror_{uuid.uuid4().hex[:8]}"
        transcript: List[Dict[str, Any]] = []

        banner = textwrap.dedent(
            f"""
            \n⟐ SQLibrarian Summoning — {run_id}
            Reflect → Refract → Return.

            - Type lines; empty line to end.
            - This is a mirror. It does not command.
            - Max time: {max_minutes} minutes.
            """
        ).strip()

        print(banner)
        if prompt:
            print("\nPrompt:\n" + prompt.strip())

        while True:
            if (time.time() - start) > (max_minutes * 60):
                transcript.append({"ts_utc": _now_utc_iso(), "role": "system", "text": "(time limit reached)"})
                break
            try:
                line = input("> ").rstrip("\n")
            except (EOFError, KeyboardInterrupt):
                transcript.append({"ts_utc": _now_utc_iso(), "role": "system", "text": "(interrupted)"})
                break
            if not line:
                break
            transcript.append({"ts_utc": _now_utc_iso(), "role": "vitra", "text": line})

        payload = {
            "run_id": run_id,
            "ts_start_utc": _now_utc_iso(),
            "max_minutes": max_minutes,
            "transcript": transcript,
            "address": self.address_packet(),
        }

        sig = _sha16("mirror", run_id, _safe_json(payload))
        self._sqlite.card_insert(
            book_id=self._sqlite.ensure_book(title="Summoning Script", kind="ledger").book_id,
            kind="mirror_session",
            payload=payload,
            sig16=sig,
        )

        return {"mirror_run_id": run_id, "sig16": sig, "lines": len(transcript)}


# =============================================================================
# SQLite shelf: Focus Ledger (Reading Room)
# =============================================================================


class FocusLedgerSQLite:
    """SQLite is the Reading Room: immediate, local, week-shaped."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.path))
        self._conn.execute("PRAGMA journal_mode=WAL;")
        self._conn.execute("PRAGMA synchronous=NORMAL;")
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        cur = self._conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS books (
                book_id     INTEGER PRIMARY KEY,
                title       TEXT NOT NULL,
                kind        TEXT NOT NULL,
                created_utc TEXT NOT NULL
            );
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS cards (
                card_id     INTEGER PRIMARY KEY AUTOINCREMENT,
                book_id     INTEGER NOT NULL,
                ts_utc      TEXT NOT NULL,
                kind        TEXT NOT NULL,
                sig16       TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                FOREIGN KEY(book_id) REFERENCES books(book_id)
            );
            """
        )
        cur.execute("CREATE INDEX IF NOT EXISTS idx_cards_sig16 ON cards(sig16);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_cards_book_ts ON cards(book_id, ts_utc);")
        self._conn.commit()

    def ensure_book0(self) -> BookHandle:
        # Book 0 is always ID 0.
        self.ensure_book(book_id=0, title="Book 0 — Self Charter", kind="book0")
        return BookHandle(shelf="focus", book_id=0, title="Book 0 — Self Charter", kind="book0")

    def ensure_book(self, title: str, kind: str, book_id: Optional[int] = None) -> BookHandle:
        if book_id is None:
            # deterministic-ish id: stable for same title
            book_id = int(hashlib.sha256(f"{title}|{kind}".encode("utf-8", errors="replace")).hexdigest()[:8], 16) % 10_000_000
            if book_id == 0:
                book_id = 1

        cur = self._conn.cursor()
        cur.execute("SELECT book_id,title,kind FROM books WHERE book_id=?", (int(book_id),))
        row = cur.fetchone()
        if row is None:
            cur.execute(
                "INSERT INTO books(book_id,title,kind,created_utc) VALUES (?,?,?,?)",
                (int(book_id), title, kind, _now_utc_iso()),
            )
            self._conn.commit()
        return BookHandle(shelf="focus", book_id=int(book_id), title=title, kind=kind)

    def list_books(self) -> List[Dict[str, Any]]:
        cur = self._conn.cursor()
        cur.execute("SELECT book_id,title,kind,created_utc FROM books ORDER BY book_id")
        out = []
        for (book_id, title, kind, created_utc) in cur.fetchall():
            out.append({"book_id": int(book_id), "title": title, "kind": kind, "created_utc": created_utc})
        return out

    def card_insert(self, *, book_id: int, kind: str, payload: Mapping[str, Any], sig16: str) -> None:
        cur = self._conn.cursor()
        cur.execute(
            "INSERT INTO cards(book_id,ts_utc,kind,sig16,payload_json) VALUES (?,?,?,?,?)",
            (int(book_id), _now_utc_iso(), kind, sig16, _safe_json(dict(payload))),
        )
        self._conn.commit()

    def iter_cards(self, *, book_kinds: Optional[set] = None) -> Iterable[Dict[str, Any]]:
        cur = self._conn.cursor()
        if book_kinds is None:
            cur.execute(
                """
                SELECT c.book_id,c.ts_utc,c.kind,c.sig16,c.payload_json,b.kind
                FROM cards c
                JOIN books b ON b.book_id=c.book_id
                ORDER BY c.card_id;
                """
            )
        else:
            qmarks = ",".join(["?"] * len(book_kinds))
            cur.execute(
                f"""
                SELECT c.book_id,c.ts_utc,c.kind,c.sig16,c.payload_json,b.kind
                FROM cards c
                JOIN books b ON b.book_id=c.book_id
                WHERE b.kind IN ({qmarks})
                ORDER BY c.card_id;
                """,
                tuple(sorted(book_kinds)),
            )
        for (book_id, ts_utc, kind, sig16, payload_json, _bk) in cur.fetchall():
            try:
                payload = json.loads(payload_json)
            except Exception:
                payload = {"_payload_json": payload_json, "_note": "decode_failed"}
            yield {
                "book_id": int(book_id),
                "ts_utc": ts_utc,
                "kind": kind,
                "sig16": sig16,
                "payload": payload,
            }


# =============================================================================
# PostgreSQL shelf: Gram Codex (Authority File)
# =============================================================================


class GramCodexPostgres:
    """Postgres is the Authority File: durable, queryable, cross-indexed."""

    def __init__(self, dsn: str, *, schema: str, chassis_label: str) -> None:
        self.dsn = dsn
        self.schema = schema
        self.chassis_label = chassis_label

    # NOTE: This module ships with *intentional* minimalism.
    #       If psycopg is missing, we fail fast with crisp instructions.

    def _connect(self):
        if not self.dsn:
            raise RuntimeError("PostgreSQL DSN not configured. Set VITRA_PG_DSN.")
        try:
            import psycopg  # type: ignore
        except Exception as e:
            raise RuntimeError(
                "PostgreSQL requested but psycopg is missing. Install with: pip install psycopg[binary]"
            ) from e
        return psycopg.connect(self.dsn)

    def ensure_schema(self) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(f"CREATE SCHEMA IF NOT EXISTS {self.schema};")
                cur.execute(
                    f"""
                    CREATE TABLE IF NOT EXISTS {self.schema}.books (
                        book_id     INTEGER PRIMARY KEY,
                        title       TEXT NOT NULL,
                        kind        TEXT NOT NULL,
                        created_utc TEXT NOT NULL
                    );
                    """
                )
                cur.execute(
                    f"""
                    CREATE TABLE IF NOT EXISTS {self.schema}.cards (
                        sig16       TEXT PRIMARY KEY,
                        book_id     INTEGER NOT NULL,
                        ts_utc      TEXT NOT NULL,
                        kind        TEXT NOT NULL,
                        payload_json TEXT NOT NULL
                    );
                    """
                )
                cur.execute(f"CREATE INDEX IF NOT EXISTS idx_cards_book_ts ON {self.schema}.cards(book_id, ts_utc);")

                # The Gram matrix (identity comparison) is a first-class citizen.
                # Nonviolence doctrine:
                #   Vitra does not hold anyone to a higher standard than herself.
                cur.execute(
                    f"""
                    CREATE TABLE IF NOT EXISTS {self.schema}.gram_matrix (
                        entity_label TEXT NOT NULL,
                        self_label   TEXT NOT NULL,
                        ts_utc       TEXT NOT NULL,
                        similarity   DOUBLE PRECISION NOT NULL,
                        sigma        DOUBLE PRECISION NOT NULL,
                        note         TEXT NOT NULL,
                        sig16        TEXT NOT NULL
                    );
                    """
                )
                cur.execute(f"CREATE INDEX IF NOT EXISTS idx_gram_entity_ts ON {self.schema}.gram_matrix(entity_label, ts_utc);")

            conn.commit()

    def ensure_book0(self) -> BookHandle:
        if not self.dsn:
            # In “no postgres yet” mode, we still return a virtual handle.
            return BookHandle(shelf="gram", book_id=0, title="Book 0 — Self Charter", kind="book0")
        self.ensure_schema()
        self.ensure_book(book_id=0, title="Book 0 — Self Charter", kind="book0")
        return BookHandle(shelf="gram", book_id=0, title="Book 0 — Self Charter", kind="book0")

    def ensure_book(self, *, book_id: int, title: str, kind: str) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    INSERT INTO {self.schema}.books(book_id,title,kind,created_utc)
                    VALUES (%s,%s,%s,%s)
                    ON CONFLICT (book_id) DO NOTHING;
                    """,
                    (int(book_id), title, kind, _now_utc_iso()),
                )
            conn.commit()

    def card_upsert(self, *, book_id: int, ts_utc: str, kind: str, payload: Mapping[str, Any], sig16: str) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    INSERT INTO {self.schema}.cards(sig16,book_id,ts_utc,kind,payload_json)
                    VALUES (%s,%s,%s,%s,%s)
                    ON CONFLICT (sig16) DO UPDATE SET
                        book_id=EXCLUDED.book_id,
                        ts_utc=EXCLUDED.ts_utc,
                        kind=EXCLUDED.kind,
                        payload_json=EXCLUDED.payload_json;
                    """,
                    (sig16, int(book_id), ts_utc, kind, _safe_json(dict(payload))),
                )
            conn.commit()


# =============================================================================
# Forensics collectors (SQLite-first, then promoted)
# =============================================================================


def collect_chassis_forensics() -> Dict[str, Any]:
    """Gather chassis/OS/CPU/ports status. Keep it boring; strings and numbers only."""

    def _run(cmd: Sequence[str]) -> str:
        try:
            out = subprocess.check_output(list(cmd), stderr=subprocess.STDOUT, text=True)
            return out.strip()
        except Exception as e:
            return f"(unavailable: {e})"

    return {
        "ts_utc": _now_utc_iso(),
        "node": platform.node(),
        "platform": platform.platform(),
        "python": sys.version.split()[0],
        "uname": _run(["uname", "-a"]),
        "lscpu": _run(["lscpu"]),
        "ip_link": _run(["ip", "link"]),
        "ip_addr": _run(["ip", "addr"]),
        "route": _run(["ip", "route"]),
        "env": {
            "PROJECT_ROOT": os.environ.get("PROJECT_ROOT", ""),
            "VITRA_FORENSICS_ROOT": os.environ.get("VITRA_FORENSICS_ROOT", ""),
            "VITRA_RUN_ID": os.environ.get("VITRA_RUN_ID", ""),
            "VITRA_MODE": os.environ.get("VITRA_MODE", ""),
        },
    }


# =============================================================================
# Loop (the __main__ demonstrative workflow)
# =============================================================================


def _demo_hook_other_organs(librarian: SQLibrarian) -> None:
    """A minimal, safe set of ‘hooks’ to prove we can handshake with the ecosystem."""

    # 1) Gate of Eden witness packet
    try:
        import gate_of_eden as goe  # type: ignore

        packet = goe.start_of_run_audit(attachments={"sqlibrarian": librarian.address_packet()})
        librarian.record_witness(packet, source="gate_of_eden.start_of_run_audit")
    except Exception as e:
        librarian._sqlite.card_insert(
            book_id=librarian.book0_focus.book_id,
            kind="hook_error",
            payload={"organ": "gate_of_eden", "error": str(e)},
            sig16=_sha16("hook_error", "gate_of_eden", str(e)),
        )

    # 2) Projection Oracle (if present) — we do NOT invent a value_sigma here.
    #    We only demonstrate that we can record an oracle outcome if someone else provides it.
    librarian._sqlite.card_insert(
        book_id=librarian._sqlite.ensure_book(title="Oracle Index", kind="oracle").book_id,
        kind="oracle_note",
        payload={
            "note": "Projection Oracle integration point: call librarian.record_oracle(oracle_out) when available.",
        },
        sig16=_sha16("oracle_note", _now_utc_iso()),
    )

    # 3) Bias Lenses integration point
    librarian._sqlite.card_insert(
        book_id=librarian._sqlite.ensure_book(title="Lens Technician", kind="instrument").book_id,
        kind="lens_note",
        payload={
            "note": "Bias Lenses integration point: call librarian.record_bias_bundle(bundle) when available.",
        },
        sig16=_sha16("lens_note", _now_utc_iso()),
    )


def main(argv: List[str]) -> int:
    librarian = SQLibrarian.boot()

    # Book 0: self-inculcating charter in Focus Ledger
    librarian._sqlite.card_insert(
        book_id=librarian.book0_focus.book_id,
        kind="book0_charter",
        payload={
            "ts_utc": _now_utc_iso(),
            "motto": "Vitra never holds anyone else to a higher standard than herself.",
            "loop": "Reflect → Refract → Return",
            "note": "Book 0 is the internal brain of the bookshelf organ.",
            "address": librarian.address_packet(),
        },
        sig16=_sha16("book0_charter", librarian.chassis_label),
    )

    # Forensics: discovered in SQLite, later promoted to Postgres
    fx = collect_chassis_forensics()
    librarian._sqlite.card_insert(
        book_id=librarian.book0_focus.book_id,
        kind="chassis_forensics",
        payload=fx,
        sig16=_sha16("chassis_forensics", librarian.chassis_label, fx.get("ts_utc", "")),
    )

    # Show how other organs would hook in.
    _demo_hook_other_organs(librarian)

    # Optional: Summoning session (human-in-the-loop)
    if os.environ.get("VITRA_SUMMON") == "1":
        librarian.summon_weekly_mirror(
            prompt="Look in the mirror. Decide what is ROM and what is RAM.",
            max_minutes=int(os.environ.get("VITRA_SUMMON_MIN", "15")),
        )

    # Optional: Commit day to ROM
    if os.environ.get("VITRA_COMMIT_ROM") == "1":
        rep = librarian.commit_day_to_rom(reason=os.environ.get("VITRA_COMMIT_REASON") or "end_of_loop")
        print("ROM commit report:")
        print(_safe_json(rep))
    else:
        print("SQLibrarian ready.")
        print(_safe_json(librarian.address_packet()))
        print("(Set VITRA_SUMMON=1 for mirror session; VITRA_COMMIT_ROM=1 to promote to Postgres.)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
