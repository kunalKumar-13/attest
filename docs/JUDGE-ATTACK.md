# ATTEST — judging rehearsal and evaluator attack

Conducted against the running product, the README and the repository. Nothing is
credited that an evaluator would not discover on their own.

**No code was changed.** Two findings need your approval before anything moves.

---

## Findings, reported not fixed

### F1 · A number in the code contradicts the artifact it cites — **fix before submitting**

`attest/api.py` explains why AI resolution is switched off:

> *"Measured at precision 0.521 over five seeds — a coin flip."*

`benchmark/anchoring.json`, the shipped five-seed artifact (1,250 pools ÷ 250
per seed), records:

```
resolved 63 · correct 27 · wrong 36 · precision 0.4286
```

`FAILURES.md` D8 does record 0.521, from an earlier run of 73 resolved / 38
correct / 35 wrong. The artifact has since been re-measured and moved.

The conclusion is unchanged and in fact **stronger** — 0.43 is worse than a coin
flip, not better — but the cited figure does not match the shipped evidence, and
this project's own standard is that every claim traces to an artifact. The claim
register does not catch it because the number lives in a Python string rather
than a generated README block.

A skeptical evaluator who opens `anchoring.json` finds a mismatch between what
the code says and what the measurement says. That is the one thing this
submission cannot afford. **Recommend correcting the string to read from the
artifact, or restating it as 0.4286.**

### F2 · The strongest evidence for the thesis is not on screen — **your call**

The single best answer to *"why not just let the AI decide?"* is that it was
tried and measured. That measurement is **not discoverable in the product**:

| probe | Investigate | any lens | behind a disclosure |
|---|---|---|---|
| `0.521` / `0.4286` | ✗ | ✗ | ✗ |
| "coin flip" | ✗ | ✗ | ✗ |
| "disabled" | ✗ | Trust only | ✗ |

Investigate says *"the loop ran and its verdict was discarded"* — true, and
good — but never says **why**. Trust says *"3 features built, measured, then
disabled · D4 · D8 · D12"* without the number.

Not submission-blocking: the demo can speak it and the docs carry it. But it is
the highest-value sentence in the project and a judge cannot currently find it.

---

## The sentence you asked me to test

> *"An AI system can produce a plausible explanation here. The problem is that
> four explanations are plausible. ATTEST doesn't ask the model which one feels
> right. It asks a deterministic solver whether the evidence proves one. Here,
> it doesn't — so nothing moves."*

Traced clause by clause against `attest/hypothesis.py` and `attest/api.py`:

| clause | verdict |
|---|---|
| "an AI system can produce a plausible explanation" | ✅ the proposer emits an anchor with reasoning |
| "four explanations are plausible" | ✅ `AMBIGUOUS`, 4 proofs survive |
| "doesn't ask the model which one feels right" | ✅ the model proposes a **constraint**, never a selection |
| **"asks a deterministic solver whether the evidence proves one"** | ⚠️ **out of order** |
| "here it doesn't — so nothing moves" | ✅ and stronger than stated |

**The correction.** The solver had already established that no unique
explanation exists — `investigate()` is only ever entered on `AMBIGUOUS`. The
model is then asked for an *anchor*, and the solver tests whether that anchor is
contained in exactly one of the four. Saying the solver is asked "whether the
evidence proves one" implies the model ran first and the solver checked its
answer. The real order is the opposite, and the real order is the better story.

**Stronger and fully supported:**

> *"An AI system can produce a plausible explanation here. The problem is that
> four are plausible. So ATTEST never asks the model to choose — the solver has
> already found the ambiguity. It asks the model for evidence that would
> **separate** them, then tests that evidence deterministically. Here the anchor
> appears in all four explanations, so it separates nothing. The engine
> abstains, and nothing moves."*

**And the fact that beats it:** in this build the loop's verdict is thrown away
regardless. `api.py` returns the original verdict, `would_have_concluded`
alongside it, and `changed_nothing: True`. The model cannot move money because
its conclusion is not consulted — a measurement, not a promise.

---

## 1 · Why this could win

**It is the only submission whose central claim is a refusal.** Fifty AI
projects will demonstrate what their model can do. This one demonstrates,
on screen, a model producing a reasonable hypothesis that the system then
declines to act on — and shows the arithmetic for why.

**The honesty is structural, not rhetorical.** `NOT VERIFIED` leads the Trust
lens. Eleven boundaries are listed in the product. Three features were built,
measured and switched off. One boundary is ATTEST reporting a discrepancy
against its own documentation. None of this is in an appendix.

**The benchmark concedes.** `exact_only` beats ATTEST on precision and the
README says so in the opening. A submission that names the baseline that beats
it is read as trustworthy on everything else.

**It looks like a financial instrument.** Zero cards, zero gradients, zero
charts. Money in monospace tabular figures with nine consistent roles. The
hierarchy survives grayscale and a 2.2px blur.

**The engineering shows without being listed.** Integer paise end to end, a
28-line kernel sharing no code with the solver, 34 adversarial attacks with
controls, a protected core with a pre-commit guard, a clean-room verification
that found three real defects.

## 2 · Why this could lose

**"Isn't this just subset-sum with a UI?"** — the most dangerous question,
because a judge can arrive at it in thirty seconds and it is half true. The
answer is search-space integrity, and it is currently the *least* legible idea
in the product.

**Abstention can read as failure.** A judge who sees `AMBIGUOUS`, `UNPRICED`,
`LEDGER UNCHANGED` in sequence and does not grasp the thesis concludes the
system did not work. Everything hangs on the framing landing in the first thirty
seconds.

**16% coverage sounds bad out of context.** Without the greedy comparison
alongside it, it reads as a weak result rather than a deliberate one.

**The AI can look decorative.** If the demo shows the model proposing and being
rejected, a judge may ask why the model is there at all. The answer — that the
alternative was measured and is a coin flip — is not currently on screen (F2).

**The data is generated.** Now labelled `GENERATED` on every screen, which is
the right call, but it invites *"so nothing here is real."* The answer is that
the ground truth is what makes a false-proof rate knowable at all.

## 3 · Questions a Razorpay engineer will ask

For each: what the repository actually supports, whether the **product** shows
it, whether the **README** shows it.

| # | question | product | README |
|---|---|---|---|
| 1 | Isn't this just subset-sum with a UI? | partial — Evidence shows the reductions and labels conventions | ✗ |
| 2 | Why do you need AI at all? | partial — the trail is shown, the measurement is not | ✗ |
| 3 | Why should Razorpay care? | ✅ blockers ranked by value unlocked | ✅ |
| 4 | Why not just exact matching? | ✗ | ✅ the three-way table |
| 5 | Your false-proof rate isn't zero — why is this safe? | ✅ policy prices it against review cost | ✅ |
| 6 | `exact_only` has better precision. Why isn't it better? | ✗ | ✅ stated in the opening |
| 7 | You haven't tested a live account — why believe the integration? | ✅ Trust, and `GENERATED` on every screen | ✅ |
| 8 | Why would a finance team use this? | ✅ *would unblock*, per blocker | partial |
| 9 | What happens when the model hallucinates? | ✅ the trail shows a rejected hypothesis | ✗ |
| 10 | Can the model cause money to move? | ✅ `Verdict unchanged`, verdict discarded | ✗ |
| 11 | What exactly constitutes a proof? | ✅ Policy's `WHAT HAD TO HOLD`, 5 conditions | ✅ |
| 12 | What prevents a forged PROVEN? | ✗ — membership check is invisible | ✗ |
| 13 | What if several explanations are valid? | ✅ the entire canonical case | ✅ |
| 14 | What does ₹47.96L blocked mean? | ✅ the blocker row | ✗ |
| 15 | What would unblock it? | ✅ *"supply an order-level reference"* | ✗ |
| 16 | What did you discover that changed the architecture? | partial — Trust lists D4/D8/D12 | ✗ |

**Weakest coverage: #12 (forged proofs) and #2 (why AI at all).** Both are
answered decisively in the code and in neither surface.

## 4 · Exact answers — fifteen seconds each

**"Isn't this just subset-sum with a UI?"**
> Subset-sum finds *a* subset. We count them, and we record the universe we
> counted in. A proof that is arithmetically perfect inside a space that already
> excluded the truth is a false proof — that is D8, and it is why every
> reduction is labelled a convention or a fact. Uniqueness inside a restricted
> space is not uniqueness.

**"Why do you need AI at all?"**
> When four explanations survive, arithmetic is finished. The remaining question
> is what else we know — which orders were captured together, which share a
> customer. Generating those hypotheses is what a model is good at. Deciding
> which is true is what it is bad at, and we measured that: letting it select
> among valid explanations scores worse than a coin flip, so it is switched off
> and the screen says the verdict was discarded.

**"Why should Razorpay care?"**
> Because 197 settlements aren't 197 problems. They're one missing field —
> ₹47,96,811.78 behind a single order-level reference on the settlement report.
> A system that says "manual review" gives you 197 tickets. This one gives you
> one schema change.

**"Why not just exact matching?"**
> We ship exact matching as a baseline and it beats us on precision — zero false
> proofs. It also decides 22 settlements out of 500 and declines 478. Safe and
> nearly useless. We decide 84 at a 4.8% false-proof rate, and we tell you which
> answers we couldn't establish.

**"Your false-proof rate isn't zero. Why is this safe?"**
> Because safety isn't the proof rate, it's what's allowed to post on it. Policy
> compares expected loss against the cost of a human review and only automates
> when automating is cheaper. Money wrongly auto-posted is ₹0 across the panel,
> and that's the gate that may not move.

**"`exact_only` has better precision. Why isn't it better?"**
> It is better, at precision. We don't claim otherwise anywhere. It answers 4%
> of the book. The interesting question isn't who is most precise, it's who is
> most useful at an acceptable, *priced* error rate — and who tells you when
> they don't know.

**"You haven't tested a live Razorpay account."**
> Correct, and the product says so before I do. Trust leads with LIVE RAZORPAY
> VALIDATION — NOT VERIFIED, and every screen says GENERATED, read from the
> adapter rather than written in. The adapter's boundary *is* tested —
> signature verification fails closed, identity, idempotency, malformed
> rejection, integer-paise parsing. Live pagination is marked NOT VERIFIED
> because it has never met a real response.

**"Why would a finance team use this?"**
> Because it answers what to do first in money rather than counts, and it says
> what it cannot do. Three blockers, three labels: requires external evidence,
> requires an engine change, requires a human search. None of them offers a
> button, because none can be resolved by pressing one.

**"What happens when the model hallucinates?"**
> You watch it happen in the demo. The model proposes an anchor that sounds
> convincing — three orders captured on the densest day. The solver finds it in
> all four explanations, so it separates nothing, and the engine abstains. A
> hallucination costs a rejected hypothesis and a line in the trail.

**"Can the model cause money to move?"**
> No, and not by convention. The loop's verdict is computed and thrown away —
> the API returns the engine's original verdict, what the loop *would* have
> concluded, and `changed_nothing: true`. Below that, posting requires a PROVEN
> verdict re-derived by a 28-line kernel that shares no code with the solver,
> over a recorded search space. No engine module imports the model layer.

**"What exactly constitutes a proof?"**
> Five conditions, all visible on the Policy lens. One explanation satisfies the
> amount exactly; the independent kernel re-derives it from source records; the
> search space integrity is recorded and not compromised; expected loss is below
> the review cost; the amount is below the exposure ceiling. On our canonical
> case, zero of five pass.

**"What prevents a forged PROVEN result?"**
> A proof carries the search space it was established in, and its order ids must
> be a subset of that space's recorded members — a proof cannot cite an order
> the search never saw. A finding with no recorded space is *not* postable; it
> used to be, which is CORE-001, and it was postable precisely because it
> omitted the evidence it would have been judged on.

**"What if several explanations are mathematically valid?"**
> That's the case we built the product around. Four survive on ₹1,00,036.83.
> ₹97,759.84 is settled whichever is right; ₹7,292.03 turns on which one is. We
> report both numbers and refuse to pick.

**"What does ₹47.96 lakh blocked actually mean?"**
> Money we could reconcile today if one field existed. It is not stuck for a
> technical reason — 197 settlements are ambiguous for the same missing field,
> so it is one action's worth of value, which is why the work is ranked by what
> it unlocks rather than by amount.

**"What would unblock them?"**
> An order-level reference on the settlement report. The recon report already
> carries `order_id`, `payment_id` and `settlement_id` on the same row — with
> that join, reconciliation is mostly arithmetic and the solver is the fallback
> for where the join fails.

**"What did you discover that changed the architecture?"**
> Three things, all recorded. A proof was postable when its search space was
> absent — it passed *because* it omitted the evidence. An anchor that completes
> an explanation looked good until we forced it to only *select* among
> explanations arithmetic had already validated, and precision fell below a coin
> flip, so the feature is disabled. And the adversarial harness was scoring its
> own crashes as successful defences — four of twenty-nine — which we found
> before reporting the number.
