# Final demo architecture — five minutes

Designed against Track 04's bar: **throughput, measured accuracy, an honest
exception list — and never one cherry-picked match.**

The structural change from every previous script: **the population comes first.**
The single case is evidence *for* a claim already made, not the claim itself.

> **Precondition (P0).** This script assumes the demo reproduces on a clean
> install. It does not today — see `COMPETITIVE-ATTACK.md` §1. Either the
> canonical case moves to one that survives the default install, or the video is
> recorded on the default install with its numbers. **Do not record until that
> is decided.**

---

## Timeline

| at | on screen | the line |
|---|---|---|
| **00:00** | landing, nothing clicked | *"Reconciliation systems are graded on how many cases they close. But a wrong explanation is worse than none — different order sets discharge receivables against different customers."* |
| **00:15** | the spine collapse | *"Fifty-three lakh in, three hundred and fifty-three rupees posted. Everything else stopped at a named stage."* — **throughput** |
| **00:35** | the benchmark table *(README or a held slide)* | *"Three ways to do this over 500 settlements. Exact-only: 22 decided, zero wrong — safe and nearly useless. Greedy: 462 decided, 439 wrong. ATTEST: 84 decided, 4 wrong."* — **measured accuracy** |
| **00:55** | the blocker register | *"Every one of the 250 settlements is on this list with a named reason. Not 197 problems — one missing field, 197 times."* — **honest exception list** |
| **01:20** | one case, 2 clicks | *"Now one of them, so you can see why."* — the anecdote, **after** the population |
| **01:40** | Evidence: 2,368 → 73 → 4 | *"Two of the three cuts that got us here are conventions, not facts. A proof can be perfect inside a space that already excluded the truth."* |
| **02:05** | **the AI boundary** | *"An AI system can suggest a plausible explanation. That is not enough to move money."* |
| **02:20** | MODEL → SOLVER → ENGINE | *"ATTEST asks a deterministic question: does the evidence distinguish one explanation from the others? Here it doesn't. So the model's answer is discarded, the verdict stays ambiguous, and no financial action occurs."* |
| **02:45** | the measurement, in place | *"We measured letting it decide: 27 correct of 63. Below a coin flip. That measurement is why the model has no authority — it investigates, it doesn't decide."* |
| **03:05** | Policy | *"No confidence score. Nothing was proved, so nothing was priced — UNPRICED, review."* |
| **03:20** | Journal | *"Debit zero, credit zero. Ledger unchanged. Nothing happened, and that's an accounting result."* |
| **03:35** | **a runtime failure, handled** | webhook: accepted / duplicate / replay mismatch / bad signature. *"Bad financial input is refused before it reaches reconciliation."* — **Failure Recovery** |
| **04:00** | Activity | *"And every step carries why it happened."* — **audit trail** |
| **04:20** | Trust | *"This runs on generated data — it says so on every screen. The Razorpay adapter is implemented and tested at its boundary; live-account validation has not been performed, so the product says NOT VERIFIED."* |
| **04:40** | architecture, spoken | *"Adapter, engine, proof, policy, ledger. No engine module mentions Razorpay — the engine cannot know which adapter produced its records, which is why the safety properties survive a change of source."* |
| **04:55** | close | *"AI can investigate the money. Only evidence can move it."* |

---

## Rules for the recording

**Never name a lens.** Not *"now let's look at Policy"* — say *"this is what
policy was allowed to do."* The instruments are how; the story is what.

**Every click earns its place.** Nine clicks total. No hunting, no scrolling to
find something, no explaining a control.

**Leave the cold start in.** ~2.6 s of `reconciling…` is real work on 250
settlements. Cutting it would be the one staged thing in the submission.

**Do not apologise at 04:20.** `NOT VERIFIED` is the product proving its own
thesis on itself.

## What moved, and why

| was | now | because |
|---|---|---|
| case first, population late | **population first, case as evidence** | the track bar names cherry-picking as the failure |
| benchmark absent from the demo | **at 00:35** | *"measured accuracy"* is one third of the bar |
| exception list implicit | **explicit at 00:55, all 250 accounted for** | it is the other third |
| AI measurement in a doc | **spoken at 02:45, on screen** | it is the answer to *AI Judgment* |
| no runtime failure shown | **webhook refusal at 03:35** | *Failure Recovery* is a named dimension we never demonstrated |
| Activity skipped | **audit trail at 04:00** | four of five track bars ask for one |
