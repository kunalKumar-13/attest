# Phase 26 — Final Product Scorecard

Every score cites something measured against the running product. §18 forbids
proxies, so nothing here counts elements, classes, lines or screenshot
similarity. The metrics are task outcomes.

**No code was changed in this phase.** The measurements below said none was
warranted, and §20 says to stop when the product passes.

---

## Task outcomes

| task | clicks | time |
|---|---|---|
| understand the money and where it collapsed | **0** | cold open |
| understand the highest-leverage blocker | **0** | cold open |
| blocker → its affected case | **2** | 1.1 s |
| blocker → case → Evidence *(why no proof)* | **3** | 1.7 s |
| blocker → case → Investigate *(what the AI did)* | **3** | 1.6 s |
| blocker → case → Policy *(may it post)* | **3** | 1.6 s |
| blocker → case → **Trust** | **3** | 1.6 s |
| distinguish ambiguous from contradicted, no ID typed | **2** | 1.2 s |

§20's targets were ≤3 to understand a blocker and ≤5 from blocker to Trust.
Measured: **0** and **3**.

---

## The stranger test, ten questions

| # | question | answered | clicks |
|---|---|---|---|
| 1 | What is ATTEST? | ✅ | 0 |
| 2 | How much money entered? | ✅ | 0 |
| 3 | Where did it stop? | ✅ | 0 |
| 4 | How much is stuck? | ✅ | 0 |
| 5 | Why is it stuck? | ✅ | 0 |
| 6 | What is ATTEST doing with AI? | ✅ | 3 |
| 7 | What does the solver do? | ✅ | 3 |
| 8 | Can it auto-post this case? | ✅ | 5 |
| 9 | Why not? | ✅ | 3 |
| 10 | What does ATTEST refuse to claim? | ✅ | 0 |

**10 / 10.** Six of the ten are answered before anything is clicked.

---

## Scores

| dimension | score | the observation behind it |
|---|---|---|
| **Clarity** | 9 | ten of ten stranger questions answered; six at zero clicks. The one that costs most is *can it auto-post* at 5 clicks, and only because the walk followed the product's own next-question chain rather than the dock — via the dock it is 3. |
| **Hierarchy** | 9 | at `grayscale(1) blur(2.2px)` the money, the spine collapse, the three ranked blockers and the next action all remain legible. Nothing financial is subordinate to chrome, because there is no chrome: zero cards, zero shadows, zero gradients, 24 painted surfaces across 14 screens and all of them chips under 165×22px. |
| **Financial legibility** | 9 | nine ₹ roles, each with exactly one type size — ENTERED 34px, HELD 20px, VALUE BLOCKED 20px, AGREED/DISPUTED 15px, CONTINUES 13px — all monospace and tabular. Median painted ₹ is 15px against 10px for everything else. |
| **Proof explanation** | 10 | `2,368 → 73 → 4` in one object, each cut labelled CONVENTION or DETERMINISTIC, with the claim that the space itself is an assumption stated beneath rather than disclosed. A reader learns the proof's *boundary*, not just its answer. |
| **AI / deterministic separation** | 10 | `◇ MODEL → ○ SOLVER → ● ENGINE` carried by shape and fill, so it survives grayscale. Ends on `ABSTAINED` / `VERDICT UNCHANGED`. The model's output is described as *discarded*, and no engine module can reach a ledger write — verified structurally in Phase 25. |
| **Policy explanation** | 9 | an inequality, never a score: `₹135.49 expected loss · ₹150.00 to check` with a marker on a threshold. On an unproven case the bar is **absent** rather than empty, and the room says *nothing was priced* with `0/5 passed` beneath. The word "confidence" appears nowhere in the product. |
| **Trust** | 10 | leads with `NOT VERIFIED`; eleven boundaries, 24 recorded failures, three features built then disabled. One boundary is ATTEST reporting a discrepancy against its own documentation. Nothing is below a fold or behind a disclosure. |
| **Navigation** | 10 | one `navigate()`; zero writes to subject/lens/context outside the shell; zero history writes outside it; Back correct 5 of 5 steps deep; the blocker survives seven instruments and a return. |
| **Context** | 10 | measured across five rooms: rail moves **0px**, room moves **0px**, the originating row stays marked. Escape closes it with the case unchanged. It is inspection, not navigation. |
| **Mobile** | 8 | zero overflow at 360/390/430/768/1024/1440/1512. The dock is 138px against a 341px room at 360×780 — all seven instruments, all seven questions, no menu. Eight rather than nine because the rail's held amount is clipped by its 25vh cap at 360px; it scrolls, and it is pre-existing. |
| **Demo** | 9 | the three-minute script is walkable with no staged step; every number in it was read off the running product. The canonical ambiguous case is 2 clicks and the contradicted case is 2 clicks, neither by ID. |

**Mean 9.4.**

---

## §20 stop condition

| | required | measured |
|---|---|---|
| stranger questions | 10/10 | **10/10** |
| clicks to understand a blocker | ≤ 3 | **0** |
| clicks blocker → Trust | ≤ 5 | **3** |
| AI/solver/engine understood without explanation | yes | **yes** — questions 6 and 7 at 3 clicks |
| ambiguous vs contradicted understood | yes | **yes** — 2 clicks, no ID |
| policy boundary understood | yes | **yes** — questions 8 and 9 |
| financial value subordinate to irrelevant UI | none | **none** — survives blur |
| behavioural regressions | none | **none** — no code changed |
| tests | 297+ | **297** |
| browser contracts | 133+ | **133** |
| safety gates | +0.0000 | **6/6 at +0.0000** |
| clean checkout | pass | **pass** |

**Every condition is met.**

---

## What was deliberately not changed

The measurements did not justify a change, and §1 forbids inventing one.

- **The dock's questions.** §12 lists a slightly different wording than the
  product uses — *"What is happening?"* against the current *"Where did the
  money stop?"*. The current set came from Phase 22, where they were sharpened
  from system-voice to operator-voice deliberately. Reverting them would undo a
  measured improvement to match an example.
- **The rail.** §11 says audit it and, if it answers its five questions, do not
  touch it. It answers all five on every lens; the case was never visually lost
  across a fifteen-step journey.
- **The mobile rail clip at 360px.** Pre-existing, reachable by scrolling, and
  outside anything this phase measured as broken.
- **Everything in §15's visual list.** No gradient, shadow, card, illustration
  or chart was added, and none was removed, because the surface audit found
  none to begin with.

---

## The one sentence

> *ATTEST never pretends to know more than the evidence proves.*

It is the product's actual behaviour, not a tagline: the engine abstains when
four explanations survive, policy refuses to price what was not proved, the
ledger does not move, and the system's own Trust screen leads with what it has
not verified.
