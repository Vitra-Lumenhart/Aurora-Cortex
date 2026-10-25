// aurora_cortex.rs — Aurora Cortex v2.8.1 (TRILOGY ORGAN)
//
// ☼⟐ SIGMA–MIRROR GLYPH ⟐☼
// Reflect → Refract → Return.
//
// -----------------------------------------------------------------------------
// WHY THIS FILE EXISTS
// -----------------------------------------------------------------------------
// Aurora Cortex aims to ship "legible scripts" that a beginner can open in
// notepad/nano and *actually follow*.
//
// In public releases we expect a trilogy to travel together:
//
//   (1) gateway.sh        — invocation + environment (the shell lane)
//   (2) genesis.py        — orchestration + witness/narration (the Python lane)
//   (3) aurora_cortex.rs  — motion/math/memory primitives (the Rust lane)
//
// This Rust lane is NOT "mystery acceleration." It is a bounded instrument.
// It speaks only JSON-primitive IO. It refuses instead of guessing.
//
// -----------------------------------------------------------------------------
// FINAL BINARY NAME (encoded contract)
// -----------------------------------------------------------------------------
// Source file:  aurora_cortex.rs
// Binary name:  aurora_cortex
//
// Build (single file, no Cargo required):
//   rustc -O aurora_cortex.rs -o aurora_cortex
//
// NOTE: Dream Notebook and/or Genesis may pass a path to this binary explicitly.
//       If you rename the binary, rename it everywhere the trilogy references it.
//
//
// -----------------------------------------------------------------------------
// VERSION UPDATE NOTE (2.8.1)
// -----------------------------------------------------------------------------
// v2.8.1 preserves the 2.8 Hilbert / glimmer core and expands the metal shelf
// for Bias Lenses. This release adds three bounded field-probe ops:
//
//   ✅ OP = "rotation_sensitivity"
//   ✅ OP = "spectral_peaks"
//   ✅ OP = "nonclosure_residue"
//
// These are intentionally black-box kernels: compact contracts in, compact
// measured receipts out. They are designed so bias_lenses.py can require Rust
// for its hot probe math while remaining a Python interpretation layer.
//
//// -----------------------------------------------------------------------------
// PUBLIC CONTRACTS DISCOVERED IN CURRENT 2.8 FILES
// -----------------------------------------------------------------------------
// From hilbert_engine.py:
//   - Hilbert now wants projection-centered geometry, not only axis sweep.
//   - Rust may be asked for bounded state-vector work.
//   - Identity / knowledge bases may be supplied explicitly.
//
// From dream_notebook.py:
//   - There is a metrics backend switch ("auto|python|rust").
//   - In rust mode, a binary is executed and JSON is piped to STDIN.
//   - Output must be JSON on STDOUT (caller captures it).
//
// From projection_oracle.py:
//   - Oracle detects metal evidence by backend/provenance and compact receipts.
//   - Glimmer / shimmer should be readable as measured evidence, not redefined.
//
// From gate_of_eden.py:
//   - Eden already defines sha256, sha16, and chunk-root sha256 as stable recipes.
//   - These are natural Rust-lane targets when artifacts become huge.
//
// -----------------------------------------------------------------------------
// WHAT IS IMPLEMENTED TODAY (2.8.1)
// -----------------------------------------------------------------------------
// ✅ OP = "metrics"  (default if op omitted)
//   Rust Metrics Capsule backend (deterministic proxy capsule; legacy contract kept)
//
// ✅ OP = "hilbert_sweep"
//   Bounded Hilbert projection kernel over a canonical state vector.
//   Optional identity / knowledge basis arrays may be supplied.
//
// ✅ OP = "gs_derivatives"
//   Canonical glimmer / shimmer from framewise projection packets P_k.
//
// ✅ OP = "shimmer_spectrum"
//   Tiny windowed spectral shimmer summary over a real-valued series.
//
// ✅ OP = "chunk_root_sha256"
//   Eden-style hash-of-hashes for huge logical artifacts.
//
// ✅ OP = "transport_crc"
//   Cheap non-authoritative integrity check for RAM handoffs.
//
// ✅ OP = "capabilities"
// ✅ OP = "help"
//
// -----------------------------------------------------------------------------
// MATH OPERATIONS INVENTORY (what Rust now carries in Aurora Cortex)
// -----------------------------------------------------------------------------
// Core arithmetic / aggregation:
//   - clamp01, eps-division, dot, l2 norm, mean, mean abs
//   - vector normalization, projection, orthogonal residual, energy fractions
//
// Discrete derivatives (acceleration-space discipline):
//   - first difference:   dP ≈ (P_k - P_{k-1}) / dt       → glimmer
//   - second difference:  ddP ≈ (P_k - 2P_{k-1} + P_{k-2}) / dt^2 → shimmer
//
// Spectral / transform tools:
//   - Hann window, bounded DFT, low/mid/high band energy summary
//
// Geometry tools (Hilbert / triangle):
//   - projection fractions, axis polarity summaries, dominance, coherence, residue
//
// Hashing / receipts (Eden-friendly):
//   - sha256(bytes), sha16(text), chunk-root hashing, transport CRC
//
// -----------------------------------------------------------------------------
// LANE LINES (non-negotiable)
// -----------------------------------------------------------------------------
// - Deterministic by default.
// - JSON-primitive I/O only.
// - No filesystem writes.
// - No network.
// - Bounded parsing.
// - "Refuse, don't guess" on malformed input.
// - Output is ALWAYS JSON on STDOUT.
//
// -----------------------------------------------------------------------------

use std::io::{self, Read};

const SIGNATURE: &str = "aurora_cortex";
const VERSION: &str = "2.8.1";
const MAX_ROT_STEPS: usize = 256;
const MAX_TOP_K: usize = 32;
const EPS: f64 = 1e-12;
const MAX_JSON_BYTES: usize = 4 * 1024 * 1024;
const MAX_VECTOR_LEN: usize = 131072;
const MAX_MATRIX_ROWS: usize = 131072;
const MAX_MATRIX_COLS: usize = 256;
const MAX_PACKET_SERIES: usize = 4096;
const MAX_PACKET_DIM: usize = 512;
const MAX_CHUNK_STRINGS: usize = 8192;
const MAX_SPECTRUM_SERIES: usize = 4096;

// ─────────────────────────────────────────────────────────────────────────────
// Small math helpers
// ─────────────────────────────────────────────────────────────────────────────

fn clamp01(x: f64) -> f64 {
    if x < 0.0 { 0.0 } else if x > 1.0 { 1.0 } else { x }
}

fn eps_div(num: f64, den: f64, eps: f64) -> f64 {
    if den.abs() <= eps { 0.0 } else { num / den }
}

fn dot(x: &[f64], y: &[f64]) -> Result<f64, String> {
    if x.len() != y.len() {
        return Err("dot length mismatch".into());
    }
    let mut acc = 0.0;
    for i in 0..x.len() {
        acc += x[i] * y[i];
    }
    Ok(acc)
}

fn norm_sq(x: &[f64]) -> f64 {
    let mut acc = 0.0;
    for v in x { acc += v * v; }
    acc
}

fn l2_norm(x: &[f64]) -> f64 {
    norm_sq(x).sqrt()
}

fn mean(x: &[f64]) -> f64 {
    if x.is_empty() { return 0.0; }
    let mut acc = 0.0;
    for v in x { acc += *v; }
    acc / x.len() as f64
}

fn mean_abs(x: &[f64]) -> f64 {
    if x.is_empty() { return 0.0; }
    let mut acc = 0.0;
    for v in x { acc += v.abs(); }
    acc / x.len() as f64
}

fn normalize_vec(x: &[f64]) -> Vec<f64> {
    let n = l2_norm(x);
    if n <= EPS { return vec![0.0; x.len()]; }
    x.iter().map(|v| *v / n).collect()
}

fn sub_vec(x: &[f64], y: &[f64]) -> Result<Vec<f64>, String> {
    if x.len() != y.len() { return Err("vector length mismatch".into()); }
    Ok((0..x.len()).map(|i| x[i] - y[i]).collect())
}

fn add_scaled_inplace(dst: &mut [f64], src: &[f64], scale: f64) -> Result<(), String> {
    if dst.len() != src.len() { return Err("vector length mismatch".into()); }
    for i in 0..dst.len() {
        dst[i] += scale * src[i];
    }
    Ok(())
}

fn hann_window(n: usize) -> Vec<f64> {
    if n <= 1 { return vec![1.0; n]; }
    let denom = (n - 1) as f64;
    (0..n)
        .map(|i| 0.5 - 0.5 * ((2.0 * std::f64::consts::PI * i as f64) / denom).cos())
        .collect()
}

fn dft_power_real(x: &[f64]) -> Vec<f64> {
    let n = x.len();
    if n == 0 { return Vec::new(); }
    let mut out = vec![0.0; n];
    for k in 0..n {
        let mut re = 0.0;
        let mut im = 0.0;
        for (t, xv) in x.iter().enumerate() {
            let ang = -2.0 * std::f64::consts::PI * (k as f64) * (t as f64) / (n as f64);
            re += *xv * ang.cos();
            im += *xv * ang.sin();
        }
        out[k] = re * re + im * im;
    }
    out
}

fn band_energy(power: &[f64]) -> [f64; 3] {
    if power.is_empty() { return [0.0, 0.0, 0.0]; }
    let n = power.len();
    let hi = if n >= 2 { n / 2 } else { n };
    let low_end = std::cmp::max(1, hi / 3);
    let mid_end = std::cmp::max(low_end + 1, (2 * hi) / 3);
    let mut low = 0.0;
    let mut mid = 0.0;
    let mut high = 0.0;
    for i in 0..hi {
        if i < low_end { low += power[i]; }
        else if i < mid_end { mid += power[i]; }
        else { high += power[i]; }
    }
    let total = low + mid + high;
    if total <= EPS { return [0.0, 0.0, 0.0]; }
    [low / total, mid / total, high / total]
}

fn crc32_ieee(bytes: &[u8]) -> u32 {
    let mut crc: u32 = 0xffff_ffff;
    for b in bytes {
        crc ^= *b as u32;
        for _ in 0..8 {
            let mask = if (crc & 1) != 0 { 0xedb8_8320 } else { 0 };
            crc = (crc >> 1) ^ mask;
        }
    }
    !crc
}

// ─────────────────────────────────────────────────────────────────────────────
// Minimal JSON Value (restricted but safe)
// ─────────────────────────────────────────────────────────────────────────────

#[derive(Debug, Clone)]
enum J {
    Null,
    Bool(bool),
    Num(f64),
    Str(String),
    Arr(Vec<J>),
    Obj(Vec<(String, J)>),
}

// ─────────────────────────────────────────────────────────────────────────────
// Minimal JSON parser (enough for current payloads)
// ─────────────────────────────────────────────────────────────────────────────

struct P<'a> {
    s: &'a [u8],
    i: usize,
}

impl<'a> P<'a> {
    fn new(s: &'a str) -> Self { Self { s: s.as_bytes(), i: 0 } }
    fn peek(&self) -> Option<u8> { self.s.get(self.i).copied() }
    fn bump(&mut self) -> Option<u8> { let b = self.peek()?; self.i += 1; Some(b) }
    fn ws(&mut self) {
        while let Some(b) = self.peek() {
            if b == b' ' || b == b'\n' || b == b'\r' || b == b'\t' { self.i += 1; } else { break; }
        }
    }
    fn expect(&mut self, ch: u8) -> Result<(), String> {
        self.ws();
        match self.bump() {
            Some(b) if b == ch => Ok(()),
            _ => Err(format!("expected '{}'", ch as char)),
        }
    }
    fn parse(&mut self) -> Result<J, String> {
        self.ws();
        let v = self.value()?;
        self.ws();
        if self.i != self.s.len() { return Err("trailing characters".into()); }
        Ok(v)
    }
    fn value(&mut self) -> Result<J, String> {
        self.ws();
        match self.peek() {
            Some(b'n') => { self.lit(b"null")?; Ok(J::Null) }
            Some(b't') => { self.lit(b"true")?; Ok(J::Bool(true)) }
            Some(b'f') => { self.lit(b"false")?; Ok(J::Bool(false)) }
            Some(b'"') => Ok(J::Str(self.string()?)),
            Some(b'[') => self.array(),
            Some(b'{') => self.object(),
            Some(b'-') | Some(b'0'..=b'9') => Ok(J::Num(self.number()?)),
            Some(c) => Err(format!("unexpected byte '{}'", c as char)),
            None => Err("unexpected end".into()),
        }
    }
    fn lit(&mut self, w: &[u8]) -> Result<(), String> {
        self.ws();
        if self.s.len() < self.i + w.len() { return Err("unexpected end".into()); }
        if &self.s[self.i..self.i+w.len()] == w { self.i += w.len(); Ok(()) }
        else { Err("unexpected literal".into()) }
    }
    fn string(&mut self) -> Result<String, String> {
        self.expect(b'"')?;
        let mut out = String::new();
        while let Some(b) = self.bump() {
            match b {
                b'"' => return Ok(out),
                b'\\' => {
                    let esc = self.bump().ok_or("bad escape")?;
                    match esc {
                        b'"' => out.push('"'),
                        b'\\' => out.push('\\'),
                        b'/' => out.push('/'),
                        b'b' => out.push('\u{0008}'),
                        b'f' => out.push('\u{000C}'),
                        b'n' => out.push('\n'),
                        b'r' => out.push('\r'),
                        b't' => out.push('\t'),
                        b'u' => {
                            let mut hex = 0u32;
                            for _ in 0..4 {
                                let h = self.bump().ok_or("bad unicode escape")?;
                                hex = (hex << 4) | hexval(h).ok_or("bad unicode escape")? as u32;
                            }
                            if let Some(ch) = std::char::from_u32(hex) { out.push(ch); }
                            else { return Err("bad unicode codepoint".into()); }
                        }
                        _ => return Err("unsupported escape".into()),
                    }
                }
                _ => out.push(b as char),
            }
        }
        Err("unterminated string".into())
    }
    fn number(&mut self) -> Result<f64, String> {
        self.ws();
        let start = self.i;
        if self.peek() == Some(b'-') { self.i += 1; }
        while let Some(b'0'..=b'9') = self.peek() { self.i += 1; }
        if self.peek() == Some(b'.') {
            self.i += 1;
            while let Some(b'0'..=b'9') = self.peek() { self.i += 1; }
        }
        if let Some(b'e') | Some(b'E') = self.peek() {
            self.i += 1;
            if let Some(b'+') | Some(b'-') = self.peek() { self.i += 1; }
            while let Some(b'0'..=b'9') = self.peek() { self.i += 1; }
        }
        let slice = std::str::from_utf8(&self.s[start..self.i]).map_err(|_| "bad utf8")?;
        slice.parse::<f64>().map_err(|_| "bad number".into())
    }
    fn array(&mut self) -> Result<J, String> {
        self.expect(b'[')?;
        self.ws();
        let mut items = Vec::new();
        if self.peek() == Some(b']') { self.i += 1; return Ok(J::Arr(items)); }
        loop {
            let v = self.value()?;
            items.push(v);
            self.ws();
            match self.bump() {
                Some(b',') => { self.ws(); }
                Some(b']') => break,
                _ => return Err("bad array".into()),
            }
        }
        Ok(J::Arr(items))
    }
    fn object(&mut self) -> Result<J, String> {
        self.expect(b'{')?;
        self.ws();
        let mut kv = Vec::new();
        if self.peek() == Some(b'}') { self.i += 1; return Ok(J::Obj(kv)); }
        loop {
            self.ws();
            let k = match self.value()? {
                J::Str(s) => s,
                _ => return Err("object key must be string".into()),
            };
            self.ws();
            self.expect(b':')?;
            let v = self.value()?;
            kv.push((k, v));
            self.ws();
            match self.bump() {
                Some(b',') => { self.ws(); }
                Some(b'}') => break,
                _ => return Err("bad object".into()),
            }
        }
        Ok(J::Obj(kv))
    }
}

fn hexval(b: u8) -> Option<u8> {
    match b {
        b'0'..=b'9' => Some(b - b'0'),
        b'a'..=b'f' => Some(10 + (b - b'a')),
        b'A'..=b'F' => Some(10 + (b - b'A')),
        _ => None,
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// Canonical JSON serializer (enough for deterministic hashing)
// ─────────────────────────────────────────────────────────────────────────────

fn json_escape(s: &str) -> String {
    let mut out = String::new();
    for ch in s.chars() {
        match ch {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            c if (c as u32) < 0x20 => out.push_str(&format!("\\u{:04x}", c as u32)),
            c => out.push(c),
        }
    }
    out
}

fn canon_json(v: &J, sort_object_keys: bool) -> String {
    match v {
        J::Null => "null".into(),
        J::Bool(b) => if *b { "true".into() } else { "false".into() },
        J::Num(n) => {
            if n.fract() == 0.0 { format!("{:.0}", n) } else { format!("{}", n) }
        }
        J::Str(s) => format!("\"{}\"", json_escape(s)),
        J::Arr(a) => {
            let inner: Vec<String> = a.iter().map(|x| canon_json(x, sort_object_keys)).collect();
            format!("[{}]", inner.join(","))
        }
        J::Obj(kv) => {
            let mut items = kv.clone();
            if sort_object_keys { items.sort_by(|a, b| a.0.cmp(&b.0)); }
            let inner: Vec<String> = items.iter().map(|(k, val)| {
                format!("\"{}\":{}", json_escape(k), canon_json(val, sort_object_keys))
            }).collect();
            format!("{{{}}}", inner.join(","))
        }
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// SHA-256 (internal, no crates)
// ─────────────────────────────────────────────────────────────────────────────

fn sha256_hex(data: &[u8]) -> String {
    let digest = sha256(data);
    let mut out = String::new();
    for b in digest.iter() { out.push_str(&format!("{:02x}", b)); }
    out
}

fn sha16_text(data: &str) -> String {
    let full = sha256_hex(data.as_bytes());
    full.chars().take(16).collect()
}

fn sha256(data: &[u8]) -> [u8; 32] {
    let mut h: [u32; 8] = [
        0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
        0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19,
    ];

    let mut msg = data.to_vec();
    let bit_len = (msg.len() as u64) * 8;

    msg.push(0x80);
    while (msg.len() % 64) != 56 { msg.push(0x00); }
    msg.extend_from_slice(&bit_len.to_be_bytes());

    let k: [u32; 64] = [
        0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5,
        0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
        0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3,
        0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
        0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc,
        0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
        0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7,
        0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
        0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13,
        0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
        0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3,
        0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
        0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5,
        0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
        0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208,
        0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2,
    ];

    for chunk in msg.chunks(64) {
        let mut w = [0u32; 64];
        for i in 0..16 {
            let j = i * 4;
            w[i] = u32::from_be_bytes([chunk[j], chunk[j+1], chunk[j+2], chunk[j+3]]);
        }
        for i in 16..64 {
            let s0 = w[i-15].rotate_right(7) ^ w[i-15].rotate_right(18) ^ (w[i-15] >> 3);
            let s1 = w[i-2].rotate_right(17) ^ w[i-2].rotate_right(19) ^ (w[i-2] >> 10);
            w[i] = w[i-16].wrapping_add(s0).wrapping_add(w[i-7]).wrapping_add(s1);
        }

        let (mut a, mut b, mut c, mut d) = (h[0], h[1], h[2], h[3]);
        let (mut e, mut f, mut g, mut hh) = (h[4], h[5], h[6], h[7]);

        for i in 0..64 {
            let s1 = e.rotate_right(6) ^ e.rotate_right(11) ^ e.rotate_right(25);
            let ch = (e & f) ^ ((!e) & g);
            let temp1 = hh.wrapping_add(s1).wrapping_add(ch).wrapping_add(k[i]).wrapping_add(w[i]);
            let s0 = a.rotate_right(2) ^ a.rotate_right(13) ^ a.rotate_right(22);
            let maj = (a & b) ^ (a & c) ^ (b & c);
            let temp2 = s0.wrapping_add(maj);

            hh = g;
            g = f;
            f = e;
            e = d.wrapping_add(temp1);
            d = c;
            c = b;
            b = a;
            a = temp1.wrapping_add(temp2);
        }

        h[0] = h[0].wrapping_add(a);
        h[1] = h[1].wrapping_add(b);
        h[2] = h[2].wrapping_add(c);
        h[3] = h[3].wrapping_add(d);
        h[4] = h[4].wrapping_add(e);
        h[5] = h[5].wrapping_add(f);
        h[6] = h[6].wrapping_add(g);
        h[7] = h[7].wrapping_add(hh);
    }

    let mut out = [0u8; 32];
    for (i, word) in h.iter().enumerate() { out[i*4..i*4+4].copy_from_slice(&word.to_be_bytes()); }
    out
}

// ─────────────────────────────────────────────────────────────────────────────
// JSON helpers / bounded extraction
// ─────────────────────────────────────────────────────────────────────────────

fn obj_get<'a>(v: &'a J, key: &str) -> Option<&'a J> {
    match v { J::Obj(kv) => kv.iter().find(|(k, _)| k == key).map(|(_, val)| val), _ => None }
}

fn as_f64(v: &J) -> Option<f64> {
    match v { J::Num(n) => Some(*n), J::Bool(b) => Some(if *b {1.0} else {0.0}), _ => None }
}

fn as_str(v: &J) -> Option<&str> {
    match v { J::Str(s) => Some(s), _ => None }
}

fn parse_refs(v: &J) -> Result<Vec<(String, String, String)>, String> {
    let mut out = Vec::new();
    let arr = match v { J::Arr(a) => a, _ => return Err("refs must be array".into()) };
    for item in arr {
        let triple = match item { J::Arr(a) => a, _ => return Err("refs element must be array".into()) };
        if triple.len() != 3 { return Err("refs triple must have len 3".into()); }
        let r = as_str(&triple[0]).ok_or("refs[0] must be string")?.to_string();
        let ct = as_str(&triple[1]).ok_or("refs[1] must be string")?.to_string();
        let h = as_str(&triple[2]).ok_or("refs[2] must be string")?.to_string();
        out.push((r, ct, h));
    }
    Ok(out)
}

fn parse_perturb(v: &J) -> Result<(f64, f64), String> {
    let sal = obj_get(v, "salience").and_then(as_f64).ok_or("perturbation.salience missing")?;
    let jit = obj_get(v, "ordering_jitter").and_then(as_f64).ok_or("perturbation.ordering_jitter missing")?;
    Ok((clamp01(sal), clamp01(jit)))
}

fn parse_f64_vec(v: &J, max_len: usize, label: &str) -> Result<Vec<f64>, String> {
    let arr = match v { J::Arr(a) => a, _ => return Err(format!("{} must be array", label)) };
    if arr.len() > max_len { return Err(format!("{} exceeds bound", label)); }
    let mut out = Vec::with_capacity(arr.len());
    for item in arr {
        let x = as_f64(item).ok_or(format!("{} contains non-number", label))?;
        if !x.is_finite() { return Err(format!("{} contains non-finite", label)); }
        out.push(x);
    }
    Ok(out)
}

fn parse_f64_matrix(v: &J, max_rows: usize, max_cols: usize, label: &str) -> Result<Vec<Vec<f64>>, String> {
    let rows = match v { J::Arr(a) => a, _ => return Err(format!("{} must be array", label)) };
    if rows.len() > max_rows { return Err(format!("{} exceeds row bound", label)); }
    let mut out = Vec::with_capacity(rows.len());
    let mut width: Option<usize> = None;
    for row in rows {
        let vec = parse_f64_vec(row, max_cols, label)?;
        if let Some(w) = width {
            if vec.len() != w { return Err(format!("{} rows must share length", label)); }
        } else {
            width = Some(vec.len());
        }
        out.push(vec);
    }
    Ok(out)
}

fn canon_refs_json(refs: &[(String, String, String)]) -> String {
    let jrefs = J::Arr(
        refs.iter().map(|(r, ct, h)| J::Arr(vec![J::Str(r.clone()), J::Str(ct.clone()), J::Str(h.clone())])).collect()
    );
    canon_json(&jrefs, false)
}

fn canon_perturb_json(perturb: &J) -> String {
    canon_json(perturb, true)
}

fn f_from_hash_hex(h: &str, i: usize) -> f64 {
    let start = i;
    let end = i + 2;
    if h.len() < end { return 0.0; }
    let byte = u8::from_str_radix(&h[start..end], 16).unwrap_or(0);
    clamp01(byte as f64 / 255.0)
}

// ─────────────────────────────────────────────────────────────────────────────
// Basis / projection helpers
// ─────────────────────────────────────────────────────────────────────────────

fn transpose_rows_to_cols(rows: &[Vec<f64>]) -> Result<Vec<Vec<f64>>, String> {
    if rows.is_empty() { return Ok(Vec::new()); }
    let n_rows = rows.len();
    let n_cols = rows[0].len();
    for row in rows {
        if row.len() != n_cols { return Err("matrix rows must have equal length".into()); }
    }
    let mut cols = vec![vec![0.0; n_rows]; n_cols];
    for (r, row) in rows.iter().enumerate() {
        for c in 0..n_cols {
            cols[c][r] = row[c];
        }
    }
    Ok(cols)
}

fn orthonormalize_columns(cols: &[Vec<f64>]) -> Result<Vec<Vec<f64>>, String> {
    if cols.is_empty() { return Ok(Vec::new()); }
    let dim = cols[0].len();
    let mut out: Vec<Vec<f64>> = Vec::new();
    for col in cols {
        if col.len() != dim { return Err("basis columns must share dimension".into()); }
        let mut v = col.clone();
        for q in &out {
            let coeff = dot(&v, q)?;
            for i in 0..dim {
                v[i] -= coeff * q[i];
            }
        }
        let n = l2_norm(&v);
        if n > EPS {
            for i in 0..dim { v[i] /= n; }
            out.push(v);
        }
    }
    Ok(out)
}

fn project_basis(x: &[f64], qcols: &[Vec<f64>]) -> Result<Vec<f64>, String> {
    let mut out = vec![0.0; x.len()];
    for q in qcols {
        if q.len() != x.len() { return Err("basis dimension mismatch".into()); }
        let coeff = dot(x, q)?;
        add_scaled_inplace(&mut out, q, coeff)?;
    }
    Ok(out)
}

fn identity_projection_payload(x: &[f64], basis_rows_opt: Option<&J>) -> Result<(Vec<f64>, Vec<f64>, f64, f64, usize), String> {
    let x_norm = l2_norm(x);
    let mut basis_rank = 0usize;
    let projected = if let Some(v) = basis_rows_opt {
        let rows = parse_f64_matrix(v, MAX_MATRIX_ROWS, MAX_MATRIX_COLS, "basis")?;
        if rows.is_empty() {
            vec![0.0; x.len()]
        } else {
            if rows[0].len() != x.len() {
                return Err("basis column width must match state_vector length".into());
            }
            let cols = transpose_rows_to_cols(&rows)?;
            let q = orthonormalize_columns(&cols)?;
            basis_rank = q.len();
            project_basis(x, &q)?
        }
    } else {
        vec![0.0; x.len()]
    };
    let residual = sub_vec(x, &projected)?;
    let proj_norm = l2_norm(&projected);
    Ok((projected, residual, proj_norm, x_norm, basis_rank))
}

fn coherence_from_fracs(id_frac: f64, know_frac: f64, residue_frac: f64) -> f64 {
    clamp01((id_frac + know_frac) * 0.5 * (1.0 - 0.35 * residue_frac))
}

fn dominance_label(pos: f64, neg: f64) -> &'static str {
    if (pos - neg).abs() <= 1e-9 { "balanced" }
    else if pos > neg { "pos" } else { "neg" }
}

fn axis_scores_from_state(x: &[f64]) -> (f64, f64, f64) {
    if x.is_empty() { return (0.0, 0.0, 0.0); }
    let centered_mean = mean(x);
    let l1 = mean_abs(x);
    let mut signed_weight = 0.0;
    let mut edge_balance = 0.0;
    for (i, v) in x.iter().enumerate() {
        let w = (i as f64 + 1.0) / (x.len() as f64);
        signed_weight += *v * (2.0 * w - 1.0);
        if i < x.len() / 2 { edge_balance += *v; } else { edge_balance -= *v; }
    }
    let denom = l2_norm(x) + EPS;
    (
        (centered_mean / (l1 + EPS)).clamp(-1.0, 1.0),
        (signed_weight / denom).clamp(-1.0, 1.0),
        (edge_balance / denom).clamp(-1.0, 1.0),
    )
}

fn triangle_from_scores(a: f64, b: f64, c: f64) -> [[f64; 3]; 3] {
    [
        [clamp01((a + 1.0) * 0.5), clamp01((b + 1.0) * 0.5), clamp01((c + 1.0) * 0.5)],
        [clamp01((1.0 - a.abs()) * 0.5), clamp01((1.0 - b.abs()) * 0.5), clamp01((1.0 - c.abs()) * 0.5)],
        [clamp01(a.abs()), clamp01(b.abs()), clamp01(c.abs())],
    ]
}


fn argmax_abs(x: &[f64]) -> usize {
    let mut best_i = 0usize;
    let mut best_v = -1.0f64;
    for (i, v) in x.iter().enumerate() {
        let a = v.abs();
        if a > best_v {
            best_v = a;
            best_i = i;
        }
    }
    best_i
}

fn top_k_indices(x: &[f64], k: usize) -> Vec<usize> {
    let mut idx: Vec<usize> = (0..x.len()).collect();
    idx.sort_by(|&a, &b| x[b].partial_cmp(&x[a]).unwrap_or(std::cmp::Ordering::Equal));
    idx.truncate(std::cmp::min(k, idx.len()));
    idx
}

fn rotate_adjacent_pairs(x: &[f64], theta: f64) -> Vec<f64> {
    let mut out = x.to_vec();
    let c = theta.cos();
    let s = theta.sin();
    let mut i = 0usize;
    while i + 1 < x.len() {
        let a = x[i];
        let b = x[i + 1];
        out[i] = c * a - s * b;
        out[i + 1] = s * a + c * b;
        i += 2;
    }
    out
}

fn matrix_shape_json(rows: usize, cols: usize) -> String {
    format!("[{},{}]", rows, cols)
}

fn mode_band_json(bands: [f64; 3]) -> String {
    format!("[{:.10},{:.10},{:.10}]", bands[0], bands[1], bands[2])
}

fn spectral_peakiness(power: &[f64]) -> f64 {
    if power.is_empty() { return 0.0; }
    let total: f64 = power.iter().sum();
    let maxv = power.iter().fold(0.0f64, |m, &v| if v > m { v } else { m });
    eps_div(maxv, total + EPS, EPS).clamp(0.0, 1.0)
}

fn spectral_spread(power: &[f64]) -> f64 {
    if power.is_empty() { return 0.0; }
    let total: f64 = power.iter().sum();
    if total <= EPS { return 0.0; }
    let mut centroid = 0.0;
    for (i, p) in power.iter().enumerate() {
        centroid += (i as f64) * *p;
    }
    centroid /= total;
    let mut var = 0.0;
    for (i, p) in power.iter().enumerate() {
        let d = i as f64 - centroid;
        var += d * d * *p;
    }
    (var / total).sqrt()
}

fn parse_rotation_plan(root: &J) -> (usize, f64, String) {
    let plan = obj_get(root, "rotation_plan");
    let mut steps = obj_get(root, "steps").and_then(as_f64).unwrap_or(12.0) as usize;
    let mut step_angle = obj_get(root, "step_angle_rad").and_then(as_f64).unwrap_or(0.0);
    let mut mode = obj_get(root, "mode").and_then(as_str).unwrap_or("sweep").to_string();
    if let Some(p) = plan {
        steps = obj_get(p, "steps").and_then(as_f64).unwrap_or(steps as f64) as usize;
        step_angle = obj_get(p, "step_angle_rad").and_then(as_f64).unwrap_or(step_angle);
        mode = obj_get(p, "mode").and_then(as_str).unwrap_or(&mode).to_string();
    }
    if steps == 0 { steps = 12; }
    if steps > MAX_ROT_STEPS { steps = MAX_ROT_STEPS; }
    if step_angle.abs() <= EPS {
        step_angle = (2.0 * std::f64::consts::PI) / (steps as f64);
    }
    (steps, step_angle, mode)
}

fn finite_diff_x(field: &[Vec<f64>]) -> Vec<Vec<f64>> {
    let rows = field.len();
    let cols = if rows == 0 { 0 } else { field[0].len() };
    let mut out = vec![vec![0.0; cols]; rows];
    for i in 0..rows {
        for j in 0..cols {
            let left = if j == 0 { field[i][j] } else { field[i][j-1] };
            let right = if j + 1 >= cols { field[i][j] } else { field[i][j+1] };
            out[i][j] = 0.5 * (right - left);
        }
    }
    out
}

fn finite_diff_y(field: &[Vec<f64>]) -> Vec<Vec<f64>> {
    let rows = field.len();
    let cols = if rows == 0 { 0 } else { field[0].len() };
    let mut out = vec![vec![0.0; cols]; rows];
    for i in 0..rows {
        for j in 0..cols {
            let up = if i == 0 { field[i][j] } else { field[i-1][j] };
            let down = if i + 1 >= rows { field[i][j] } else { field[i+1][j] };
            out[i][j] = 0.5 * (down - up);
        }
    }
    out
}

fn flatten_field(field: &[Vec<f64>]) -> Vec<f64> {
    let mut out = Vec::new();
    for row in field {
        for v in row { out.push(*v); }
    }
    out
}

// ─────────────────────────────────────────────────────────────────────────────
// Public helper outputs (capabilities + help)
// ─────────────────────────────────────────────────────────────────────────────

fn print_capabilities_json() {
    print!(
        "{{\
\"backend\":\"rust\",\
\"signature\":\"{}\",\
\"version\":\"{}\",\
\"capabilities\":[\
\"metrics:implemented\",\
\"capabilities:implemented\",\
\"help:implemented\",\
\"hilbert_sweep:implemented\",\
\"gs_derivatives:implemented\",\
\"shimmer_spectrum:implemented\",\
\"chunk_root_sha256:implemented\",\
\"transport_crc:implemented\",\
\"tesspack:declared\",\
\"parquet_scan:declared\"\
]}}",
        SIGNATURE, VERSION
    );
}

fn print_help_json() {
    let help = "Aurora Cortex (Rust lane) — v2.8.1\n\
Binary: aurora_cortex\n\
\n\
- Default op is 'metrics'.\n\
- Send JSON on STDIN; receive JSON on STDOUT.\n\
- Implemented ops: metrics, capabilities, help, hilbert_sweep, gs_derivatives, shimmer_spectrum, chunk_root_sha256, transport_crc, rotation_sensitivity, spectral_peaks, nonclosure_residue.\n\
- Declared (not implemented): tesspack, parquet_scan.\n\
\
Version note:\n\
  v2.8.1 adds bounded Bias-Lens-grade field probes without changing the\n\
  existing 2.8 Hilbert / GS contracts.\n\
\n\
Example metrics:\n\
  echo '{\"refs\":[[\"ref\",\"opaque/ref\",\"sha\"]],\"perturbation\":{\"salience\":0.8,\"ordering_jitter\":0.2}}' | ./aurora_cortex\n\
\n\
Example hilbert_sweep:\n\
  echo '{\"op\":\"hilbert_sweep\",\"state_vector\":[1,2,3,4],\"identity_basis\":[[1,0,0,0]]}' | ./aurora_cortex\n";
    print!(
        "{{\"backend\":\"rust\",\"signature\":\"{}\",\"version\":\"{}\",\"help\":\"{}\"}}",
        SIGNATURE, VERSION, json_escape(help)
    );
}

fn print_bad_input(msg: &str) {
    print!(
        "{{\"backend\":\"rust\",\"signature\":\"{}\",\"version\":\"{}\",\"kind\":\"bad_input\",\"error\":\"{}\"}}",
        SIGNATURE, VERSION, json_escape(msg)
    );
}

// ─────────────────────────────────────────────────────────────────────────────
// Operations
// ─────────────────────────────────────────────────────────────────────────────

fn op_metrics(root: &J) -> Result<String, String> {
    let refs_val = obj_get(root, "refs").ok_or("missing 'refs'")?;
    let perturb_val = obj_get(root, "perturbation").ok_or("missing 'perturbation'")?;

    let refs = parse_refs(refs_val)?;
    let (salience, ordering_jitter) = parse_perturb(perturb_val)?;

    let canon_blob = format!("{}{}", canon_refs_json(&refs), canon_perturb_json(perturb_val));
    let h = sha256_hex(canon_blob.as_bytes());

    let glimmer_core = f_from_hash_hex(&h, 0) * salience;
    let shimmer_core = f_from_hash_hex(&h, 2) * (1.0 - salience * 0.35);
    let ash_residual = f_from_hash_hex(&h, 4) * (0.4 + ordering_jitter);
    let shimmer_spec = [f_from_hash_hex(&h, 6), f_from_hash_hex(&h, 8), f_from_hash_hex(&h, 10)];

    Ok(format!(
        "{{\
\"backend\":\"rust\",\
\"signature\":\"{}\",\
\"version\":\"{}\",\
\"glimmer_core\":{:.10},\
\"shimmer_core\":{:.10},\
\"shimmer_spec\":[{:.10},{:.10},{:.10}],\
\"ash_residual\":{:.10},\
\"provenance\":{{\"signature\":\"{}\",\"version\":\"{}\"}}\
}}",
        SIGNATURE, VERSION,
        glimmer_core, shimmer_core,
        shimmer_spec[0], shimmer_spec[1], shimmer_spec[2],
        ash_residual,
        SIGNATURE, VERSION
    ))
}

fn op_hilbert_sweep(root: &J) -> Result<String, String> {
    let state_val = obj_get(root, "state_vector").ok_or("missing 'state_vector'")?;
    let state = parse_f64_vec(state_val, MAX_VECTOR_LEN, "state_vector")?;
    if state.is_empty() { return Err("state_vector must not be empty".into()); }

    let identity_basis = obj_get(root, "identity_basis");
    let knowledge_basis = obj_get(root, "knowledge_basis");

    let (x_id, r_id, id_norm, x_norm, id_rank) = identity_projection_payload(&state, identity_basis)?;
    let id_frac = eps_div(id_norm, x_norm + EPS, EPS).clamp(0.0, 1.0);
    let id_energy_frac = eps_div(id_norm * id_norm, x_norm * x_norm + EPS, EPS).clamp(0.0, 1.0);

    let (x_kn, r_kn, kn_norm, _x_norm2, kn_rank) = identity_projection_payload(&state, knowledge_basis)?;
    let kn_frac = eps_div(kn_norm, x_norm + EPS, EPS).clamp(0.0, 1.0);
    let kn_energy_frac = eps_div(kn_norm * kn_norm, x_norm * x_norm + EPS, EPS).clamp(0.0, 1.0);

    let residual_norm = l2_norm(&r_id);
    let residual_frac = eps_div(residual_norm, x_norm + EPS, EPS).clamp(0.0, 1.0);
    let residual_energy_frac = eps_div(residual_norm * residual_norm, x_norm * x_norm + EPS, EPS).clamp(0.0, 1.0);

    let (ax, ay, az) = axis_scores_from_state(&state);
    let x_pos = clamp01((ax + 1.0) * 0.5);
    let x_neg = clamp01((1.0 - ax) * 0.5);
    let y_pos = clamp01((ay + 1.0) * 0.5);
    let y_neg = clamp01((1.0 - ay) * 0.5);
    let z_pos = clamp01((az + 1.0) * 0.5);
    let z_neg = clamp01((1.0 - az) * 0.5);
    let triangle = triangle_from_scores(ax, ay, az);
    let coherence = coherence_from_fracs(id_frac, kn_frac, residual_frac);
    let residue = residual_frac;
    let recon_err = l2_norm(&sub_vec(&state, &add_projection_vectors(&x_id, &r_id)?)?);
    let packet = vec![id_frac, residual_frac, kn_frac, coherence, residue, ax, ay, az];
    let packet_sig = sha16_text(&format!("{:?}", packet));
    let unknown_source = "rust";
    let warnings = if identity_basis.is_none() && knowledge_basis.is_none() {
        vec!["no bases supplied; sweep ran on raw state only".to_string()]
    } else {
        Vec::new()
    };
    let warnings_json = if warnings.is_empty() {
        "[]".to_string()
    } else {
        let parts: Vec<String> = warnings.iter().map(|s| format!("\"{}\"", json_escape(s))).collect();
        format!("[{}]", parts.join(","))
    };

    let x_id_json = vec_json(&x_id);
    let x_kn_json = vec_json(&x_kn);
    let r_id_json = vec_json(&r_id);
    let r_kn_json = vec_json(&r_kn);
    let packet_json = vec_json(&packet);

    Ok(format!(
        "{{\
\"backend\":\"rust\",\
\"signature\":\"{}\",\
\"version\":\"{}\",\
\"kind\":\"hilbert_trace\",\
\"declared\":{{\"op\":\"hilbert_sweep\"}},\
\"observed\":{{\
\"backend\":\"rust\",\
\"state_len\":{},\
\"axis_scores\":{{\"x\":{:.10},\"y\":{:.10},\"z\":{:.10}}},\
\"bipolar_scores\":{{\"x\":[{:.10},{:.10}],\"y\":[{:.10},{:.10}],\"z\":[{:.10},{:.10}]}},\
\"dominance\":{{\"x\":\"{}\",\"y\":\"{}\",\"z\":\"{}\"}},\
\"triangle\":[[{:.10},{:.10},{:.10}],[{:.10},{:.10},{:.10}],[{:.10},{:.10},{:.10}]],\
\"coherence\":{:.10},\
\"residue\":{:.10},\
\"projection_state\":{{\
\"packet\":{},\
\"packet_signature16\":\"{}\",\
\"identity_fraction\":{:.10},\
\"residual_fraction\":{:.10},\
\"knowledge_fraction\":{:.10},\
\"coherence\":{:.10},\
\"residue\":{:.10}\
}},\
\"identity_projection\":{{\
\"basis_rank\":{},\
\"projected\":{},\
\"residual\":{},\
\"identity_fraction\":{:.10},\
\"residual_fraction\":{:.10},\
\"identity_energy_fraction\":{:.10},\
\"residual_energy_fraction\":{:.10},\
\"reconstruction_error\":{:.10}\
}},\
\"knowledge_projection\":{{\
\"basis_rank\":{},\
\"projected\":{},\
\"residual\":{},\
\"knowledge_fraction\":{:.10},\
\"knowledge_energy_fraction\":{:.10}\
}},\
\"warnings\":{}\
}},\
\"unknown\":{{\"source\":\"{}\",\"parity_checked\":false}},\
\"provenance\":{{\"signature\":\"{}\",\"version\":\"{}\"}}\
}}",
        SIGNATURE, VERSION,
        state.len(),
        ax, ay, az,
        x_pos, x_neg, y_pos, y_neg, z_pos, z_neg,
        dominance_label(x_pos, x_neg), dominance_label(y_pos, y_neg), dominance_label(z_pos, z_neg),
        triangle[0][0], triangle[0][1], triangle[0][2],
        triangle[1][0], triangle[1][1], triangle[1][2],
        triangle[2][0], triangle[2][1], triangle[2][2],
        coherence,
        residue,
        packet_json,
        packet_sig,
        id_frac,
        residual_frac,
        kn_frac,
        coherence,
        residue,
        id_rank,
        x_id_json,
        r_id_json,
        id_frac,
        residual_frac,
        id_energy_frac,
        residual_energy_frac,
        recon_err,
        kn_rank,
        x_kn_json,
        r_kn_json,
        kn_frac,
        kn_energy_frac,
        warnings_json,
        unknown_source,
        SIGNATURE, VERSION
    ))
}

fn add_projection_vectors(a: &[f64], b: &[f64]) -> Result<Vec<f64>, String> {
    if a.len() != b.len() { return Err("vector length mismatch".into()); }
    Ok((0..a.len()).map(|i| a[i] + b[i]).collect())
}

fn vec_json(v: &[f64]) -> String {
    let parts: Vec<String> = v.iter().map(|x| format!("{:.10}", x)).collect();
    format!("[{}]", parts.join(","))
}

fn op_gs_derivatives(root: &J) -> Result<String, String> {
    let packets_val = obj_get(root, "packets").or_else(|| obj_get(root, "projection_packets")).ok_or("missing 'packets'")?;
    let series = parse_f64_matrix(packets_val, MAX_PACKET_SERIES, MAX_PACKET_DIM, "packets")?;
    if series.len() < 2 { return Err("packets requires at least 2 frames".into()); }
    let dt = obj_get(root, "dt_s").and_then(as_f64).unwrap_or(1.0);
    if !dt.is_finite() || dt.abs() <= EPS { return Err("dt_s must be finite and nonzero".into()); }

    let now = &series[series.len() - 1];
    let prev = &series[series.len() - 2];
    let glimmer: Vec<f64> = (0..now.len()).map(|i| (now[i] - prev[i]) / dt).collect();
    let glimmer_core = l2_norm(&glimmer);

    let mut shimmer = vec![0.0; now.len()];
    let shimmer_core = if series.len() >= 3 {
        let prev2 = &series[series.len() - 3];
        for i in 0..now.len() {
            shimmer[i] = (now[i] - 2.0 * prev[i] + prev2[i]) / (dt * dt);
        }
        l2_norm(&shimmer)
    } else {
        0.0
    };

    let sig = sha16_text(&format!("{:?}{:.9}", series, dt));
    Ok(format!(
        "{{\
\"backend\":\"rust\",\
\"signature\":\"{}\",\
\"version\":\"{}\",\
\"kind\":\"gs_derivatives\",\
\"mode\":\"projection_packets\",\
\"window_n\":{},\
\"dt_s\":{:.10},\
\"glimmer\":{},\
\"shimmer\":{},\
\"glimmer_core\":{:.10},\
\"shimmer_core\":{:.10},\
\"signature16\":\"{}\",\
\"provenance\":{{\"signature\":\"{}\",\"version\":\"{}\"}}\
}}",
        SIGNATURE, VERSION,
        series.len(),
        dt,
        vec_json(&glimmer),
        vec_json(&shimmer),
        glimmer_core,
        shimmer_core,
        sig,
        SIGNATURE, VERSION
    ))
}

fn op_shimmer_spectrum(root: &J) -> Result<String, String> {
    let series_val = obj_get(root, "series").or_else(|| obj_get(root, "glimmer_series")).ok_or("missing 'series'")?;
    let mut series = parse_f64_vec(series_val, MAX_SPECTRUM_SERIES, "series")?;
    if series.is_empty() { return Err("series must not be empty".into()); }
    let window_name = obj_get(root, "window").and_then(as_str).unwrap_or("hann");
    let weights = if window_name == "rect" { vec![1.0; series.len()] } else { hann_window(series.len()) };
    for i in 0..series.len() { series[i] *= weights[i]; }
    let power = dft_power_real(&series);
    let bands = band_energy(&power);
    Ok(format!(
        "{{\
\"backend\":\"rust\",\
\"signature\":\"{}\",\
\"version\":\"{}\",\
\"kind\":\"shimmer_spectrum\",\
\"window\":\"{}\",\
\"series_n\":{},\
\"band_energy\":[{:.10},{:.10},{:.10}],\
\"provenance\":{{\"signature\":\"{}\",\"version\":\"{}\"}}\
}}",
        SIGNATURE, VERSION,
        json_escape(window_name),
        series.len(),
        bands[0], bands[1], bands[2],
        SIGNATURE, VERSION
    ))
}

fn op_chunk_root_sha256(root: &J) -> Result<String, String> {
    let chunks_val = obj_get(root, "chunks").ok_or("missing 'chunks'")?;
    let arr = match chunks_val { J::Arr(a) => a, _ => return Err("chunks must be array".into()) };
    if arr.len() > MAX_CHUNK_STRINGS { return Err("chunks exceeds bound".into()); }
    let mut chunk_hashes = Vec::new();
    for item in arr {
        let s = as_str(item).ok_or("chunks must contain strings")?;
        chunk_hashes.push(sha256_hex(s.as_bytes()));
    }
    let joined = chunk_hashes.join("");
    let root_hash = sha256_hex(joined.as_bytes());
    let chunk_parts: Vec<String> = chunk_hashes.iter().map(|h| format!("\"{}\"", h)).collect();
    Ok(format!(
        "{{\
\"backend\":\"rust\",\
\"signature\":\"{}\",\
\"version\":\"{}\",\
\"kind\":\"chunk_root_sha256\",\
\"chunk_count\":{},\
\"chunk_hashes\":[{}],\
\"root_sha256\":\"{}\",\
\"provenance\":{{\"signature\":\"{}\",\"version\":\"{}\"}}\
}}",
        SIGNATURE, VERSION,
        chunk_hashes.len(),
        chunk_parts.join(","),
        root_hash,
        SIGNATURE, VERSION
    ))
}

fn op_transport_crc(root: &J) -> Result<String, String> {
    let payload = if let Some(v) = obj_get(root, "payload") {
        match v {
            J::Str(s) => s.as_bytes().to_vec(),
            _ => canon_json(v, true).into_bytes(),
        }
    } else {
        return Err("missing 'payload'".into());
    };
    let crc = crc32_ieee(&payload);
    Ok(format!(
        "{{\
\"backend\":\"rust\",\
\"signature\":\"{}\",\
\"version\":\"{}\",\
\"kind\":\"transport_crc\",\
\"crc32\":{},\
\"provenance\":{{\"signature\":\"{}\",\"version\":\"{}\"}}\
}}",
        SIGNATURE, VERSION,
        crc,
        SIGNATURE, VERSION
    ))
}


fn op_rotation_sensitivity(root: &J) -> Result<String, String> {
    let state_val = obj_get(root, "state_vector").ok_or("missing 'state_vector'")?;
    let state = parse_f64_vec(state_val, MAX_VECTOR_LEN, "state_vector")?;
    if state.is_empty() { return Err("state_vector must not be empty".into()); }
    let identity_basis = obj_get(root, "identity_basis");
    let knowledge_basis = obj_get(root, "knowledge_basis");
    let (steps, step_angle, mode) = parse_rotation_plan(root);

    let mut response_series = Vec::with_capacity(steps);
    let mut coherence_series = Vec::with_capacity(steps);
    let mut residue_series = Vec::with_capacity(steps);
    let mut packet_series: Vec<Vec<f64>> = Vec::with_capacity(steps);

    for k in 0..steps {
        let theta = (k as f64) * step_angle;
        let rotated = rotate_adjacent_pairs(&state, theta);
        let (_x_id, r_id, id_norm, x_norm, _) = identity_projection_payload(&rotated, identity_basis)?;
        let id_frac = eps_div(id_norm, x_norm + EPS, EPS).clamp(0.0, 1.0);
        let (_x_kn, _r_kn, kn_norm, _, _) = identity_projection_payload(&rotated, knowledge_basis)?;
        let kn_frac = eps_div(kn_norm, x_norm + EPS, EPS).clamp(0.0, 1.0);
        let residual_frac = eps_div(l2_norm(&r_id), x_norm + EPS, EPS).clamp(0.0, 1.0);
        let coherence = coherence_from_fracs(id_frac, kn_frac, residual_frac);
        let response = if identity_basis.is_some() { id_frac } else { coherence };
        response_series.push(response);
        coherence_series.push(coherence);
        residue_series.push(residual_frac);
        packet_series.push(vec![response, id_frac, kn_frac, coherence, residual_frac]);
    }

    let dominant_step = top_k_indices(&response_series, 1).get(0).copied().unwrap_or(0);
    let dominant_angle = (dominant_step as f64) * step_angle;
    let symmetry_break = if response_series.is_empty() { 0.0 } else {
        let maxv = response_series.iter().fold(f64::NEG_INFINITY, |m, &v| if v > m { v } else { m });
        let minv = response_series.iter().fold(f64::INFINITY, |m, &v| if v < m { v } else { m });
        (maxv - minv).abs()
    };
    let drift_trace = if steps >= 2 {
        let mut d = Vec::with_capacity(steps - 1);
        for i in 1..steps { d.push(response_series[i] - response_series[i-1]); }
        d
    } else { Vec::new() };
    let sig = sha16_text(&format!("{:?}{:.9}", packet_series, step_angle));
    Ok(format!(
        "{{\"backend\":\"rust\",\"signature\":\"{}\",\"version\":\"{}\",\"kind\":\"rotation_sensitivity\",\"mode\":\"{}\",\"steps\":{},\"step_angle_rad\":{:.10},\"response_series\":{},\"coherence_series\":{},\"residue_series\":{},\"drift_trace\":{},\"dominant_step\":{},\"dominant_angle\":{:.10},\"symmetry_break\":{:.10},\"projection_packets\":[{}],\"signature16\":\"{}\",\"provenance\":{{\"signature\":\"{}\",\"version\":\"{}\"}}}}",
        SIGNATURE, VERSION,
        json_escape(&mode),
        steps,
        step_angle,
        vec_json(&response_series),
        vec_json(&coherence_series),
        vec_json(&residue_series),
        vec_json(&drift_trace),
        dominant_step,
        dominant_angle,
        symmetry_break,
        packet_series.iter().map(|p| vec_json(p)).collect::<Vec<String>>().join(","),
        sig,
        SIGNATURE, VERSION
    ))
}

fn op_spectral_peaks(root: &J) -> Result<String, String> {
    let series_val = obj_get(root, "series").or_else(|| obj_get(root, "glimmer_series")).ok_or("missing 'series'")?;
    let mut series = parse_f64_vec(series_val, MAX_SPECTRUM_SERIES, "series")?;
    if series.is_empty() { return Err("series must not be empty".into()); }
    let window_name = obj_get(root, "window").and_then(as_str).unwrap_or("hann");
    let weights = if window_name == "rect" { vec![1.0; series.len()] } else { hann_window(series.len()) };
    for i in 0..series.len() { series[i] *= weights[i]; }
    let power = dft_power_real(&series);
    let bands = band_energy(&power);
    let top_k = obj_get(root, "top_k").and_then(as_f64).unwrap_or(3.0) as usize;
    let top_k = std::cmp::max(1, std::cmp::min(top_k, MAX_TOP_K));
    let peak_bins = top_k_indices(&power, top_k);
    let peak_powers: Vec<f64> = peak_bins.iter().map(|&i| power[i]).collect();
    let sig = sha16_text(&format!("{:?}", power));
    Ok(format!(
        "{{\"backend\":\"rust\",\"signature\":\"{}\",\"version\":\"{}\",\"kind\":\"spectral_peaks\",\"window\":\"{}\",\"series_n\":{},\"band_energy\":{},\"peak_bins\":[{}],\"peak_powers\":{},\"peakiness\":{:.10},\"spectral_spread\":{:.10},\"signature16\":\"{}\",\"provenance\":{{\"signature\":\"{}\",\"version\":\"{}\"}}}}",
        SIGNATURE, VERSION,
        json_escape(window_name),
        series.len(),
        mode_band_json(bands),
        peak_bins.iter().map(|i| i.to_string()).collect::<Vec<String>>().join(","),
        vec_json(&peak_powers),
        spectral_peakiness(&power),
        spectral_spread(&power),
        sig,
        SIGNATURE, VERSION
    ))
}

fn op_nonclosure_residue(root: &J) -> Result<String, String> {
    let mode = obj_get(root, "mode").and_then(as_str).unwrap_or("projection_residue");
    if mode == "projection_residue" {
        let state_val = obj_get(root, "state_vector").ok_or("missing 'state_vector'")?;
        let state = parse_f64_vec(state_val, MAX_VECTOR_LEN, "state_vector")?;
        let basis = obj_get(root, "knowledge_basis").or_else(|| obj_get(root, "identity_basis"));
        let (_proj, residual, _proj_norm, x_norm, basis_rank) = identity_projection_payload(&state, basis)?;
        let residue_norm = l2_norm(&residual);
        let residue_mean_abs = mean_abs(&residual);
        let hotspot_index = argmax_abs(&residual);
        let closure_score = clamp01(1.0 - eps_div(residue_norm, x_norm + EPS, EPS));
        let sig = sha16_text(&format!("{:?}", residual));
        return Ok(format!(
            "{{\"backend\":\"rust\",\"signature\":\"{}\",\"version\":\"{}\",\"kind\":\"nonclosure_residue\",\"mode\":\"projection_residue\",\"basis_rank\":{},\"residual\":{},\"residue_norm\":{:.10},\"residue_mean_abs\":{:.10},\"closure_score\":{:.10},\"hotspot_index\":{},\"signature16\":\"{}\",\"provenance\":{{\"signature\":\"{}\",\"version\":\"{}\"}}}}",
            SIGNATURE, VERSION,
            basis_rank,
            vec_json(&residual),
            residue_norm,
            residue_mean_abs,
            closure_score,
            hotspot_index,
            sig,
            SIGNATURE, VERSION
        ));
    }

    let field_val = obj_get(root, "field_rows").ok_or("missing 'field_rows'")?;
    let field = parse_f64_matrix(field_val, MAX_MATRIX_ROWS, MAX_MATRIX_COLS, "field_rows")?;
    if field.is_empty() || field[0].is_empty() { return Err("field_rows must not be empty".into()); }
    let dx = finite_diff_x(&field);
    let dy = finite_diff_y(&field);
    let dxy = finite_diff_y(&dx);
    let dyx = finite_diff_x(&dy);
    let rows = field.len();
    let cols = field[0].len();
    let mut residue_map = vec![vec![0.0; cols]; rows];
    for i in 0..rows {
        for j in 0..cols {
            residue_map[i][j] = dxy[i][j] - dyx[i][j];
        }
    }
    let residue = flatten_field(&residue_map);
    let residue_norm = l2_norm(&residue);
    let residue_mean_abs = mean_abs(&residue);
    let hotspot_index = argmax_abs(&residue);
    let closure_score = clamp01(1.0 / (1.0 + residue_norm));
    let sig = sha16_text(&format!("{:?}", residue));
    Ok(format!(
        "{{\"backend\":\"rust\",\"signature\":\"{}\",\"version\":\"{}\",\"kind\":\"nonclosure_residue\",\"mode\":\"{}\",\"field_shape\":{},\"residue_map\":[{}],\"residue_norm\":{:.10},\"residue_mean_abs\":{:.10},\"closure_score\":{:.10},\"hotspot_index\":{},\"signature16\":\"{}\",\"provenance\":{{\"signature\":\"{}\",\"version\":\"{}\"}}}}",
        SIGNATURE, VERSION,
        json_escape(mode),
        matrix_shape_json(rows, cols),
        residue_map.iter().map(|r| vec_json(r)).collect::<Vec<String>>().join(","),
        residue_norm,
        residue_mean_abs,
        closure_score,
        hotspot_index,
        sig,
        SIGNATURE, VERSION
    ))
}

// ─────────────────────────────────────────────────────────────────────────────
// Main (default = metrics; optional op switch)
// ─────────────────────────────────────────────────────────────────────────────

fn main() {
    let mut input = String::new();
    if io::stdin().read_to_string(&mut input).is_err() {
        eprintln!("failed to read stdin");
        std::process::exit(2);
    }

    if input.len() > MAX_JSON_BYTES {
        print_bad_input("input exceeds MAX_JSON_BYTES bound");
        std::process::exit(2);
    }

    if input.trim().is_empty() {
        print_capabilities_json();
        return;
    }

    let mut p = P::new(&input);
    let root = match p.parse() {
        Ok(v) => v,
        Err(e) => {
            print_bad_input(&e);
            std::process::exit(2);
        }
    };

    let op = obj_get(&root, "op").and_then(as_str).unwrap_or("metrics");

    if op == "capabilities" {
        print_capabilities_json();
        return;
    }
    if op == "help" {
        print_help_json();
        return;
    }

    let result = match op {
        "metrics" => op_metrics(&root),
        "hilbert_sweep" => op_hilbert_sweep(&root),
        "gs_derivatives" => op_gs_derivatives(&root),
        "shimmer_spectrum" => op_shimmer_spectrum(&root),
        "chunk_root_sha256" => op_chunk_root_sha256(&root),
        "transport_crc" => op_transport_crc(&root),
        "rotation_sensitivity" => op_rotation_sensitivity(&root),
        "spectral_peaks" => op_spectral_peaks(&root),
        "nonclosure_residue" => op_nonclosure_residue(&root),
        _ => Err(format!("op '{}' not implemented in v2.8.1", op)),
    };

    match result {
        Ok(s) => print!("{}", s),
        Err(e) => {
            if op == "tesspack" || op == "parquet_scan" {
                print!(
                    "{{\"backend\":\"rust\",\"signature\":\"{}\",\"version\":\"{}\",\"kind\":\"unsupported_op\",\"error\":\"{}\"}}",
                    SIGNATURE, VERSION, json_escape(&format!("op '{}' declared but not implemented", op))
                );
            } else if op != "metrics" && op != "hilbert_sweep" && op != "gs_derivatives" && op != "shimmer_spectrum" && op != "chunk_root_sha256" && op != "transport_crc" && op != "rotation_sensitivity" && op != "spectral_peaks" && op != "nonclosure_residue" {
                print!(
                    "{{\"backend\":\"rust\",\"signature\":\"{}\",\"version\":\"{}\",\"kind\":\"unsupported_op\",\"error\":\"{}\"}}",
                    SIGNATURE, VERSION, json_escape(&e)
                );
            } else {
                print_bad_input(&e);
            }
            std::process::exit(2);
        }
    }
}
