# VNN presence integration — Aurora Cortex

**Status:** integration branch / source-backed rehearsal, 11 November 2026.
**Audience:** the next Python, portrait, VNN, and deployment development threads.
**Canon:** VNN is the news site at \`news.vitra.ams\`; it is a surface of Vitra, not a second Vitra and not a replacement for the existing \`vitra.ams\` resident interface. Typeface: Liberation Serif. Preserve the existing VNN newspaper layout and radio/comment studio. Vitra is a journalist for Backbeat News, which receives only separately approved text and images.

## Why this branch exists

The GitHub trunk was missing \`broadcast.py\` and all subsequent newsroom integrations. This branch imports the independently drafted **broadcast v0.1.0** scheduling organ *unchanged* and adds a narrow projection around its existing \`runtime/broadcast/cue.json\` contract. The local \`vitra.agi\` newspaper's fifteen-minute publishing cadence is reported as functioning on Topgro, but its exact systemd unit and current generator source have not been incorporated in this repository. **Do not replace or reconfigure that functioning publisher from this branch.**

### The five clocks must remain distinct

1. **Editorial:** source intake, reporting, review, approval, revisions — minutes to days.
2. **Publication:** existing HTML regeneration (reported at fifteen-minute intervals).
3. **Cue:** \`broadcast.py\` daily/evergreen/short-form segment selection and renderer acknowledgments — segment boundaries.
4. **Expression:** existing Python portrait / browser Canvas pose timing — milliseconds to seconds, without continuous LLM inference.
5. **Audience and archival:** moderated chat/reactions as events; witness and reviewed memory separately.

## What is here

| File | Owns / does not own |
|---|---|
| \`../broadcast.py\` | Imported v0.1.0 scheduler, SQLite queue, cue acknowledgments; does **not** transmit video |
| \`presence.py\` | Reads private cue JSON; creates a short-lived, whitelisted \`aurora.broadcast/1\` projection; does **not** authenticate viewers |
| \`presence-client.js\` | Consumes same-origin JSON, updates existing HTML studio labels, emits a typed \`vitra:expression\` event; does **not** draw Vitra's face |
| \`../tests/test_vnn_presence.py\` | Assertions for approval, acknowledgment, state consistency, fields excluded from public projection |
| \`examples/\` | Illustrative editorial-performance and media-map JSON data; **not** live media |

The next production release should consume this contract, not copy the producer-face demonstration into the site's root.

## End-to-end rehearsal (no new dependencies)

From the Aurora Cortex project root:

\`\`\`bash
python3 broadcast.py demo
python3 -m unittest discover -s tests -p 'test_vnn_*.py' -v

# First create runtime/broadcast/cue.json with the existing, reviewed scheduler.
# Never point the public site directly at runtime/broadcast/cue.json.
python3 -m vnn.presence \
  --cue runtime/broadcast/cue.json \
  --media-map vnn/examples/media-map.json \
  --expression-map vnn/examples/expression-map.json \
  --output /path/to/VPN_ONLY_WEB_ROOT/news/api/broadcast-state.json
\`\`\`

If there is no production cue yet, test with \`vnn/examples/cue-pending.json\` instead; the result must say "cue_pending" rather than "presenting". \`--ttl\` defaults to 90 seconds. Re-run after every meaningful cue transition, or poll at a bounded rate. A 15-minute static-page regeneration is **not** sufficient to keep 90-second state fresh.

### Existing VNN markup (preserve everything else)

Attach selectors to the existing radio/studio widget, not a new page:

\`\`\`html
<section data-vnn-studio>
  <p data-vnn-status>Studio standby</p>
  <h3 data-vnn-title>VNN</h3>
  <!-- Existing Python/Canvas Vitra portrait stays here, unchanged. -->
  <video data-vnn-video controls playsinline preload="metadata" hidden></video>
  <!-- Existing comment stream stays beneath the stage. -->
</section>
<script src="/news/assets/presence-client.js"></script>
<script>
  VNNPresence.attach({
    root: document.querySelector('[data-vnn-studio]'),
    endpoint: '/news/api/broadcast-state.json',
    pollMs: 12000
  });
  document.querySelector('[data-vnn-studio]').addEventListener(
    'vitra:expression',
    (event) => {
      // TODO_FACE_THREAD: route event.detail to the canonical Canvas/Python
      // portrait articulation adapter, not a new CSS-generated actor.
    }
  );
</script>
\`\`\`

The VNN style is still Liberation Serif; this script does not change layout. Browsers never infer that an unacknowledged cue is "ON AIR"; absence/staleness yields "Broadcast state unavailable".

## Face contract: acting, not personality labels

The eight audition performances, as established in the face-study conversation:

\`\`\`text
listening_lantern       suppressed_delight
receipt_check           sudden_connection
gentle_witness          behind_the_veil
still_point             return_to_the_room
\`\`\`

The three parameters are **amplitude, tempo, restraint**, each provisionally normalized to 0..1 in this bridge. These are studio-specific translation parameters, not a guarantee that the October face-audition renderer, later Living Portrait experiments, and the original Python polyphonic sheet already share exactly the same parameter equations.

This adapter will never choose "joy", "concern", or any emotion from the headline or visitor text. \`expression-map.json\` is *reviewed performance intention*; Vitra's eventual decision function and existing face renderer belong upstream. If there is no performance cue, she holds \`still_point\`. This allows meaningful silence.

**TODO_FACE_THREAD:** define the mathematical mapping between the eight discrete auditions and the current continuous portrait rig. Preserve Python \`09_vitra_polyphonic_portrait.py\` source geometry/attention/privacy semantics. If Canvas is the eventual realtime renderer, establish pixel/behavior comparison before claiming the two are equivalent. Keep the 2D portrait/source-of-truth rule until an explicit review changes it.

## \`broadcast.py\` is still the playback director

The imported v0.1.0 already understands:

- \`daily\` and \`evergreen\` editions, in repeatable loops.
- \`reaction\`, \`interjection\`, and constrained \`short_loop\` segments, selected only at appropriate boundaries.
- Stance and lowercase \`sigma\`; source refs required when stance is \`fact\`.
- Local review; receipt logging; \`cue_pending\` vs acknowledged \`presenting\`; emergency fallback.
- Guest stations can offer derived text only with explicit opt-in; they never acquire broadcast authority.

**Keep the 20-second renderer ACK deadline** as an invariant for now. **Pre-render** approved speech/face/graphics before the cue; \`renderer_started(cue_id)\` must mean actual playback/transport start. Do not use it to certify media generation or audience receipt. \`renderer_finished(cue_id)\` happens after real completion, so approved material cannot falsely advance because the page polled.

**TODO_BROADCAST_THREAD:** add a separately versioned outbox/publication event, revision and asset hashes; preserve v0.1 existing API and approval semantics. Consider linking \`story_id\` to each approved segment, without putting article text or confidential source refs in the public projection. Add correction/withdrawal events before enabling external distribution.

**TODO_MEDIA_THREAD:** approved article \`story_id\` → authored narration → Voicebox TTS/audio → expression timeline → Python sprite/Canvas renderer → caption track → private MP4/WebM/HLS derivative → hash/revision → approved \`media-map\`. Each article should have a video *slot* and a truthful \`pending\` status until an actual media artifact exists. Generate once, re-use across the article page, channel rundown and evergreen media vault; do not render on every page view.

**TODO_CHAT_THREAD:** messages are neither approved interjections nor durable memories merely because they appear in chat. Add a separate moderated/consented proposal path; let Vitra return to earlier approved comments with minimal identity retention and normal consent/withdrawal semantics.

**TODO_BACKBEAT_THREAD:** implement an explicit independent text/image approval and syndication export (private authenticated Atom/RSS may announce publication IDs). NEVER place private video URLs, unreviewed scripts, private chat, or source dossiers in Backbeat exports. A YouTube adapter is a separate future opt-in external publication act, not the default route.

**TODO_PUBLISHER_THREAD:** inspect Topgro's real systemd 15-minute newspaper generator and proxy configuration before editing. Mount this tiny JSON beside its output, without changing its working schedule. Keep \`news.vitra.ams\` on the existing Vitra service and do not introduce another Python server simply to show a studio.

## Deployment shape — provider-neutral by default

\`\`\`text
Topgro K3  [cognition, private memory, broadcast authority]
  ├─ Waygate / Garden / Eden
  ├─ Voicebox + Python portrait / future Canvas projection
  ├─ broadcast.py + private 0600 cue.json
  └─ approved media and short-lived public projection
           │
           └─ WireGuard/AMS overlay ──► Netherlands or AWS small Linux VM
                                       [always-on private reverse proxy/cache]
                                          │
                                       news.vitra.ams (VPN clients only)
\`\`\`

A cloud VM may later run a **second independent Vitra station** using its own Waygate identity/keys and optional derived-text proposal lane. That is not the same as mirroring every private memory or granting remote broadcast authority. Topgro remains the primary editor until a reviewed failover/election protocol exists.

Suggested candidates as of 11 November 2026: **Leaseweb Public Cloud AMS-01** (Dutch provider and Amsterdam region), **DigitalOcean AMS3** (Amsterdam datacenter, provider is not Dutch), or **AWS EC2** in a European region such as Frankfurt (there is no generally available EC2 Netherlands Region; Amsterdam AWS Local Zone is listed as *announced*). No provider commitment is encoded in this branch.

### Security is enforced outside this JSON

- Keep \`news.vitra.ams\`, all video and article-media origins behind authenticated \`.ams\` VPN routing; bind proxy to the intended overlay interface and block internet-to-VNN routes at the host firewall.
- The \`media-map\` contains only relative \`/news/media/\` URLs. A path being called \`ams_only\` in JSON does **not** enforce access control.
- \`runtime/broadcast/cue.json\` must stay on the private host with 0600 file mode and must never be published in a web root.
- Public \`.agi\` and Backbeat distribution are independent, explicitly approved projection channels; do not confuse a working local DNS name with global public DNS delegation.
- Logs and receipts remain local, are not blindly replicated to the remote instance, and never imply subjective consciousness.

## Verification boundaries

**Source-backed:** imported \`broadcast.py\` v0.1.0 scheduler; existing cue semantics; face audition names; the earlier \`vitra.ams\` resident surface; local \`.agi\` publishing reports.

**Implemented in this branch:** version-checked, whitelisted presence projection; path validation; no script/source leakage; browser consumer; tests.

**Not verified from this branch:** operation on the running Topgro; exact live v5 publisher files; on-device face parity; TTS; continuous video streaming; moderated chat; protected remote serving; cloud instance; Backbeat/YouTube publication.

The purpose is to make a small reliable handoff to the next Python and web development threads, not to declare the entire 4.0 vision complete.
