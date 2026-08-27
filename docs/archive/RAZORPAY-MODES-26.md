# The Razorpay boundary — three modes

ATTEST has one ingestion architecture and three states it can be in. The state
is **derived from the adapter**, never asserted, and it is on screen at all
times.

```
adapter → normalized domain records → engine
```

The adapter owns authentication, requests, pagination, normalisation,
deduplication, malformed-record rejection, signature verification and source
identity. The engine owns the search space, the solver, the proof, the verdict,
the policy and the ledger. Nothing Razorpay-specific reaches the proof kernel —
`subsetsum.py`, `layers.py` and `verdict.py` contain no provider name, no
formatting and no I/O.

---

## The three modes

| mode | when | what the bar says |
|---|---|---|
| **GENERATED** | the synthetic adapter produced the records | `GENERATED` |
| **RAZORPAY** | an adapter holding credentials produced them | `RAZORPAY`, in the proven colour |
| **NOT CONFIGURED** | credentials absent — Razorpay is listed but not connected | Trust: `LIVE RAZORPAY VALIDATION · NOT VERIFIED` |

The mode is computed in `api.source_mode()` from `integrations()`, which reads
`RazorpayAdapter.status()`. An environment without `RAZORPAY_KEY_ID` **cannot**
render as anything but generated — the label is a function of the adapter, so
there is no path that prints "Razorpay" over synthetic records.

Three browser contracts hold this:

```
test_the_data_source_is_named_on_every_screen
test_the_source_mode_comes_from_the_adapter_not_a_constant
test_razorpay_is_never_named_as_the_source_without_credentials
```

## This environment

**No credentials are configured.** `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET` and
`RAZORPAY_WEBHOOK_SECRET` are all unset, so:

- the product runs on generated data — seed 20260821, 250 settlements, 2,368
  orders — and says `GENERATED` on every screen
- Trust leads with `LIVE RAZORPAY VALIDATION · NOT VERIFIED`
- **live pagination remains NOT VERIFIED.** The loop is written and its
  *consequence* is tested over synthetic overlapping pages; it has never been
  run against a real response, and this document will not claim otherwise
- no live-account behaviour of any kind has been exercised

This is an intentional state, not an error. The alternative — running the demo
and describing it as a Razorpay integration — is the one thing the product is
built to refuse.

## Configuring a live account

```bash
export RAZORPAY_KEY_ID=rzp_test_xxxxxxxx
export RAZORPAY_KEY_SECRET=...
export RAZORPAY_WEBHOOK_SECRET=...
./run-demo
```

Credentials are read from the environment only. They are never committed, never
logged, never written into a snapshot, and `status()` truncates the key id to
eight characters. Nothing in the UI or in any generated artifact carries a
secret.

**The connection is read-only by construction.** `RazorpayAdapter.status()`
reports `writes: []`; every endpoint it touches is a `GET`; and no code path in
the adapter mutates anything. ATTEST cannot post, refund, capture or settle
against a real account, and policy demonstrating what it *would* permit does not
reach Razorpay — it reaches ATTEST's own ledger.

## What a live run would and would not change

**Would:** the bar reads `RAZORPAY`; records carry real settlement and payment
identities; the webhook path verifies real signatures; pagination could finally
be verified against a real response shape.

**Would not:** the engine. The search space, the solver, the kernel, the policy
and the ledger receive normalized domain records and cannot tell which adapter
produced them. That is the point of the boundary, and it is why the canonical
ambiguous case stays labelled as generated even when a live account is attached.

## Two worlds, kept apart

If a live account is connected, the demo has two clearly separated halves:

**Source** — real records entering through the adapter. *Here is how data
enters.*

**Proof** — the canonical case, `setl_000089`, generated and labelled as such.
*Here is why the proof boundary matters.*

They are not blurred, and the canonical case is never presented as a live
transaction. A real account is unlikely to contain a naturally interesting
four-explanation ambiguity on demand, and manufacturing one would be the exact
dishonesty this system exists to prevent.
