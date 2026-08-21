# Razorpay integration — audit

Written by reading `attest/adapters/razorpay.py` and `attest/webhooks.py` and
running every capability against the code, not by reading the architecture. No
row below says IMPLEMENTED unless a test exercises it.

**Nothing here has ever run against a live Razorpay account.** `fetch` performs
a real authenticated HTTP request, and it has never been called with real
credentials because none exist in this repository. That distinction is the point
of the STATUS column: code that *would* perform a live operation is not the same
as a live integration.

## Capability matrix

| Capability | Status | Implementation | Test | Limitation |
|---|---|---|---|---|
| Settlement ingestion | IMPLEMENTED | `normalise` aggregates recon rows by `settlement_id` into `Settlement(id, settled_on, net_paise, utr)` | `test_adapter001_*` | Net is `credit − debit` summed over the period's rows. A settlement spanning a period boundary is split across two pulls and neither half will balance. |
| Payment ingestion | IMPLEMENTED | rows where `type == "payment"` become `Order` | `test_adapter001_distinct_rows_are_not_deduplicated` | Only settled payments appear in recon. A captured-but-unsettled payment is invisible to this adapter. |
| Refund ingestion | PARTIAL | refunds reduce the settlement total via `debit`; they are **not** modelled as records | `test_adapter001_*` (aggregate only) | A refund cannot be cited as evidence. The engine sees a smaller credit and no reason for it, so a refunded settlement reads as unexplained rather than as refunded. |
| Fee ingestion | PARTIAL | `fee` and `tax` are read per row and folded into `gross = amount` | — | Read but not retained per-order: `Order` has no fee field, and fees are re-derived from the rule set. If Razorpay's fee disagrees with the rule set the difference surfaces as a residual, not as a fee mismatch. |
| Bank statement ingestion | SIMULATED | `BankCredit` is **synthesised** from each settlement: `bank_{sid}`, same amount, a constructed NEFT narration | — | No bank statement is read. The credit always matches the settlement exactly by construction, so this adapter cannot exercise the case the engine exists for — a bank credit that does not correspond to one settlement. |
| Webhook ingestion | IMPLEMENTED | `Ingest.handle` → verify, de-duplicate, scope, report | `test_a_repeat_delivery_*`, `test_webhook_*` | Six event types in `HANDLED`; anything else is recorded as `unsupported` rather than dropped. |
| Signature verification | IMPLEMENTED | HMAC-SHA256 over the **raw** body, `hmac.compare_digest` | `test_webhook_*` bad-signature case | Only enforced when a secret is configured. With `RAZORPAY_WEBHOOK_SECRET` unset the branch never runs — a deployment that forgets the secret verifies nothing and says so nowhere. |
| Idempotency (webhook) | IMPLEMENTED | keyed on event id **and** a hash of the payload | `test_webhook_*` duplicate and replay cases | In-process dict. A restart loses the log and a redelivery would be accepted again. Production needs a unique index on `(provider, event_id)`. |
| Idempotency (ingest) | IMPLEMENTED | recon rows de-duplicated by `entity_id`, or a row hash where absent | `test_adapter001_*` | Within one `normalise` call. Two separate pulls of an overlapping period produce two Snapshots and nothing reconciles them. |
| Duplicate events | IMPLEMENTED | `DUPLICATE` for an identical body, `REPLAY_MISMATCH` for the same id with a different body | `test_webhook_*` | — |
| Incremental sync | NOT IMPLEMENTED | `fetch(year, month, day)` pulls a whole period every time | — | No cursor, no watermark, no "since". Re-pulling a month re-reads it entirely. |
| Pagination | IMPLEMENTED | `count`/`skip` until a short page, capped at 100,000 rows with a warning | — | Never exercised against a real response. The stop condition assumes a short final page, which is the documented behaviour and is unverified here. |
| Replay | PARTIAL | webhook replay is detected; a recon **pull** has no replay concept | `test_webhook_*` | — |
| Error handling | PARTIAL | `NotConnected` for absent credentials; malformed rows counted and skipped | `test_adapter003_*`, `test_the_adapter_refuses_to_fetch_*` | `urlopen` has **no** try/except: an HTTP 500, a timeout or a DNS failure propagates as a raw urllib exception. There is no retry and no backoff. |
| Malformed input | IMPLEMENTED | non-dict rows counted and skipped; unknown methods dropped with a warning; non-integer amounts dropped | `test_adapter002_*`, `test_adapter003_*` | A malformed **webhook body** still raises `JSONDecodeError` out of `Ingest.handle`; the HTTP layer catches it and returns 400, so it is handled at the boundary and not in the adapter. |
| Authentication / secrets | IMPLEMENTED | `RAZORPAY_KEY_ID` / `RAZORPAY_KEY_SECRET` from the environment; `status()` returns the key id truncated to 8 characters | — | No secret is written to a snapshot, a log or the UI. Not verified by a test; verified by reading. |
| Field normalisation | IMPLEMENTED | see the mapping below | `test_the_adapter_never_reports_a_fixture_as_live` | Unrecognised `method` values are dropped rather than guessed — a wrong method is a wrong fee (D16). |
| Integer-paise conversion | IMPLEMENTED | every amount is `int`; non-integer values are dropped with a warning | `test_adapter002_*` | Razorpay's API is already in paise, so this is a validation rather than a conversion. |

## Normalised mapping

Only mappings that exist in the code.

| Razorpay recon field | ATTEST field | Consumer |
|---|---|---|
| `settlement_id` | `Settlement.settlement_id` | subject identity; grouping key for the credit total |
| `settlement_utr` | `Settlement.utr` | `exact_utr` evidence edge; the bank narration |
| `settled_at` | `Settlement.settled_on` | the settlement calendar that builds the candidate pool |
| `credit` − `debit` | `Settlement.net_paise` | the subset-sum target |
| `order_id` (falls back to `entity_id`) | `Order.order_id` | exact join; membership of the candidate universe |
| `payment_id` (falls back to `entity_id`) | `Order.payment_id` | exact join, and the tie-break for identical amounts |
| `amount` (falls back to `credit + fee + tax`) | `Order.gross_paise` | the solver |
| `method` via `METHOD_MAP` | `Order.method` | the fee schedule, hence `net_paise` |
| `created_at` | `Order.captured_on` | blocking by capture date |
| `description` | `Order.customer_name` | evidence display only |
| `entity_id` | — | de-duplication key; not retained |
| `fee`, `tax` | — | read for the `amount` fallback; fees are re-derived from the rule set |
| `type` | — | routes payment rows to orders; everything else to the settlement total |

Fields present in the API and **not** consumed: `currency`, `on_hold`,
`settled`, `notes`, `order_receipt`, `card_network`, `card_issuer`, `card_type`,
`dispute_id`.

## Adversarial pass

Every case run against the code. Outcomes observed, not predicted.

| Attack | Outcome | Behaviour |
|---|---|---|
| fetch without credentials | REJECTED | `NotConnected`; no data fabricated |
| malformed payload (non-dict row) | HANDLED | counted and skipped, warned — **was UNHANDLED** (`AttributeError`) |
| missing identifier | HANDLED | empty `order_id`; row still aggregates into the settlement |
| missing amount | HANDLED | falls back to `credit + fee + tax` |
| zero amount | HANDLED | order with `gross_paise = 0`; blocking's amount ceiling excludes it |
| negative adjustment | HANDLED | `debit` reduces the settlement total; not modelled as an order |
| extreme amount (10¹⁵) | HANDLED | integer, no overflow; exceeds the solver envelope and reports INSUFFICIENT |
| unknown event type | HANDLED | not a payment, so it only affects the settlement total |
| unknown method | HANDLED | dropped with a warning; credit stays in the total, so the settlement reports CONTRADICTED with the exact gap |
| duplicate settlement rows | HANDLED | de-duplicated by `entity_id` — **was UNHANDLED**, inflated the net from 1000 to 2000 |
| repeated refund | HANDLED | same de-duplication |
| out-of-order events | HANDLED | order is irrelevant; aggregation is commutative |
| partial / incomplete source | HANDLED | a settlement with no rows yields net 0 |
| float amount | HANDLED | dropped with a warning — **was UNHANDLED**, `10.5` became `10` silently |
| null `created_at` | HANDLED | epoch 0; the date lands in 1970 and the settlement calendar excludes it |
| duplicate webhook (same body) | HANDLED | `DUPLICATE`, no second action |
| same id, different body | HANDLED | `REPLAY_MISMATCH`, neither acted on |
| invalid signature | REJECTED | `BAD_SIGNATURE`, not processed, not queued, not retried |
| malformed JSON webhook body | UNHANDLED in adapter | `JSONDecodeError` propagates; the HTTP layer returns 400 |

Three of these were defects found by running the pass: ADAPTER-001
(de-duplication), ADAPTER-002 (float amounts), ADAPTER-003 (malformed rows). All
three are fixed and carry regression tests.

## What would be needed for a live integration

1. **A bank statement source.** The synthesised `BankCredit` makes every credit
   match its settlement exactly, which is the one thing this engine exists to
   handle when it does not.
2. **Refunds and adjustments as records**, so they can be cited as evidence
   rather than only reducing a total.
3. **Retry, backoff and error handling** around `_get`.
4. **A durable event log** with a unique index on `(provider, event_id)`.
5. **Incremental sync** with a watermark.
6. **A run against a real account**, after which most rows in this table should
   be re-audited — the difference between reading an API's documentation and
   reading its responses is where adapters actually fail.
