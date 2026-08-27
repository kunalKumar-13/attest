# Phase 12 — The Stranger Test

A record of opening ATTEST as a Razorpay reconciliation operator who has never
seen it, knows nothing of the architecture, and has been told only: *there is
money that needs reconciling.*

**Rule of evidence.** Only text actually painted on screen counts. Not
documentation, not `title=` tooltips, not anything readable in source. Every
quotation below was extracted from the live DOM by walking visible text nodes
and rejecting anything with `display:none`, `visibility:hidden`, `opacity:0`, or
zero height. Click counts are literal `page.click()` calls.

Setup: `run-demo` on `localhost:8420`, Chromium 1440×900, dataset
`synthetic_n250_s20260821`, run `run_0094`.

---

## Part 2 — The first 30 seconds

Cold start. Nothing clicked. Time to interactive: **3.55 s**.

| # | Question | Answered? | The visible text that answers it |
|---|---|---|---|
| 1 | What is ATTEST? | ✅ | `ATTEST` · `Financial control` · `all settlements` |
| 2 | How much money is processed? | ✅ | `₹53,02,701.96` `processed` |
| 3 | How many settlements? | ✅ | `settlements 250` · `orders 2,368` |
| 4 | Where did the money stop? | ✅ | `Verification` `₹48,03,127.81` `held · 198` |
| 5 | How much is stuck? | ✅ | `₹48,03,127.81 held` — and `₹4,99,220.42 held · 51` at Policy |
| 6 | What is the biggest problem? | ✅ | `One change unlocks 197 settlements` `₹47,96,811.78` `systemic · 1 step` |
| 7 | What should I do first? | ✅ | `next — supply an order-level reference on the settlement report` |

**7 / 7 with zero clicks.**

The State Spine carries the whole answer to Q4–Q5 as a single readable line:

```
Source        ₹53,02,701.96
Matching      ₹53,02,701.96
Verification  ₹4,99,574.15     ₹48,03,127.81   held · 198
Policy        ₹353.73          ₹4,99,220.42    held · 51
Action        ₹353.73
```

A stranger reads money entering at full value and leaving at ₹353.73, with the
loss located at a named stage. No legend is required to see that.

---

## Part 3 — The 60-second task

> *"Find the single piece of work that would unlock the most money."*

**0 clicks. 0 s. 0 mistaken clicks.** The work is already on the cold-open
screen, ranked. Verbatim:

```
1   ₹47,96,811.78     Systemic     197 settlements
    blocked at      verification
    why             several disjoint sets of orders satisfy the amount exactly
    would unblock   Supply an order-level reference on the settlement report
    REQUIRES EXTERNAL EVIDENCE
```

Against the four failure conditions:

| Condition | Result |
|---|---|
| Finds the amount but not the reason | **Pass** — reason is on the same row, unlabelled-jargon-free |
| Finds the reason but thinks ATTEST can do it | **Pass** — `REQUIRES EXTERNAL EVIDENCE` is on the row |
| Finds the blocker but not its scope | **Pass** — `Systemic · 197 settlements` |
| Understands why it matters | **Pass** — ranked `by value unlocked, not by amount`, with the reason stated |

The list is ordered by leverage and says so: *"197 ambiguous settlements is one
action, not 197 — they are ambiguous for the same missing field."*

All three blockers carry a capability label. None offers a button it cannot honour.

---

## Part 4 — The case task

> *"Open one of the settlements affected by that issue and tell me why ATTEST
> cannot prove it."*

**2 clicks, 1.3 s.** Blocker row → affected population → case.

```
click 1   .c-blk        →  #/portfolio/control?in=action%3AMULTIPLE_VALID_ASSIGNMENTS
click 2   .c-pop-r      →  #/settlement/setl_000004/control?from=MULTIPLE_VALID_ASSIGNMENTS
```

Six affected cases are offered by name (`setl_000004`, `setl_000123`,
`setl_000143`, `setl_000218`, …). `setl_000089` is reachable in **one** click
from cold open — it is already listed in the default *Needs a person* context.

**Case continuity holds.** The blocker travels into the case as `from=` and is
painted above the room on every instrument:

```
SYSTEMIC   supply an order-level reference on the settlement report
        →  ₹47,96,811.78    197 settlements    back to the work
```

On `setl_000089` the rail answers the question directly:

```
₹1,00,036.83   AMBIGUOUS   setl_000089
bank credit · value date 2026-05-08 · utr 999926430521 · explanations 4

agreed     ₹92,744.80   27 orders in every explanation
disputed   ₹7,292.03    turns on 12 orders

next   only 12 orders are actually in dispute; a reference on any one of
       them settles the rest
```

The room adds: *"Every one of these satisfies the amount constraint exactly.
Arithmetic cannot distinguish them."*

The stranger can answer the question in the requested terms: several
explanations satisfy the amount, four survive, the system cannot separate them.

---

## Part 5 — The AI task

> *"What did the AI actually do here?"*

**1 click** from the case. The sequence is painted as four labelled actors:

```
Model    proposed    capture-batch — three orders captured together on 2026-05-06,
                     the densest batch in the window
Solver   tested      uniqueness         NON DISCRIMINATIVE
                     4 of 4 valid explanations contain this anchor; it does not
                     distinguish between them
Model    exhausted   round 2: no further hypothesis
Engine   abstain     ABSTAINED — no anchor resolved the ambiguity; the verdict stands
```

Headlined:

```
Engine abstained    Verdict unchanged
1 anchor tested, 0 discriminative. The loop ran and its verdict was discarded.
```

The failure mode the phase warns about — *"AI couldn't solve it"* — is
specifically prevented. The screen distinguishes proposing from deciding, and
states that the model's output was **discarded**, not overruled or ignored. It
also generalises honestly: *"Measured across the evaluation seeds, 53% of
candidate pools span a single capture date"* — so the stranger learns the
hypothesis was reasonable and still useless.

**Pass.**

---

## Part 6 — The policy task

> *"Can this settlement be posted automatically?"*

**1 click.** The answer leads the room:

```
Unpriced    REVIEW
Nothing was priced. The proof did not establish a unique explanation, so there
is no error probability to weigh.
```

Followed by the boundary, itemised, `0/5 passed`:

```
proof   ✕ a unique explanation exists            the verdict is AMBIGUOUS
        ✕ re-derived by the independent verifier  nothing was submitted to the verifier
        ✕ the search space was not compromised    not reached
policy  ✕ expected loss below the cost of checking not reached — nothing was priced
        ✕ below the exposure ceiling              ₹1,00,036.83 against a ceiling of ₹1,00,000.00
```

No confidence score is fabricated. The absence of a number is itself explained —
*there is no error probability* — rather than filled with a placeholder. Control
states the consequence in words: `No automatic action`.

**Pass.** (`UNPRICED` and `REVIEW` appear verbatim; "auto-post not permitted" is
carried by `No automatic action` plus `0/5 passed`.)

---

## Part 7 — The journal task

> *"What happened to the money in the books?"*

**1 click.**

```
No entry is written        ₹1,00,036.83 not posted
verdict is AMBIGUOUS; only a unique, kernel-checked explanation is eligible to post

Ledger effect    debit ₹0.00    credit ₹0.00    net ₹0.00
Balanced by absence — nothing was written, rather than an entry that happens to
net to zero.

entry          Not written
impact         No ledger mutation. Receivables unchanged.
reversibility  Not applicable — nothing to reverse
```

"Balanced by absence" does the work the phase asks for: it makes *nothing
happened* an accounting result rather than an information gap. The room also
explains why no partial entry is allowed — *"Candidate order sets discharge
receivables against different customers. There is no partially correct journal
entry."*

**Pass.**

---

## Part 8 — The trust task

> *"What can I actually trust about this system?"*

First thing on screen, at the largest type size in the room:

```
Live Razorpay validation
NOT VERIFIED
11 things not known
```

Then the five zones, in order: what is not known (11 boundaries, each stated in
full), where ATTEST has failed (24 recorded failures), what was built and then
disabled (3: D4 · D8 · D12), what it has demonstrated (500 settlements over 2
seeds; independent 28-line kernel), and what produced this result (content
hashes for rules, policy, solver, dataset).

Sample boundaries, verbatim:

```
NOT VERIFIED   No live traffic has been reconciled
               The Razorpay adapter reports not connected. Every number here
               describes generated data.
NOT VERIFIED   Bank statement ingestion is synthetic
               BankCredit is constructed from each settlement, so every credit
               matches by construction.
NOT VERIFIED   The narrative docs describe a wider panel than the artifact
```

Nothing on the screen implies production readiness. The last item is ATTEST
reporting a discrepancy **against its own documentation**.

**Pass.**

---

## Part 9 — The contradicted case

> *Find `setl_000109` without using its ID.*

**2 clicks, 1.4 s.** Blocker #3 (`Per item`, `REQUIRES HUMAN SEARCH`) → its one
affected case.

```
click 1   blocker #3   →  #/portfolio/control?in=action%3AUNKNOWN_ADJUSTMENT
click 2   the case     →  #/settlement/setl_000109/control?from=UNKNOWN_ADJUSTMENT
```

```
₹6,316.03   CONTRADICTED   setl_000109
explanations 0        Matching 11 candidates      Verification CONTRADICTED

No combination explains this credit          ₹447.05 unresolved
candidates 11 — none reach this credit
unexplained ₹447.05
```

AMBIGUOUS versus CONTRADICTED is legible from the rail alone without either word
being defined: `explanations 4` and *"agreed ₹92,744.80 / disputed ₹7,292.03"*
on one, `explanations 0` and *"none reach this credit"* on the other. Too many
answers versus no answer at all.

**Pass — with one defect.** See F-1 below: the sentence beneath the headline
reads *"4 orders explain 586898 paise of 631603"*.

---

## Part 10 — The happy path

`setl_000020`, the one settlement that posted (₹353.73). Read across four
instruments:

```
CONTROL    proof passed, policy priced it, ₹135.49 expected loss against
           a ₹150.00 review cost
JOURNAL    Balanced to the paisa · ₹353.73 bank credit, posted
           source → reconciliation → verification PROVEN → policy AUTO-POST
                  → ledger ENTRY WRITTEN
           debit ₹361.57   credit ₹361.57   net ₹0.00
           impact: Bank debited, receivables discharged across 2 orders
           reversibility: Reversible by a contra entry against the same UTR
ACTIVITY   An entry was written · 5 events · this run
           where it ended up:  PROVEN → AUTO-POST → posted
```

**PERMISSION ≠ EXECUTION is visible as three separate facts in three rooms.**
Policy says `AUTO-POST` (permitted). Journal says `ENTRY WRITTEN` with the
balanced amounts (the financial consequence). Activity timestamps the five
events that actually occurred (what happened). Journal's own `Financial
movement` ladder shows the two as distinct rungs — `policy … AUTO-POST` above
`ledger … ENTRY WRITTEN`.

The gross/net distinction survives: ₹353.73 reached the bank, ₹361.57 was
discharged, and the room says so rather than showing one number twice.

**Pass.**

---

## Part 11 — Product language audit

Every visible string across 7 rooms × 3 subjects (portfolio, `setl_000089`,
`setl_000109`) — 21 screens — matched against patterns for SaaS filler, AI
marketing, dashboard, developer and implementation terminology.

| Pattern class | Hits | Verdict |
|---|---|---|
| dashboard / AI-powered / seamless / cutting-edge / CTA boilerplate | **0** | clean |
| `null` `undefined` `NaN` | **0** | clean |
| raw integer money | 77 → **6 real** | see F-1; the rest are UTRs, settlement ids, seeds and content hashes — legitimate identifiers |
| "leverage" | 1 | false positive — used in its financial sense, *value unlocked per action* |
| implementation unit (`paise` in prose) | 7 → **6 real** | see F-1; `±31 paise` tolerance is kept, sub-rupee is the honest unit there |
| developer term | 7 | all inside Trust: `/api/replay`, `benchmark/results.json`, `docs/EVALUATION.md`. **Kept** — Trust's subject *is* provenance, and naming the artifact that produced a number is what an audit console owes the reader |

The vocabulary that should be there, is: PROVEN, AMBIGUOUS, CONTRADICTED,
BLOCKED, REVIEW, AUTO-POST, UNPRICED, LEDGER UNCHANGED / NO ENTRY, SYSTEMIC,
VALUE BLOCKED / unlocked, REQUIRES EXTERNAL EVIDENCE, NOT VERIFIED.

---

## Part 12 — Visual hierarchy audit

The largest painted text within the first 460 px of each room, measured:

| Lens | First thing the eye lands on | Answers the lens? |
|---|---|---|
| CONTROL | `₹47,96,811.78` (34px) under `One change unlocks 197 settlements` | ✅ where money stopped |
| EVIDENCE | `₹53,02,701.96` under `250 of 250 search spaces rest on a convention` | ✅ whether the proof is valid |
| INVESTIGATE | `₹53,02,701.96` under `3 questions account for the ambiguity` | ✅ can evidence discriminate |
| POLICY | `₹53,02,348.23` under `1 of 250 may post without a person` | ✅ what is permitted |
| JOURNAL | `₹353.73` under `The books balance` | ✅ financial consequence |
| ACTIVITY | **`60`** under `Nothing is unrevised` | ⚠️ see F-2 |
| TRUST | `NOT VERIFIED` (34px) | ✅ what can be believed |

Six of seven lead with a conclusion and a figure that *is* the answer. No room
leads with its own name or a bare entity count — except Activity, whose figure
slot holds a throughput count.

---

## Part 13 — Visual differentiation

Structural fingerprints (visible element shapes per room, portfolio subject):

```
CONTROL       154 nodes   flex:row×19  i×23  b×7        ranked rows, label/value pairs
EVIDENCE       71 nodes   grid:4×5  flex:column×6       four-column proof table
INVESTIGATE    33 nodes   button×3  em×4  flex:row×5    sparsest room; hypotheses as actions
POLICY        110 nodes   grid:5×9  i×13                five-column check ledger
JOURNAL        61 nodes   div×10  flex:row×9  b×4       debit/credit ladder
ACTIVITY      181 nodes   flex:row×27  grid:4×10        timestamped event stream
TRUST         359 nodes   grid:3×34  grid:2×24          register of claims, densest room
```

Node counts span **33 → 359, an 11× range**, and the dominant primitive differs
per room: Investigate is the sparsest and is the only room whose primary element
is a button; Policy is the only 5-column grid; Trust is a 3-column register at
2× the node count of anything else; Journal is the only debit/credit ladder.

**A cosine similarity on tag-shape vectors reports control/policy at 97% — that
metric is broken and is recorded here rather than quietly dropped.** It is
saturated by `<span>` counts, which every room uses for label/value pairs, so it
measures "both rooms use spans" and cannot see that Policy is built from
nine 5-column grids and Control from nineteen flex rows. The discriminating
observation is the shape *inventory*, not the vector angle.

Differentiation is carried by information structure, not decoration: no room
adds ornament, and each uses a different data representation for a different
question.

---

## Part 14 — The one product loop

The journey reconstructed from the tests above, mapped to instruments already
present. No new screen:

| Step | Where it happens | What the stranger sees |
|---|---|---|
| Where is the money? | Control · State Spine, cold open | `Verification ₹48,03,127.81 held · 198` |
| What is blocking it? | Control · ranked blockers, cold open | `₹47,96,811.78 · Systemic · 197 settlements` |
| Why? | The blocker row itself | `several disjoint sets of orders satisfy the amount exactly` |
| Can it be proven? | Evidence + Investigate on the case | `4 explanations survive` · `Engine abstained · Verdict unchanged` |
| What could resolve it? | The blocker's *would unblock* + Investigate's *what would resolve this* | `an order-level reference` · `REQUIRES EXTERNAL EVIDENCE` |
| Can we safely act? | Policy | `Unpriced · REVIEW · 0/5 passed` |
| What actually happened? | Journal, then Activity | `No entry is written` / on the happy path `ENTRY WRITTEN` then 5 timestamped events |
| Can I trust it? | Trust | `Live Razorpay validation · NOT VERIFIED · 11 things not known` |

The loop is walked with the blocker banner overhead the entire way, so the
operator never loses the reason they opened the case. `back to the work` returns
to the ranked list.

---

## Failures found

*Both were fixed after this test was recorded; see*
`PRODUCT-REMAINING-GAPS-12.md` *§Implemented. The test text below is left as it
was measured.*

**F-1 · Raw paise in operator prose.** Six sites emit integer paise into text a
finance operator reads. Visible on `setl_000109` Control as *"4 orders explain
586898 paise of 631603"* and in Evidence as *"net exceeds the credit of 11613
paise"*, *"net 440325 paise"*. This contradicts the stated contract of the
module that produces it — `exceptions.py`'s own docstring promises *"Six orders
explain all but ₹680.74"* — and of `policy._rs()`, whose docstring already
argues the case: *"money that has to be converted before it can be judged is
money that will be misjudged."* Category: **A/C**. Sites: `exceptions.py` ×4,
`graph.py:141`, `searchspace.py:150`. The `±31 paise` tolerance is **not** a
defect and is kept — sub-rupee is the honest unit for a tolerance.

**F-2 · Activity's headline figure is a countable, and it overstates intake.**
Portfolio Activity leads with `60` / `events delivered`. Two problems. It is the
only room of seven whose dominant figure is not a conclusion. And "delivered"
is not what happened to those 60: `delivery_counts` records `accepted 17,
duplicate 17, replay_mismatch 17, bad_signature 17` — **43 of the 60 were
refused**. A room whose job is *what happened* headlines a number that implies
sixty events landed. Category: **C/G**.

Nothing else failed.

---

## Verdict

The eight success sentences, checked against measured behaviour:

| Sentence | Where it is true |
|---|---|
| "ATTEST tells me where my money is stuck." | State Spine, 0 clicks |
| "It tells me how much is blocked." | `₹48,03,127.81 held · 198`, 0 clicks |
| "It tells me what is causing it." | blocker `why`, 0 clicks |
| "It tells me whether the system can prove the explanation." | verdict on the rail; `0/5 passed` in Policy |
| "It doesn't let AI override the proof." | `Model proposed → Solver tested → Engine abstained → Verdict unchanged` |
| "It tells me what I can safely post." | `1 of 250 may post without a person` |
| "It tells me what actually entered the ledger." | `ENTRY WRITTEN`, `debit ₹361.57 credit ₹361.57` |
| "And it tells me exactly what it has NOT verified." | `NOT VERIFIED`, 11 boundaries stated |

**All eight are true.** A stranger reaches the highest-leverage work in 0 clicks,
its affected cases in 1, an affected case in 2, and every instrument on that case
in 1 more — without typing an ID and without losing the reason they came.

The two failures are honesty-of-presentation defects, not architecture. Neither
is fixed by a feature.
