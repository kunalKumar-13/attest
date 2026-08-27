# Product prototype review — ATTEST 10

Phase 10.1–10.3. Three interactive prototypes, four lenses each, the same data
through the same `data.js`, the same engine, the same canonical case
`setl_000089`. No prototype got an easier dataset and none invented content.

Screenshots: `img/proto-evidence.png`, `img/proto-policy.png`,
`img/proto-portfolio.png` — A, B, C top to bottom in each.

---

## The measurements

### The autopsy criteria

| | target | **A** | **B** | **C** | before |
|---|---|---|---|---|---|
| instrument starts at y | — | **0px** | 96px | 198px | 343px |
| instrument height | — | 699px | **804px** | 702px | 533px |
| instrument height as % of viewport | — | 78% | **89%** | 78% | 59% |
| widest *undivided* instrument | — | **1144px** | ~740px | **1440px** | 1180px |
| cross-lens redundancy | <25% | **49%** | 70% | 52% | 41–97% |
| worst pairwise overlap | — | **40%** | 67% | 44% | 76% |
| strings identical on every lens | — | **19** | 38 | **19** | 29 |
| lens conclusion in top-3 visual weight | 4/4 | **3/4** | 1/4 | **3/4** | 1/7 |
| max scroll | <1.5 screens | **1.0** | **1.0** | **1.0** | 6.8 |

### The tasks — clicks until the answer is on screen

Every prototype reaches `setl_000089` in one action; all seven tasks are
answerable in all three.

| task | A | B | C |
|---|---|---|---|
| 1 where did the money stop | 0 | 0 | 0 |
| 2 why is it ambiguous | 0 | 0 | 0 |
| 3 what is actually disputed | 2 | **1** | 2 |
| 4 what would resolve it | 0 | 0 | 0 |
| 5 can ATTEST auto-post this | **0** | **0** | 4 |
| 6 what did the AI do | 3 | 3 | 3 |
| 7 what should an operator do next | 0 | 0 | 0 |
| **total** | 5 | **4** | 9 |

### Product metrics

| | A | B | C |
|---|---|---|---|
| case object byte-stable across a lens change | **yes** | no | **yes** |
| case object shows identity **and** amount | yes | yes | yes |
| content kept Evidence → Investigate | 27% | **44%** | 31% |
| lens switch | **9ms** | 12ms | 13ms |
| context open | **3ms** | 4ms | 4ms |
| horizontal overflow at 360/393/430/768/1024/1512 | **all 0** | **all 0** | 239/206/169/0/0/0 |

### One metric that misled, recorded because it did

I defined "chrome %" as viewport area not available to the instrument, and it
scored **A 44%, B 12%, C 22%** — apparently making A worse than the product it
replaces. That number is wrong for the question. It counts A's case rail as
chrome, and the rail is the **case object** — identity, amount, verdict, spine,
agreed, disputed, next action — every part of which is case-specific and changes
with the case. It is content that was asked for, not overhead.

The autopsy's actual complaint was never "chrome exists". It was **343px of
identical pixels stacked above every instrument, squeezing it into 533px**. The
honest measure is the height the instrument gets, and by that measure the
ranking inverts. Recording this rather than quietly dropping the metric: it was
a bad proxy and it nearly chose the wrong winner.

---

# A — FINANCIAL TERMINAL · **WINNER**

### Strengths

**The instrument starts at y=0.** The autopsy's finding is not reduced, it is
eliminated. 533px → 699px of height, +31%, with nothing above it at all.

**The case object carries the answer, not just the label.** The rail holds
`AGREED ₹97,759.84 / DISPUTED ₹7,292.03` and the next action, persistently, on
every lens. Neither other direction does this — B's line carries identity,
amount and verdict; C's head carries identity, amount and the stage map. **A is
the only direction where you can read what the case concluded without reading
the instrument.**

**Conclusion in the hierarchy on 3 of 4 lenses**, against 1 of 7 today.

**Widest undivided instrument.** B has more raw room but splits it, so any
single instrument gets ~740px against A's 1144px. It shows: A's explanation bars
are the longest and most readable of the three.

**Zero overflow at every width tested**, and the fastest transitions (9ms/3ms).

### Weaknesses

- 19 strings still repeat across lenses — better than 29, short of the <25%
  redundancy target at 49%.
- Portfolio is the weakest of its own screens: actions are a list, without C's
  inline case rows.
- Policy is a strong thesis statement (PROOF → POLICY → ACTION, "never MODEL →
  ACTION") but leaves the lower half of the room empty.
- The rail is a fixed 296px tax. On a 1280px laptop the instrument is 984px.

**Score: 8.5 / 10**

---

# B — INVESTIGATION WORKSTATION · deleted

### Strengths

**The most room and the best continuity, measured.** 804px of height, 89% of the
viewport, and 44% of content survives Evidence → Investigate — the highest of
the three, which is exactly the bet it made. Fewest total clicks (4).

**The specimen genuinely persists.** On Policy you see the evidence and the
consequence at once, which no other direction offers.

### Why it lost

**Redundancy 70% — the worst of the three, and worse than most of the current
product.** The premise creates it: if the specimen persists, consecutive lenses
share most of what is visible. The thing that makes continuity felt is the same
thing that makes the lenses look alike.

**Conclusion in the top-3 on 1 lens of 4.** The case line is a single row of
small type, so nothing on the screen competes with the specimen — and the
specimen is the *same* on every lens, so the lens's own conclusion never
dominates.

**Dividing the bench costs more than it buys.** Every instrument gets ~740px.
Its right-hand panes were consistently the thinnest content in the experiment:
21 relationship rows on Evidence, a mostly-empty pane on Policy.

**The case object is not stable** — the spare slot rewrites on every lens.

**Score: 6.5 / 10**

---

# C — OPERATIONS CONTROL ROOM · deleted

### Strengths

**The best portfolio screen produced in this experiment.** "What to do first ·
value unlocked ÷ operator effort", then each group with its value, its cases,
its per-step figure, and the settlement rows inline. An operator can see the
work and the cases in it without leaving.

**The best Policy of the three, and it is not close.** It shows the boundary
**across all 250 settlements** — `1 AUTO-POST · 249 REVIEW · 0 BLOCK`, expected
loss against cost of checking — beneath this case's UNPRICED. That is how a
policy is actually evaluated; one case's decision means little alone.

**The spine is a genuine control**, five stage buttons that scope the queue.

### Why it lost

**Nine clicks against A's five.** Instruments apply to an opened case, so
Policy costs four clicks where A costs zero.

**The case answer is not persistent.** The head carries identity, amount and the
map — not agreed, disputed, or next action. Change lens and the conclusion goes
with the instrument.

**It overflows on mobile** — 239px at 360. Fixable, but it is the only
direction that failed a guarantee the current product holds.

**Score: 7 / 10**

---

## What the winner changes

1. The lens strip stops being a horizontal band. Instruments move to the rail's
   foot — 46px × 7 of identical pixels recovered.
2. The subject header stops being a band above the workspace. The case becomes a
   rail written once and never re-rendered.
3. The spine moves into the rail as a vertical flow and becomes a control.
4. The instrument gains the full viewport height, starting at y=0.
5. The rail gains two live slots — **now** and **next** — so agreed, disputed
   and the next action are legible on every lens.
6. Each lens's own conclusion is promoted into the top three by visual weight.

## What the winner preserves

The engine and everything beneath it, untouched. In the UI: the spine's
proportional collapse; the 34px amount as the financial subject; subject × lens
× context with URL addressability; context-origin motion, focus return and
scroll persistence; the stale-fetch guard; ◇ MODEL → ○ SOLVER → ● ENGINE;
`UNPRICED` rather than a fabricated zero; Trust leading with failures; the
Razorpay boundaries; the candidate-universe visualisation; every WCAG,
keyboard and reduced-motion guarantee; all 94 browser contracts.

## What was sacrificed

Named, because choosing means losing and a review that pretends otherwise is a
sales document.

- **C's across-the-group Policy.** The strongest single screen in the
  experiment, and A does not have it.
- **C's work queue with inline case rows.** A's portfolio is weaker for it.
- **B's persistent specimen.** Evidence → Investigate keeps 27% in A against
  B's 44%.

Per §10.3 these were not merged in. If any is later shown to be load-bearing it
returns as a deliberate change to A, argued on its own, not as a graft.

---

## Migration plan

Six steps, each independently verifiable, all 94 contracts green throughout.

| # | step | risk | check |
|---|---|---|---|
| 1 | Move the case object into a rail: `#app` becomes two columns, `#subject` the left. Header and strip stop being bands. | layout only | contracts asserting `.c-subject` and `#lenses` still resolve |
| 2 | Move the spine into the rail; delete `#w-spine`. | the spine must stay on all 14 views | the existing spine contract |
| 3 | Add the rail's `now` / `next` slots, written by each lens. | new surface | a contract that agreed/disputed is visible on every settlement lens |
| 4 | Promote each lens's conclusion into the type hierarchy. | typography only | re-run the attention proxy; target 7/7 |
| 5 | Re-point contract selectors that named a band rather than a concept. | test churn | each change argued in the commit, as in 9.3 |
| 6 | Responsive: rail → top band under 768px. | mobile | zero overflow at all six widths |

**Steps 1–3 are structural and should land together**, because a rail without
the case object is just a narrower page. Steps 4–6 are independent.

No micro-polish — no hover, shadow, gradient or microcopy work — until all six
land and the metrics are re-measured.
