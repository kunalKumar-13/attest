# Phase 25 — Code Quality Audit

Measured against **tracked files only** — what someone cloning the repository
actually receives. Every finding names a file and a symbol.

---

## Inventory

| | tracked files | lines |
|---|---|---|
| Python | 59 | 17,135 |
| JavaScript | 19 | 4,805 |
| HTML (incl. all CSS) | 3 | 2,277 |
| Markdown | 54 | 11,187 |
| Rust | 3 | 485 |
| **total tracked** | **155** | |

No CSS files: the entire stylesheet is one token-led block inside
`workspace.html`. No checked-in virtualenv, no build artifacts, no generated
junk — `.gitignore` covers `.venv/`, `__pycache__/`, `data/`, `native/target/`,
`*.so`, `*.png`.

### Largest ten

```
2315  attest/api.py                  ← 6 of the 9 functions over 100 lines
2195  tests/test_shell_contract.py
1672  attest/ui/workspace.html
1263  tests/test_invariants.py
1200  attest/eval/blocking_study.py
 630  attest/ui/shell.js
 574  attest/partition.py
 491  attest/ui/lens-control.js
 445  attest/eval/claims.py
 443  attest/ui/components.js
```

### Function and class size

| | count | worst |
|---|---|---|
| functions > 100 lines | 9 | `blocking_study.report` 595, `api.trust_claims` 267, `razorpay.normalise` 161 |
| functions 51–100 lines | 31 | `blocking_study.study_run` 90, `api.demonstrate_events` 86 |
| classes > 200 lines | 1 | `RazorpayAdapter` 245 |

### Hazards

| | count | note |
|---|---|---|
| bare `except:` | **0** | |
| `except Exception` | 8 | 5 addressed, 3 in the adversarial harness — see below |
| `TODO` / `FIXME` / `HACK` / `XXX` | **0** | |
| import cycles | **0** | |
| unused imports (pyflakes) | 8 → **1** | |
| unused locals | 9 → 7 | remainder in `blocking_study` report scaffolding |

---

## 25B · Architectural boundaries — verified, not assumed

The import graph was built from the AST and checked against the stated
pipeline. Results:

| claim | verdict |
|---|---|
| a Razorpay adapter should not know about UI | ✅ `attest/adapters/*` imports nothing from `api`, `web` or `ui` |
| **no engine module imports UI or API** | ✅ zero |
| import cycles | ✅ zero |
| policy should not discover proof | ✅ `policy.py` imports `Finding`/`Verdict` — it *reads* a verdict; it imports no solver |
| the ledger should not decide proof validity | ✅ `ledger.py` reads `Decision`, `Judgement`, `Verdict` and the shared `why_not_postable` |
| the solver should not know about presentation | ✅ `subsetsum.py`, `layers.py`, `verdict.py` contain **zero** occurrences of `₹`, `rupees`, `_rs` or `format` |
| formatting code should not live in the proof kernel | ✅ same measurement |

Six imports run "upward" against a naive layering — `partition → subsetsum /
layers / verdict`, `subsetsum → verdict`, `agents → policy`, `certificate →
policy`. On inspection these are **not violations**: `partition` is a solver
orchestrator rather than a search-space module, and `agents`/`certificate`
*consume* a policy decision to describe it rather than making one. Recorded so
the next reader does not re-derive the same false alarm.

`policy.py` imports `money.rupees` — for the human-readable `reasons` strings
attached to a decision, never for the decision. Confirmed by searching every
`rupees(`/`_rs(` call site for use inside a conditional: **none**.

---

## 25C · Money — the important one

Traced rather than grepped.

| check | result |
|---|---|
| `float()` on any amount | **0** — every `float()` is on a *rate* (precision, recall) or a gate metric |
| `round()` on any amount | **0** — every `round()` is on a rate, a density or seconds |
| `Decimal` | only in `attest/adapters/money.py`, at the parse boundary, converting to `int` |
| implicit unit inference | none — `AMOUNT_UNIT = Unit.PAISE` is declared and passed at all 5 amount sites in the adapter |
| a decision reading a formatter | **none** |

The invariant `INPUT → parse → integer paise → computation → formatted output`
holds structurally.

### The one real defect: four money formatters, and one of them lied

`attest/money.py` was meant to be the only renderer. Four survived:

| | grouping | paise | equivalent? |
|---|---|---|---|
| `attest/money.py:rupees` | Indian | yes | — |
| `attest/api.py:_rs` | Indian | yes | **byte-equivalent over 20,016 values** incl. negatives and 12-digit amounts |
| `attest/eval/report.py:_rs` | Indian | yes | **byte-equivalent over 5,008 values** |
| `attest/eval/claims.py:_rs` | **Western** | **truncated** | **no** |

`claims._rs` was `f"₹{paise // 100:,}"`. It renders `₹353.73` as `₹353` and
`₹47,96,811.78` as `₹4,796,811` — and it writes the **generated results block in
README.md**, the repository's front door.

In a system whose entire argument is exact integer paise, a report that silently
drops them is not a style difference. Fixed; before/after in
`CODE-QUALITY-25.md`.

---

## 25K · UI invariants — verified

| invariant | result |
|---|---|
| subject / lens / context owned by the shell | ✅ **zero** assignments to `SHELL.subject`, `.lens`, `.context` or `.from` outside `shell.js` |
| navigation centralised | ✅ one `navigate()`; lenses reach it through one call site |
| history writes centralised | ✅ **zero** `pushState`/`replaceState`/`location.hash =` outside `shell.js` |
| stale async responses discarded | ✅ `AsyncResourceGuard` plus an explicit subject re-check after every await |

The `S.sub = null` class of bug is structurally unavailable: a lens has no
handle to mutate.

---

## 25L · Razorpay adapter

The eleven properties are explicit, not implicit:

```
AMOUNT_UNIT = Unit.PAISE          module-level, never inferred
_ID_FIELDS + _identity()          source identity, per record type
IdentityConflict(ValueError)      two different ids on one row is an error
parse_amount(raw, AMOUNT_UNIT)    at all 5 amount sites, exact or raises
connected() / status()            credential boundary, reported not assumed
Rejection(index, reason, ...)     malformed input rejected with its reason
```

`normalise()` is 161 lines covering three record types in one pass. The steps
25L asks for are all present and in order; they are interleaved rather than
separated. **Not split** — see *changes not made*.

---

## 25O · Dead code

`attest/ui/exp/` (5 files) and `attest/ui/proto/` (5 files) are the surviving
compositions from the Phase 9.2 and 10.1 reviews. They are referenced by
`docs/COMPOSITION-REVIEW.md`, which records that `comp-b`/`comp-c` were removed
and `comp-a` kept.

**Not deleted.** They are documented evidence of a design decision, and removing
them would make the surviving documentation false. This is exactly the case
§25O's conservatism exists for: static analysis calls them unused; the
repository's own record says otherwise.

---

## What the audit did not find

No bare excepts. No TODO/FIXME/HACK. No import cycles. No float or rounding on
money. No formatter influencing a decision. No engine module importing the UI.
No lens mutating shell state. No checked-in build output.
