# ATTEST — talk tracks

Three lengths. Each answers the same eight things: **problem, insight, system,
AI role, proof, abstention, business value, Razorpay boundary.**

The test for all three: can the judge repeat this afterwards?

> *"ATTEST lets AI investigate financial reconciliation, but deterministic
> evidence decides whether money is allowed to move."*

---

## 60 seconds

> **[landing]** Financial reconciliation that refuses to invent certainty.
>
> Fifty-three lakh entered. Three hundred and fifty-three rupees came out.
> Everything else stopped at verification — and the biggest single reason is
> ₹47,96,811.78 across 197 settlements, all waiting on the same missing field.
>
> **[open the case — 2 clicks]** Here's one. A hundred thousand rupees.
> Four different sets of orders explain it exactly. Ninety-seven thousand is
> settled whichever is right; seven thousand turns on which one is.
>
> **[Investigate — 1 click]** The model proposed an anchor — three orders
> captured on the densest day. The solver tested it, found it in all four
> explanations, so it separates nothing. The engine abstained. Verdict
> unchanged, no financial action.
>
> An AI could have picked one of those four. We measured letting it: worse than
> a coin flip. So it proposes, and a deterministic solver decides.
>
> **[Trust — 1 click]** And this runs on generated data. The Razorpay adapter is
> implemented and tested at its boundary, but no live account has been
> contacted — so the product says NOT VERIFIED rather than pretending.

**5 clicks.**

---

## 3 minutes

**0:00 · the problem** — *[landing]*

> Reconciliation systems are measured on how many cases they close, so they're
> built to close more. But a wrong explanation is worse than none: different
> order sets discharge receivables against different customers, so posting the
> wrong one moves money against the wrong account and the books still balance.

**0:20 · the collapse**

> Fifty-three lakh in. Three hundred and fifty-three rupees posted. Watch the
> bars, not the numbers — full at source, a stub at verification. That's
> ₹48,03,127.81 held, and it's held for a reason we can name.

**0:40 · the work**

> ₹47,96,811.78, systemic, 197 settlements. Not 197 problems — one missing
> field, 197 times. And notice there's no button: ATTEST can't supply that
> field, so it doesn't offer to. It says REQUIRES EXTERNAL EVIDENCE.

**1:00 · one case** — *[2 clicks]*

> A hundred thousand rupees. Four explanations satisfy the amount exactly.
> ₹25,330.46 settled either way, ₹5,603.30 in dispute across 11 orders.

**1:20 · the search space** — *[Evidence]*

> This is the part that matters. 2,368 orders in the book, 73 that could belong
> to this credit, four explanations surviving. And two of the three cuts that
> got us from 2,368 to 73 are **conventions**, not facts. A proof can be
> arithmetically perfect inside a space that already excluded the truth — so we
> record the space and label every reduction.

**1:50 · the core moment** — *[Investigate]*

> An AI system can produce a plausible explanation here. The problem is that
> four are plausible. So ATTEST never asks the model to choose — the solver
> already found the ambiguity. It asks the model for evidence that would
> **separate** them, then tests that evidence deterministically.
>
> The model proposed a capture-batch anchor. The solver found it in all four
> explanations. Non-discriminative. The engine abstained.
>
> **Verdict unchanged. No financial action.**
>
> And we measured the alternative. Letting the model select among valid
> explanations scores worse than a coin flip, so that path is switched off — the
> loop still runs, and its verdict is thrown away.

**2:20 · the consequence** — *[Policy, Journal]*

> Policy won't price what wasn't proved. No confidence score — UNPRICED, review.
> Debit zero, credit zero, ledger unchanged. Nothing happened, and that's an
> accounting result, not an empty screen.

**2:40 · the boundary** — *[Trust]*

> This runs on generated data — it says GENERATED on every screen, read from the
> adapter. The Razorpay adapter is implemented and tested at its boundary:
> signature verification fails closed, identity, idempotency, malformed
> rejection, integer paise with the unit declared. Live-account validation has
> not been performed, so ATTEST says NOT VERIFIED rather than pretending
> otherwise. Eleven boundaries listed, twenty-four recorded failures, three
> features built and then switched off.

**2:55 · close**

> ATTEST lets AI investigate reconciliation. Deterministic evidence decides
> whether money is allowed to move.

---

## 5 minutes

Everything above, plus four expansions.

**After the collapse (0:40)** — the benchmark, spoken as a concession:

> Three ways to do this over 500 settlements. Exact matching: 22 decided, zero
> wrong. Perfectly safe, and it declines 478. A greedy matcher: 462 decided, 439
> wrong — a 95% false-proof rate, because deciding more and being right are
> different objectives. ATTEST: 84 decided, 4 wrong.
>
> Exact-only beats us on precision and we say so in the README. Our claim is
> eighty-four decided against exact-only's twenty-two, at a twentieth of
> greedy's error rate, and knowing which answers we couldn't establish.

**After the search space (1:50)** — what stops a forged proof:

> A proof carries the space it was established in, and its order ids must be a
> subset of that space's recorded members — it cannot cite an order the search
> never saw. A finding with no recorded space isn't postable. It used to be, and
> it was postable *precisely because* it omitted the evidence it would have been
> judged on. That's CORE-001, and it's in the failure log.

**After the core moment (2:20)** — the other failure mode, 2 clicks:

> Ambiguous means too many answers. Here's the opposite — ₹6,316.03, and no
> combination of any window reaches it. ₹447.05 unresolved. Not "review this",
> but "look for a fee correction of ₹447.05 around this value date." That's a
> work item.

**Before the close** — what building it changed:

> Three things we found and kept. A proof was postable when its search space was
> missing. An anchor that looked useful fell below a coin flip once we forced it
> to only select among explanations arithmetic had already validated — so the
> feature is disabled and the screen says the verdict was discarded. And our own
> adversarial harness was scoring its crashes as successful defences, four of
> twenty-nine, which we found before reporting the number.

---

## What not to say

- Not *"production-ready"*. It isn't, and `RAZORPAY-INTEGRATION.md` says so.
- Not *"we tested against a live Razorpay account"*. No account has been
  contacted.
- Not *"most accurate"*. `exact_only` is more precise and we publish that.
- Not *"our AI reconciles payments"*. The AI proposes; the solver decides.
- Don't apologise for `NOT VERIFIED`. It is the most credible thing on screen.
