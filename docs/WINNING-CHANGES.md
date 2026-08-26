# Winning changes — ranked

Every entry answers one question: **does this increase the probability of
selection?** If it does not, it is DELETE, however much work it was.

Ten days to the 5 September deadline.

---

## Scorecard

Current scores are judged against the **stated Track 04 bar**, not against our
own checklist.

| area | current | target | change |
|---|---|---|---|
| problem clarity | 9 | 10 | already strong; README now opens with problem → benchmark → insight → case |
| **Razorpay relevance** | **6** | 9 | adapter is real and tested, but nothing live. Honest positioning is the ceiling — **P0-3** |
| **AI necessity** | **7** | 10 | the measurement answers it decisively but is spoken, not led with — **P0-2** |
| AI measurement | 9 | 10 | 27/63 read from the artifact; missing an LLM baseline row — **P1-2** |
| technical depth | 9 | 10 | kernel, search-space integrity, membership invariant — strong |
| financial safety | 10 | 10 | six gates, 34 attacks, fail-closed. Do not touch |
| novelty | 8 | 9 | the authority boundary is the novelty; it needs naming, not building |
| UX | 9 | 9 | measured 10/10 stranger, zero overflow. **Stop polishing** |
| **demo memorability** | **6** | 10 | one cherry-picked case, no population, no failure, no audit trail — **P0-1, P0-2** |
| internship signal | 9 | 10 | three stories written; needs to reach the video |
| **credibility** | **4** | 10 | **the demo does not reproduce on a clean install** — **P0-1** |

Two numbers matter: credibility at 4, and demo memorability at 6. Everything
else is already competitive.

---

## P0 — could materially affect selection

### P0-1 · Make the demo reproduce on a clean install

**Problem.** Measured today: on `pip install -e .` without the Rust kernel,
`setl_000089` is `INSUFFICIENT` with zero proofs, the top blocker is
₹25,58,683.75 / 37 settlements rather than ₹47,96,811.78 / 197, and there are
four blockers rather than three. A judge following our README cannot reproduce
our pitch.

**Options, in order of preference:**

**(a) Move the canonical case to one that survives both execution paths.**
28 candidates exist on the numpy path with four surviving explanations and a
clean agreed/disputed split. The best is **`setl_000225`** — ₹27,208.12 credit,
4 explanations, ₹25,330.46 agreed across 6 orders, ₹5,603.30 disputed across 11.
Verify it is also AMBIGUOUS with the kernel, then it is canonical on any install.

**(b) Record the video on the default install** and quote the numpy-path
figures throughout. Zero gap between video and judge, but the headline drops
from ₹47.96L to ₹25.6L.

**(c) Surface the execution path in the product** — the bar already says
`GENERATED`; it could also say `NUMPY` or `NATIVE KERNEL`. Small, consistent
with the source-mode work, and it makes any discrepancy self-explaining. **Do
this regardless of (a) or (b).**

**Risk:** low — (a) is choosing a different id in documents; (c) is one label.
**Cost:** hours. **This is the single highest-value change available.**

### P0-2 · Reorder the demo: population first, case as evidence

**Problem.** The track bar is *throughput plus measured accuracy plus an honest
exception list*, and *"one cherry-picked match proves nothing."* We have all
three and lead with the match.

**Change.** `FINAL-DEMO-ARCHITECTURE.md` — throughput at 00:15, benchmark at
00:35, the full 250-settlement exception list at 00:55, and the single case at
01:20 as evidence for a claim already made.

**Risk:** none — a script change, no code. **Cost:** hours.

### P0-3 · Say the Razorpay boundary is the point, not the gap

**Problem.** We treat *"live validation NOT VERIFIED"* as a limitation to
disclose. Against a bar that rewards honest exception lists, it is a
demonstration.

**Change.** In the video: *"No engine module mentions Razorpay. The engine
cannot know which adapter produced its records — which is why the proof and
safety properties survive a change of source."* Verified: zero of fourteen
engine modules reference the provider.

**Risk:** none — wording. **Cost:** minutes.

---

## P1 — strong competitive advantage

### P1-1 · Show one runtime failure, handled — *"Failure Recovery"*

A **named evaluation dimension** we never demonstrate live. The material exists:
the webhook path already refuses duplicates, replay mismatches and bad
signatures through the real verification code. Add it to the demo at 03:35 and
show Activity's audit trail at 04:00. **No new capability — we currently just
skip it.**

### P1-2 · Add the LLM baseline row to the benchmark

Every competitor effectively *is* the naive-LLM baseline, and we do not measure
it. We have the harness, the ground truth and the proposer interface. Expected
outcome: near `greedy`. Publishing it either way is the strongest form of *"we
measured instead of trusting."*

**Risk:** medium — it is new measurement code in `attest/eval/`, not the engine.
**Cost:** a day. **Do only if P0 is done and time remains.**

### P1-3 · One-paragraph architecture doc for the submission

*"Architecture documentation"* is a stated requirement. `ARCHITECTURE.md` exists
at 166 lines; a judge needs the one-page version. Largely assembly of what
exists.

---

## P2 — polish, only if everything above is done

- Trust's capability matrix in the product rather than only the doc.
- The `.i-bound` instrument on the portfolio, not just per case.

---

## DELETE — does not increase winning probability

- **More tests.** 308 and 141 contracts already exceed what any judge will
  check. Another test is a day not spent on the video.
- **§IX's "Judge Mode".** A separate judge entry point duplicates the landing,
  which already answers six of ten stranger questions at zero clicks. Building a
  second front door says the first one failed.
- **More lenses, agents, chat, dashboards.** Against *AI Judgment*, each is a
  penalty.
- **Further UI polish.** Measured 10/10 stranger, zero overflow at seven widths,
  hierarchy survives blur. It is done.
- **Rewriting `api.py`.** Real debt, zero selection value in ten days.

---

## The recommendation

**Do P0-1, P0-2, P0-3 — then record the video.** They are days of work, not
weeks, and they convert a submission that is technically strong but
non-reproducible into one whose central claim a judge can verify on their own
machine in five minutes.

P1-1 if the recording slips a day. P1-2 only with time to spare.

**Nothing in P2 or DELETE before 5 September.**
