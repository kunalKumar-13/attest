# The five-minute pitch — spoken script

Every figure below is on screen when it is spoken. Nothing is read from memory.
Verified against the running product on seed `20260821`, run of 250,
**on the native kernel** — which is the path the recording uses. Confirm
`run-demo` prints `ATTEST · GENERATED · NATIVE KERNEL` before you start.

**One precision rule for the whole script:** ₹47,96,811.78 belongs to the **197
ambiguous** settlements. **198** are held at verification — the extra one is the
single contradicted case, a separate blocker whose figure appears only in the
workspace and is therefore never spoken. Never say "198" while ₹47,96,811.78 is
on screen.

Word count ≈ 720, which is five minutes at a measured pace. Do not rush the
two pauses; they are marked.

---

## 0:00 — 0:15 · Hook

> A reconciliation system's output is not an answer. It is a claim about
> whether the evidence supports acting.
>
> This is ATTEST. Fifty-three lakh rupees, two hundred and fifty settlements,
> one finance-ops loop — synthetic data, by design, because known ground truth
> is the only way to measure how often a system is confidently wrong.

*On screen: the run manifest. ₹53,02,701.96 · 250 · 2,368 · seed 20260821.*

## 0:15 — 0:40 · The loop

> A settlement credit has to be explained by the orders it discharges, net of
> fees and tax. The settlement report does not carry an order-level reference,
> so the explanation has to be reconstructed — and often more than one
> reconstruction fits exactly.
>
> In the native-kernel run, these two hundred and fifty separate into fifty-two
> proved, one hundred and ninety-seven ambiguous, and one contradicted. A
> twenty-point-eight percent match rate, and a hundred and ninety-eight
> exceptions it could not resolve.
>
> The repository also has a portable path with a smaller solver envelope; the
> portfolio counts differ there, and the case we are about to open is identical
> on both.

*Scroll to the population field. Every point is one settlement.*

## 0:40 — 1:05 · The credibility test

> Before anything else — the measurement. This is a held-out panel: five
> hundred settlements over two seeds, neither of them the seed the live run
> uses.
>
> ATTEST decides eighty-four of five hundred at a four-point-eight percent
> false-proof rate. Exact-only decides twenty-two, at zero percent. Greedy
> decides four hundred and sixty-two and is wrong four hundred and thirty-nine
> times.
>
> Exact-only is safer than us. It also decides a quarter as much. We are not
> optimising for the most decisions — we are optimising for knowing when a
> decision is justified.

*On screen: the benchmark, both populations labelled above it.*

## 1:05 — 1:35 · The real cost

> Forty-seven lakh, ninety-six thousand rupees is blocked across a hundred and
> ninety-seven settlements. Those settlements are not broken. Several disjoint
> sets of orders satisfy each credit exactly, and arithmetic cannot choose
> between them.
>
> One field would release all of them: an order-level reference on the
> settlement report. That is a change at the source — not something this
> software can perform.

*On screen: the exception section, the "would unblock" line.*

## 1:35 — 2:05 · One case

> Inside one settlement. Two thousand three hundred and sixty-eight candidate
> orders in the book. The settlement calendar, the already-claimed set and an
> amount ceiling cut that to a hundred and sixty-four. Then arithmetic: every
> subset whose net equals the credit within tolerance.
>
> Four survive.

*Pause one beat.*

> No unique explanation means no financial action.

## 2:05 — 2:45 · The AI question

> So we asked whether a model could break the tie.
>
> It proposes an anchor — here, a capture-batch. A deterministic solver tests
> whether that anchor actually isolates one explanation. On this settlement,
> two tested, zero discriminative.
>
> Then we measured the whole loop. Across the evaluation panel it resolved
> twenty-seven of sixty-three correctly. Forty-two point nine percent. Below a
> coin flip.
>
> We did not hide that number. We did not enlarge the prompt. We did not give
> the model more authority. We built the architecture so its conclusion cannot
> reach the ledger — the engine never reads it.
>
> On this case the model concluded ambiguous and the engine concluded
> ambiguous. They agree, and it does not matter: the verdict is produced
> without reading the model's, so agreement and disagreement are equally
> inconsequential.

*Pause. On screen: NO FINANCIAL ACTION.*

## 2:45 — 3:20 · Engineering, not a prompt

> Four properties hold that up, all measured from the running system.
>
> The proof checker is twenty-eight lines and does not import the solver — the
> solver imports the checker. A bug in the search cannot also be the bug that
> waves its own answer through.
>
> Six of six safety gates pass. Money is integer paise end to end. Thirty-four
> attempts to move money the engine should not move; zero succeeded.

## 3:20 — 3:50 · Razorpay

> The provider boundary sits outside the engine on purpose. Razorpay, then a
> read-only adapter, then normalised records, then the engine.
>
> Twenty-one of twenty-one modules that produce a verdict contain no reference
> to the provider. Swap the adapter and the same verdict is produced.
>
> Today's data is synthetic by design. Live account validation is not claimed
> and the product says so on its own Trust instrument.

## 3:50 — 4:20 · The refusal

> Back to the money. Forty-seven lakh, ninety-six thousand, across a hundred
> and ninety-seven settlements. No financial action. Supply an order-level
> reference.
>
> There is no button here, and that is deliberate. There is nothing honest for
> the software to do next.

## 4:20 — 4:45 · Why this matters

> The interesting problem in reconciliation is not the case where everything
> matches. It is the boundary between evidence that supports posting and
> evidence that merely looks plausible.
>
> That boundary is where financial automation becomes dangerous, because a
> wrong posting discharges a receivable against the wrong customer while the
> books still balance. ATTEST makes that boundary explicit and refuses to cross
> it.

## 4:45 — 5:00 · Close

> Explainable, bounded, gated.
>
> We tried AI. We measured it. It was not reliable enough to decide. So we
> built the system so it cannot.
>
> No financial action — until the evidence supports it.

*Cut on the umber room. No thank-you slide.*
