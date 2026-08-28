# ATTEST

**It won't move money it can't prove.**

Financial reconciliation that reports what it proved, what it could not, and
hands the unresolved work to a person.

```
₹53,02,701.96   processed
₹48,03,127.81   stopped at verification
197             settlements blocked by one missing piece of evidence
```

```
MODEL     proposes.
SOLVER    tests.
ENGINE    decides.
POLICY    permits.
LEDGER    records.
OPERATOR  resolves what evidence could not.
```

## For a reviewer — the five-minute path

If you only open three files: [`attest/verdict.py`](attest/verdict.py) is the
28-line proof kernel and it does not import the solver — the solver imports it.
[`attest/eval/baseline_panel.py`](attest/eval/baseline_panel.py) is the
benchmark that ATTEST loses on precision. [`attest/adapters/razorpay.py`](attest/adapters/razorpay.py)
is the only module that knows Razorpay exists; it is read-only and has no write
scope. Everything on screen describes generated data, always labelled as such.

Track 04 asks for an agent that closes one finance-ops loop across a 50+ record
batch of synthetic data, **reporting its match rate and the exceptions it could
not resolve.** ATTEST runs 250 settlements, reports a 20.8% match rate on the
native kernel (both execution paths are tabled below), and the
198 exceptions it could not resolve are the product rather than a footnote —
and they leave the system as a work queue, with the contested orders, the
blocker and the evidence that would settle each one:

```bash
curl "http://127.0.0.1:8420/api/export/queue?run=<id>&format=csv"
```

That export is a read. `tests/test_export_safety.py` pins it: the run, the
ledger and the filesystem are compared before and after, and the source is read
for the names of every mutating call.

### Reproduce the demo

```bash
git clone https://github.com/kunalKumar-13/attest && cd attest
python3.13 -m venv .venv && ./.venv/bin/pip install -e .
cd native && maturin develop --release && cd ..   # optional kernel — see below
./run-demo
```

**Two execution paths, and the demo uses the first.**

| | solver envelope | this run of 250 |
|---|---|---|
| **Native kernel** — the recorded demo | ₹2,00,000 | 52 proven · 197 ambiguous · 1 contradicted |
| **Portable** — no Rust toolchain needed | ₹30,000 | 51 proven · 161 ambiguous · 1 contradicted · **37 insufficient** |

The 37 are not failures. They are settlements whose candidate space exceeds
what the portable solver will attempt, so it reports INSUFFICIENT rather than
searching a space it cannot finish — the same refusal the rest of this
document is about, applied to compute instead of evidence.

`./run-demo` prints which path is active **before** any portfolio figure, so
the two can never be confused.

**The canonical case is identical on both.** `setl_000225` — ₹27,208.12,
AMBIGUOUS, 2,368 → 164 → 4, four surviving explanations, the model/solver/
engine boundary, and the anchoring benchmark (`C-006` in
[docs/CLAIMS.md](docs/CLAIMS.md)). It was chosen for that reason. Only
portfolio-wide counts diverge.

| | |
|---|---|
| **1. See it** | `./run-demo` — opens the investigation at `/`, the instrument at `/app`. Every figure on both is read from the running engine at load. |
| **2. Architecture** | [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) · [docs/ARCHITECTURE-DIAGRAM.md](docs/ARCHITECTURE-DIAGRAM.md) |
| **3. Measurement** | [docs/EVALUATION.md](docs/EVALUATION.md) · `benchmark/baselines.json` — four methods over 500 held-out settlements, and `exact_only` beats us on precision |
| **4. Razorpay boundary** | [docs/RAZORPAY-INTEGRATION.md](docs/RAZORPAY-INTEGRATION.md) — read-only adapter, no live account contacted, and the engine's 21 modules contain no reference to the provider |
| **5. What we refuse to claim** | [docs/CLAIMS.md](docs/CLAIMS.md) · [docs/FAILURE-STORY.md](docs/FAILURE-STORY.md) |

Fifteen documents in `docs/`. The working record — phase audits, design
explorations, reversed decisions — is in [docs/archive/](docs/archive/) and is
not part of the reading path.

### The problem

Reconciliation systems are measured on how many cases they resolve, so they are
built to resolve more. But a **wrong** financial explanation is worse than no
explanation: candidate order sets discharge receivables against different
customers, so posting the wrong one moves money against the wrong account while
the books still balance.

Measured on this repository's benchmark, over 500 settlements:

```
                decided   wrong    false-proof rate
exact_only         22       0            0.0%     safe, and nearly useless
ATTEST             84       4            4.8%
greedy            462     439           95.0%     useful, and catastrophic
```

`exact_only` beats ATTEST on precision and we say so. The claim is not *most
accurate*. It decides **84 settlements against `exact_only`'s 22**, at a
false-proof rate one twentieth of `greedy`'s — **and it says which of its
answers it could not establish.**

### The insight

AI should investigate. Deterministic systems should prove. Policy should control
action.

### One case

```
₹1,00,036.83     a bank credit
164 candidates    after the reductions, two of which are conventions
4 explanations   satisfy the amount exactly

₹97,759.84       settled whichever one is right
₹7,292.03        turns on which one is, across 12 orders
```

The model proposed an anchor — three orders captured together on the densest day
in the window. The solver found it in **all four** explanations, so it separates
nothing. The engine abstained.

```
AMBIGUOUS  →  UNPRICED  →  REVIEW  →  LEDGER UNCHANGED
```

An AI system could have picked one of those four. ATTEST refuses to.

---

ATTEST treats settlement reconciliation as a **constrained proof problem**, not
as fuzzy matching. A bank credit is the net of some subset of the orders a
merchant captured — after per-transaction fees, GST on those fees, refunds, and
the T+2 settlement calendar. Finding that subset is subset-sum: NP-complete.

> A merchant's bank statement shows one credit: **₹47,382.19**. It is the net of
> some subset of the 400 orders they captured that week — minus per-transaction
> fees, minus GST on those fees, offset by a refund, shifted T+2 by the
> settlement calendar.
>
> **Which orders?**

This is resolved by hand, in Excel, daily, at effectively every merchant in India.

---

## The engine does not emit a confidence score

`97%` is not interpretable. It does not say what would have to be true for the
answer to be wrong, it cannot be audited, and it invites a threshold — and a
threshold invites posting an entry nobody can defend.

Instead every settlement receives a **decidable property of the constraint
system**:

| | |
|---|---|
| 🟢 **PROVEN** | exactly one assignment satisfies every constraint |
| 🟡 **AMBIGUOUS** | two or more do — the engine reports them and stops |
| 🔴 **CONTRADICTED** | none does — the engine reports which constraints conflict |

These are **counted, not estimated**. The solver saturates its subset counter at
two, because the question is never *how many* explanations exist, only whether
the explanation is *unique*. Two bits per reachable sum decides the verdict.

### The trusted kernel

The prover is large: blocking, a counting DP over the amount axis, constraint
propagation, model-proposed hypotheses. The verifier is **28 lines**
(`attest/verdict.py::check`), depends on none of it, and recomputes every value
from source records rather than trusting a single field on the proof.

A proof is accepted only if the kernel accepts it.

> A bug anywhere in the prover can cost recall. It cannot post a wrong entry.

## What this does not claim

Stated here rather than in an appendix, because a system that reports only what
it wins has not been evaluated.

- **No live Razorpay account has ever been contacted.** `fetch` performs a real
  authenticated request and has never been called with real credentials. The
  product says so itself, on the Trust lens, unprompted.
- **The bank statement is simulated.** Every synthetic credit matches its
  settlement by construction, so the adapter cannot exercise the one case the
  engine exists for — a credit that corresponds to no single settlement.
- **`exact_only` is more precise than ATTEST**: 0.0% false proofs against 4.8%.
  It achieves that by answering 22 settlements of 500 and declining 478.
  Published in the product as claim C-004.
- **The numbers describe generated data.** That is what makes a false-proof rate
  knowable at all — the generator holds ground truth — and it is a population
  ATTEST created.
- **Coverage is 16%, not 90%.** Most settlements are correctly refused rather
  than resolved.

`docs/RAZORPAY-DEMO.md` separates IMPLEMENTED from SIMULATED from NOT VERIFIED,
capability by capability.

Same reason a proof assistant separates its kernel from its tactics.

---

## Measured

Ground truth is exact by construction: orders are generated first, and
settlements derived *from* them. Fifteen hazard families
(`attest/generate/taxonomy.py`) are frozen — written before the matcher, so the
benchmark cannot be tuned to flatter the engine.

<!-- generated: results -->
```
2 held-out seeds × 250 settlements
calibrated on [20260821, 314159, 271828], evaluated on [555001, 999983]

RESOLUTION
  exact set recovery           16.0%   complete truth recovered
  coverage                     16.8%   resolved outright
  ambiguity rate               82.4%   correctly refused

SAFETY
  proof precision              0.952   right when it claims sure
  false proof rate             0.80%   ← the number that moves money

ACCOUNTED FOR
  settled (undisputed)     ₹67,66,131.23   agreed by every explanation
  disputed                 ₹75,73,097.75
  accounted for                66.7%   of all processed value

MONEY
  processed              ₹1,02,04,411.89
  auto-posted                 ₹40,464.20
  protected              ₹1,01,63,947.69   refused, deliberately
  wrongly auto-posted              ₹0.00

NORTH STAR
  safe resolution rate          2.2%   resolved without a human
```
<!-- /generated -->

Every figure is read from [`benchmark/results.json`](benchmark/results.json),
regenerated by `python -m attest.eval.benchmark`. Nothing about this engine is
quoted from a second place — "precision 1.000" survived six days past the
measurement that refuted it because a number had been typed into a README and
never re-derived.

### Read `accounted for`, not `exact set recovery`

16.0% complete recovery reads like an engine that fails five times out of
six. That reading is wrong, and `accounted for` is why.

Most abstentions are not *"we do not know"*. When several explanations survive,
the orders appearing in **every** one of them belong to that settlement whichever
explanation is right — so the engine can state that part as settled and name the
exact remainder that is in dispute. Across the panel, **47% of ambiguous value
turns out not to be in dispute at all.**

A real case: a ₹1,00,036.83 settlement with four surviving explanations. Twenty-seven
orders worth ₹97,759.84 appear in all four. Only ₹7,292.03 across twelve orders is
contested — and the next step is not "investigate", it is *"a reference on any one
of those twelve settles the rest."*

**One number cannot describe this engine.** 16.0% exact recovery and
0.952 proof precision measure different things: the first is how often the
complete truth is recovered, the second how often the engine is right *when it
claims to be sure*. Blending them into "95.2% accurate reconciliation"
would be selling the second while doing the work of the first.

**A decline is a correct outcome.** The engine is built to refuse rather than
guess, so `declined` is a feature and `WRONG` is the only real failure.

### Against reference matchers, same data, same pools

<!-- generated: baselines -->
```
  matcher      coverage   decided   wrong   false proof       pair prec
------------------------------------------------------------------
  attest          16.0%        84       4          4.8%        95.9%
  exact_only       4.4%        22       0          0.0%       100.0%
  fuzzy            3.6%        30      12         40.0%        60.0%
  greedy           4.6%       462     439         95.0%        16.5%

  500 settlements over seeds [555001, 999983], identical datasets and identical scoring
```
<!-- /generated -->

`exact-only` is more precise than ATTEST and answers a quarter as often.
Precision alone is trivially winnable by declining, which is why coverage sits
beside it. Greedy answers almost everything and is wrong almost every time —
that is what a matcher with no way to abstain does.

**Read the WRONG column.** `greedy` declines 5% of the time and is wrong 90% of
the time — 226 of 250 settlements posted against orders that did not produce
them. That is what a matcher with no way to abstain actually does. `fuzzy`, the
industry default, scores *below* doing nothing clever and buys it with 11 false
proofs.

Greedy fails structurally, not by tuning: taking the largest order that fits is a
local decision, and subset-sum has no greedy-choice property. One early take
consumes an order a correct explanation needed and there is no way back.

Full methodology in [eval/BASELINES.md](attest/eval/BASELINES.md).

### A feature that was measured and then disabled

Cross-settlement constraint propagation (`attest/evidence.py`) works — an order
belongs to exactly one settlement, so settlements are evidence about each other.
It is off by default:

```
                  exact     WRONG    precision      (seed 20260821)
off               20.8%      0.0%      1.000
on                24.0%      3.6%      0.829
```

Three points of exact-set match, bought by going from **zero** false proofs to
nine. One bad seed amplifies across the population, because propagation is only
as sound as what it propagates from. A change that raises exact-set match by
three points is not an improvement if it raises false proofs by the same amount.
See [FAILURES.md](FAILURES.md), D4.

---

## Run

```bash
python3.13 -m venv .venv && ./.venv/bin/pip install -e .

./run-demo                              # the demo: engine + UI on :8420
./.venv/bin/python -m attest.web        # the same server, without the wrapper
#   http://127.0.0.1:8420/              the investigation — the front door
#   http://127.0.0.1:8420/app           the instrument workspace
./.venv/bin/python -m attest.eval.adversarial   # 34 attacks, source to ledger
./.venv/bin/python -m attest 250 --sweep   # the five-seed panel — report THIS
./.venv/bin/python -m attest 250        # a single seed
./.venv/bin/python -m attest 250 --html # emit report.html
ATTEST_PROP=1 ./.venv/bin/python -m attest 250   # reproduce the D4 ablation
```

The UI runs a generated portfolio or takes your own `orders.csv` and
`settlements.csv`. Stdlib only — no framework, no build step, and nothing leaves
the machine. It leads with rupees rather than row counts, because the question a
merchant has is never "what is your exact-set match rate", it is **how much of my
money is accounted for, and what happened to the rest.**

Navigation is four verbs, and depth lives inside a mode rather than beside it:

```
SUBJECT  ×  LENS  ×  CONTEXT

CONTROL      Where did the money stop?       JOURNAL      What entered the books?
EVIDENCE     Can the explanation be proved?  ACTIVITY     What actually happened?
INVESTIGATE  What would separate them?       TRUST        What can I believe?
POLICY       What is safe to automate?
```

A **subject** is what you are looking at — the portfolio, or one settlement. A
**lens** is the question you are asking about it. A **context** is something
inspected *inside* that state without leaving it. All three live in the URL, so
every view is addressable and Back means what it says.

The case rail carries the subject through every lens: amount, verdict, where it
stopped, what is agreed against what is disputed, and what to do next. Changing
lens does not change the case, and opening a context moves neither.

CONTROL opens on the work, ranked by what each item **unlocks** rather than by
what is stuck — in the native-kernel run, 197 ambiguous settlements are one
action, not 197, because they are ambiguous for the same missing field. Each row states where it is blocked,
why, what would unblock it, and whether ATTEST can do that itself. Three of them
say it cannot.

The state spine runs down the rail on every lens — `SOURCE → MATCHING →
VERIFICATION → POLICY → ACTION` — drawn as the proportion that survives each
stage, so the collapse is legible before any number is read. Clicking a stage
opens the instrument that owns it.

Four screens demonstrate rather than assert. **Activity** sends webhook
deliveries through the same verify/de-duplicate/scope path the HTTP endpoint
uses and reports what came back. **Policy** runs the permission pipeline against
the current run, so a refused capability is something the code did. **Trust**
reads the same benchmark files the build reads, so it cannot report a pass CI
would fail. **Investigate** runs the hypothesis loop, discards its verdict, and
shows the measurement that disabled it — read from `benchmark/anchoring.json`
rather than transcribed.

`⌘K` reaches any lens and any settlement in the attention queue.

See `docs/archive/UX-AUDIT.md` for what the audit found and the defects that reading the
screens turned up.

Optional: build the Rust kernel for the wider envelope and the 52× DP.

```bash
cd native && maturin develop --release
```

## Layout

```
attest/model.py        fee model, tolerance derivation, records
attest/verdict.py      PROVEN/AMBIGUOUS/CONTRADICTED + the 28-line kernel
attest/blocking.py     calendar-inverted candidate generation, escalating
attest/subsetsum.py    counting DP over the amount axis
attest/evidence.py     cross-settlement propagation (off by default)
attest/generate/       hazard taxonomy + generator — FROZEN
attest/policy.py       Wilson-priced risk, the auto-post inequality
attest/ledger.py       the journal entry a proof implies, balanced to the paisa
attest/actions.py      the work ranked by value unlocked per step
attest/eval/          harness, baselines, ablations, regression gates
attest/rules.py        content-hashed rule set + run provenance
attest/agents.py       capabilities, and the four granted to nothing
attest/whatchanged.py  run-to-run diff with computed attribution (CLI)
attest/webhooks.py     raw-byte HMAC, idempotency on id AND payload hash
attest/api.py          the JSON API behind the Case Desk
attest/adapters/       source adapters; money.py reads amounts exactly or refuses
attest/ui/             the Case Desk — one subject, seven lenses, three axes
eval/cpsat_study.py    the CP-SAT measurement that rejected set packing
native/                Rust port of the DP hot path
```

## The kernel

The DP is three ALU ops per cell and re-reads an array the width of the credit
once per order. It is bandwidth-bound, not compute-bound, so the only
optimisation that matters is **making the array smaller**.

Two bits is the floor — the verdict only distinguishes none / one / more than
one. Rather than interleaving 2-bit lanes, which forces lane-masking on every
shift, the counter is split into two **bitplanes** of one bit per sum: `one[s]`
and `many[s]`, mutually exclusive, so together they encode 0/1/2 exactly and each
shifts with a plain bit-shift. The saturating add becomes six bitwise operations
over 64 sums at a time:

```
both  = (one | many) & (s_one | s_many)     // both sides non-zero ⇒ ≥ 2
many' = many | s_many | both
one'  = (one | s_one) & !both
```

```
credit        numpy      native    speedup
₹20,000      275.6 ms   17.11 ms     16.1×
₹80,000    1,342.8 ms   25.46 ms     52.7×

DP footprint at ₹200,000:  4.8 MB   (one byte per sum would be 19.5 MB)
```

The speedup widens with credit size, which is what a bandwidth-bound kernel
should do. **Verified byte-identical to the numpy reference over 1,777 instances
and 1.32 × 10¹¹ DP cells, across all fifteen hazard families** — `tobytes()`
compared, not `array_equal`, because `solve` sums a slice of this array and a
dtype difference would change the sum.

This is not a benchmark flourish. The Python reference could only afford a
₹30,000 envelope, which silently skipped **14.8% of the portfolio** — including
*every* large bundle — before a single subset was examined. The port is what made
those settlements reachable at all. Without the extension the engine falls back
to numpy and a narrower envelope, and still runs correctly.

## Documents

- **[PRD.md](PRD.md)** — the problem, the algorithm, the tolerance derivation, the plan
- **[FAILURES.md](FAILURES.md)** — what broke, daily. Four entries and counting
- **[AGENTS.md](AGENTS.md)** — the working agreement, enforced by `.githooks/pre-commit`
- **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** — layers, the trusted kernel, search-space integrity
- **[docs/ALGORITHMS.md](docs/ALGORITHMS.md)** — the tolerance derivation, the counting DP, why greedy and Hungarian both fail
- **[docs/EVALUATION.md](docs/EVALUATION.md)** — ground truth, the metric vocabulary, baselines, the seed panel
- **[docs/DECISIONS.md](docs/DECISIONS.md)** — fifteen ADRs, including the five that rejected work already built
- **[native/BENCH.md](native/BENCH.md)** — parity methodology and benchmarks

**Evidence and boundaries**

- **[docs/ARCHITECTURE-DIAGRAM.md](docs/ARCHITECTURE-DIAGRAM.md)** — the one diagram: source → ledger, with the model outside the decision path
- **[docs/EVALUATION-PANEL.md](docs/EVALUATION-PANEL.md)** — ATTEST against three baselines, including the one that beats it
- **[docs/FAILURE-STORY.md](docs/FAILURE-STORY.md)** — five failures that changed the system, with reproductions
- **[docs/FAILURE-REGRESSION-MAP.md](docs/FAILURE-REGRESSION-MAP.md)** — every failure mapped to the test that would catch it returning, machine-checked
- **[docs/RAZORPAY-INTEGRATION.md](docs/RAZORPAY-INTEGRATION.md)** — capability matrix with an evidence column, and the frozen boundaries
- **[docs/RAZORPAY-DEMO.md](docs/RAZORPAY-DEMO.md)** — IMPLEMENTED / SIMULATED / NOT VERIFIED, capability by capability
- **[docs/GOLDEN-DATASET.md](docs/GOLDEN-DATASET.md)** — the canonical dataset and the eleven states it produces
- **[docs/archive/WINNING-SUBMISSION.md](docs/archive/WINNING-SUBMISSION.md)** — fifteen questions a reviewer would ask, answered from artifacts
- **[docs/ADVERSARIAL.md](docs/ADVERSARIAL.md)** — 34 attacks from source to ledger, and the defect they found
- **[docs/REPRODUCE.md](docs/REPRODUCE.md)** — clone to running, with the three things that did not work
- **[docs/MONEY-MODEL.md](docs/MONEY-MODEL.md)** — integer paise, tolerance, rounding direction
