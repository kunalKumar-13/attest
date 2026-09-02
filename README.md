# ATTEST

### AI can decide. Your ledger can't guess.

**ATTEST is a financial control layer that verifies AI-proposed actions before
they can change financial state.** Settlement reconciliation is the first
workflow it does that for.

![ATTEST financial control — the native kernel reconciling 250 settlements on
held-out seed 555001: 39 proven and eligible to automate, 210 ambiguous and
held, 1 contradicted.](docs/img/product-control.png)

<sub>The live demo on **held-out evaluation seed 555001**, on the **native
kernel** — one of the two execution paths, both stated below.</sub>

---

## The problem

A payment gateway does not pay a merchant order by order. It sends one lump sum
covering many orders at once, minus its fees, and somebody has to establish what
that credit was composed of.

Where the records carry an order-level reference, that reconstruction is a join
and it is easy. The hard case is the one where they do not — a bank credit
reconciled against a statement rather than a gateway report, a period whose
recon is unavailable, an adjustment with no linked entity. There, composition
has to be *derived* from amounts, fees and dates, and **more than one set of
orders can add up to the same credit exactly**.

Those sets discharge different customers. Picking one is a guess, and a guess
marks the wrong customer as paid while the books still balance — so nobody finds
out until it is expensive. The alternative today is a person in a spreadsheet.

## How ATTEST works

```
ADVISOR    proposes investigative signals — which records to look at
VERIFIER   independently reconstructs and proves the explanation
POLICY     decides whether a proven result is safe to automate
LEDGER     records only permitted execution
```

**The advisor is advisory only. It cannot authorize financial action.** It is
given identifiers, names and dates and never an amount; the verifier recomputes
the explanation from the source records without reading what the advisor said;
and the ledger accepts nothing the verifier has not re-derived.

## The two outcomes

Both are settlements in the held-out evaluation seed. Every figure is read from
the run, and both are pinned by a test so the data cannot move underneath them.

| | `setl_000233` | `setl_000225` |
|---|---|---|
| **event** | ₹6,523.53 | ₹23,922.07 |
| **advisor** | proposed a capture batch | proposed a capture batch |
| **verifier** | 2,328 → 4 → **1** · PROVEN, residual ₹0.00 | 2,328 → 23 → **4** · AMBIGUOUS, four valid explanations |
| **policy** | expected loss ₹247.82 < ₹250 review cost | not eligible at any price |
| **ledger** | **AUTO-POST** — balanced entry written | **HOLD** — no financial action |

On the second, the advisor's proposal sits inside exactly one of the four
explanations, so a system that listened to it would post ₹23,922.07 today.
Across the held-out panel that advisor is right 27 times in 63. A 43% opinion is
not evidence, so ₹12,630.27 is reported as settled whichever explanation is
right, ₹30,107.39 is held, and the operator is handed the one field that ends
the argument.

## Measured results

Held-out evaluation. Calibration and evaluation seeds are disjoint by
construction, and every figure below is regenerated from
[`benchmark/results.json`](benchmark/results.json) rather than typed.

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
  accounted for                68.8%   of all processed value

MONEY
  processed              ₹1,02,04,411.89
  auto-posted               ₹2,52,431.44
  protected                ₹99,51,980.45   refused, deliberately
  wrongly auto-posted              ₹0.00

NORTH STAR
  safe resolution rate          6.6%   resolved without a human
```
<!-- /generated -->

**A false proof and a wrongly posted entry are different things, and the gap
between them is the product.** Over 500 held-out settlements the engine offered
84 proofs and 4 of them were wrong. None of those 4 was posted: the policy
priced them into REVIEW or BLOCK, so of the 33 settlements that auto-posted,
**33 were exact and ₹0.00 moved against the wrong account.**

Against three reference matchers on identical data — including one that is more
precise than ATTEST, which is said here rather than omitted:

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

Full methodology, metric definitions and the seed panel:
**[docs/EVALUATION.md](docs/EVALUATION.md)**.

## Why this is safe

- **Exact money.** Integer paise end to end. No float touches an amount, so the
  rounding tolerance is a derived bound rather than a guess.
- **Independent verification.** A 35-line checker re-derives every proof from
  the source records and shares no code with the search that produced it. A bug
  in the search can cost recall; it cannot post a wrong entry.
- **A policy gate, not a threshold.** Automation happens where the *measured*
  error rate for that class of result, priced at its 95% upper bound, costs less
  than a human check. Change what a review is worth and the boundary moves on
  its own.
- **The ledger cannot bypass verification.** It calls the checker itself rather
  than trusting that someone upstream did — see
  [reports/](reports/), which documents two defects where that was not yet true.
- **Adversarial testing.** 35 attacks from source to ledger run on every build.
- **Held out.** The policy is calibrated on seeds it is not evaluated on.

## The AI boundary

**AI proposes. ATTEST proves. Policy permits. Ledger records.**

There is no language model in this repository, and the product says so on every
screen — every run stamps `model_version = none`. The advisory layer is a
**deterministic capture-batch ranking heuristic**: it reads the records a person
would read and points at the orders it believes belong together.

It was measured before it was trusted. Over 1,250 candidate pools it offered an
answer on 63 and was right on 27 — **below a coin flip** — so it is disabled as
a *resolver* and retained as an *advisor*. It still runs on every case, because
a boundary nobody can inspect is a claim rather than an architecture.

A language model implements the same interface and nothing downstream changes,
because nothing downstream trusts it. That is the point of the boundary: the
advisor is allowed to be wrong, cheaply, somewhere being wrong costs a wasted
search rather than a customer's balance.

## Architecture

**[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** — the layers, the trusted
kernel, and search-space integrity.
**[docs/ARCHITECTURE-DIAGRAM.md](docs/ARCHITECTURE-DIAGRAM.md)** — source to
ledger in one diagram, with the advisor outside the decision path.

## Run locally

### Reproduce the demo

```bash
git clone https://github.com/kunalKumar-13/attest && cd attest
python3.13 -m venv .venv && ./.venv/bin/pip install -e .
cd native && maturin develop --release && cd ..   # optional kernel — see below
./run-demo                                        # UI on http://127.0.0.1:8420
```

**Two execution paths, and the recorded demo uses the first.**

| | solver envelope | this run of 250 |
|---|---|---|
| **Native kernel** — the recorded demo | ₹2,00,000 | 39 proven · 210 ambiguous · 1 contradicted |
| **Portable** — no Rust toolchain needed | ₹30,000 | 38 proven · 170 ambiguous · 1 contradicted · **41 insufficient** |

The 41 are not failures. They are settlements whose candidate space exceeds what
the portable solver will attempt, so it reports INSUFFICIENT rather than
searching a space it cannot finish — the same refusal this whole document is
about, applied to compute instead of evidence. `./run-demo` prints which path is
active **before** any portfolio figure, so the two can never be confused.

**The canonical cases are identical on both.** `setl_000233` and `setl_000225`
behave the same either way; only portfolio-wide counts diverge.

Tests and evidence:

```bash
./.venv/bin/pip install -q pytest ortools playwright
./.venv/bin/python -m playwright install chromium

./.venv/bin/python -m pytest tests/ -q          # 385 tests
./.venv/bin/python -m attest.eval.adversarial   # 35 attacks, source to ledger
./.venv/bin/python -m attest.eval.gate 250      # the safety gates
./.venv/bin/python -m attest.eval.benchmark 250 # regenerate benchmark/results.json
```

Clone-to-running, including the three things that did not work the first time:
**[docs/REPRODUCE.md](docs/REPRODUCE.md)**.

## Repository map

```
attest/       the engine, the adapters, the API and the UI
tests/        385 contracts and regression tests
docs/         architecture, evaluation, decisions, failure reports
benchmark/    the artifacts every published figure is read from
reports/      numbered defect reports for the money-deciding core
ci/           what the build defends, runnable locally
native/       the Rust port of the DP hot path
```

**[docs/](docs/)** indexes everything below, in the order a reviewer would
want it.

- **[FAILURES.md](FAILURES.md)** — twenty-four dated failures, what each one
  cost, and what changed because of it.
- **[docs/DECISIONS.md](docs/DECISIONS.md)** — fifteen ADRs, including five that
  rejected work already built.
- **[docs/CLAIMS.md](docs/CLAIMS.md)** — every externally visible number, the
  artifact it is read from, and the command that regenerates it.
- **[docs/QUESTIONS.md](docs/QUESTIONS.md)** — questions a reviewer would ask,
  answered from artifacts.

## Limitations

Stated here rather than in an appendix, because a system that reports only what
it wins has not been evaluated.

- **The evaluation data is synthetic.** That is what makes a false-proof rate
  knowable at all — the generator holds ground truth — and it is a population
  ATTEST created. The hazard taxonomy was frozen before the matcher was written.
- **No live merchant money.** The Razorpay adapter is read-only, has no write
  scope, and has never been called with real credentials.
  [docs/RAZORPAY-DEMO.md](docs/RAZORPAY-DEMO.md) separates IMPLEMENTED from
  SIMULATED from NOT VERIFIED, capability by capability.
- **Ambiguity rises with candidate density.** More settlements over the same
  window means larger candidate pools, so more subsets land within tolerance and
  more settlements are correctly refused. Coverage roughly a third at 1,200
  settlements of what it is at 250 — a denser portfolio is a harder question,
  not a worse engine. Measured at three densities in
  [docs/EVALUATION.md](docs/EVALUATION.md).
- **The advisory layer is non-authoritative and weak.** Measured at 0.429
  precision and disabled as a resolver. It is not a language model and is not
  described as one.
- **Coverage is 16%, not 90%.** Most settlements are correctly refused rather
  than resolved. A decline is a correct outcome here; a wrong posting is the
  only real failure.

---

<sub>Built for the Razorpay AI Buildathon, Track 04. Working agreement and the
protected-core rule: [AGENTS.md](AGENTS.md). Product requirements and the
tolerance derivation: [PRD.md](PRD.md).</sub>
