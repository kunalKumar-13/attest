# Submission checklist

Track 04 — AI Finance Controller. *"Build an agent that closes one finance-ops
loop across a 50+ record batch of synthetic data, reporting its match rate and
the exceptions it could not resolve."*

Razorpay asks for four things: pick a track, build something real, show your
work — a public repo, a five-minute pitch video, the architecture.

## Required

| | State | Where |
|---|---|---|
| Public repo | ✅ | `github.com/kunalKumar-13/attest` |
| README with a reading path | ✅ | `README.md` — the five-minute reviewer path opens it |
| Architecture | ✅ | `docs/ARCHITECTURE.md`, `docs/ARCHITECTURE-DIAGRAM.md` |
| **Five-minute pitch video** | ❌ **outstanding** | script and shot list ready: `DEMO-SCRIPT-35.md`, `DEMO-SHOTLIST-35.md` |
| Batch of 50+ synthetic records | ✅ 250 | first screen, and `benchmark/` |
| Match rate reported | ✅ 20.8% | first screen scoreboard |
| Exceptions it could not resolve | ✅ 198 | first screen scoreboard; the blocker register names the cause |
| Demo reproducibility | ✅ | `./run-demo`, seed 555001, `docs/REPRODUCE.md` |
| Known limitations | ✅ | `docs/CLAIMS.md`, Trust instrument, "what ATTEST does not claim" |

## The one outstanding item

The video is the only required deliverable not yet produced. It is also the
only artefact that guarantees a judge experiences the argument in the intended
order rather than scrolling fourteen screens at their own pace.

## Before recording

- [ ] `./run-demo` on a clean checkout; confirm seed `555001` and run count 250
- [ ] Confirm the four benchmark rows read 84/22/462/30 and 4.8/0.0/95.0/40.0
- [ ] Confirm the anchoring line reads 27 of 63, 42.9%
- [ ] Confirm Trust reads NOT VERIFIED for live account validation
- [ ] Browser at 1440×900, chrome hidden, no bookmarks bar
- [ ] Nothing on screen that is not ATTEST — no editor, no terminal, no Slack

## Claims discipline — do not say

production-ready · autonomous payments · AI-powered *(as the headline)* ·
100% accurate · lowest false-proof rate · live Razorpay data · real-time ·
enterprise-grade · the AI improved the verdict

## Claims discipline — do say

measured · deterministic · explainable · bounded · gated · held out ·
synthetic by design · refuses when unproven · diagnostic only

## Numbers cleared for use

Verified against the running product, seed 555001, and the artifacts.

```
₹51,35,744.40   processed          250 settlements · 2,328 orders
39 / 210 / 1    proven / ambiguous / contradicted
20.8%           match rate         198 exceptions it could not resolve
₹48,03,127.81   held at verification, across 198
₹47,97,685.11   blocked across the 210 AMBIGUOUS  (not the 198)
₹6,316.03       the 1 contradicted case — WORKSPACE ONLY, not on the front
                door. Do not speak it during the recording; it is here so the
                197/198 distinction is understood, not to be said aloud.
₹353.73         reached the ledger · 0 wrongly auto-posted
2,328 → 23 → 4 setl_000225 · AMBIGUOUS · ₹23,922.07
2 tested, 0 discriminative        anchor: capture-batch
27 of 63 = 42.9%                  anchoring benchmark
84/500 4.8% · 22/500 0.0% · 462/500 95.0% · 30/500 40.0%
panel: 500 = 2 seeds × 250, seeds 555001 and 999983 — not the live seed
35-line kernel · 6/6 gates · 35 attacks 0 breached · 21/21 modules clean
```

**The trap in this list:** ₹47,97,685.11 is the **210 ambiguous**, and **198**
are held at verification. The difference is the one contradicted case. Say one
or the other, never both in the same breath.
